import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowUp, CheckCircle2, ChevronDown, MapPin, MessageCircle, Settings2, ShoppingBag, Sparkles } from "lucide-react";
import { api, money } from "./api";
import { Brand, MealCard, SelectedNutrition, Spinner, Stepper } from "./components";
import { OrderReviewCard } from "./Reviews";
import { ChatPreferences } from "./ChatPreferences";
import { confirmsOrder, matchChoice, normalize, reportsContext, requestedQuantity, wantsNewOrder } from "./chat-flow";
import { consumptionMigrated, loadConsumption, markConsumptionMigrated, saveConsumption } from "./storage";
import type { Address, Candidate, CheckoutChoices, Nutrition, OrderReviewInput, Recommendation, SelectedOption, Session } from "./types";

type Phase = "address" | "discover" | "customize" | "delivery" | "payment" | "confirm" | "ordered";
type ChatMessage = { id: string; role: "user" | "assistant"; text: string; recommendations?: Recommendation[] };
const greeting = "Oi! Me conte o que você quer comer e como está seu dia. Posso considerar seus gostos, suas avaliações e seu objetivo para encontrar um prato que combine com você.";
const prompts = ["Treinei hoje e estou com muita fome", "Quero algo leve até R$ 30", "Meu objetivo é ganhar massa e hoje só comi frutas"];
const phaseLabels: Record<Phase, string> = {
  address: "Endereço do iFood", discover: "Sua próxima refeição", customize: "Seu prato",
  delivery: "Entrega", payment: "Pagamento", confirm: "Revisão do pedido", ordered: "Pedido confirmado",
};
const errorText = (error: unknown) => error instanceof Error ? error.message : "Não foi possível concluir. Tente novamente.";
// Frase com as calorias do prato montado (vezes a quantidade), ou "" se ainda não estão prontas.
const caloriesText = (nutrition: Nutrition | undefined, quantity: number) =>
  nutrition?.state === "ready" && nutrition.calories != null
    ? `cerca de ${Math.round(nutrition.calories * quantity)} kcal` + (nutrition.minimum != null && nutrition.maximum != null
      ? ` (entre ${Math.round(nutrition.minimum * quantity)} e ${Math.round(nutrition.maximum * quantity)} kcal)` : "")
    : "";
// Macros, confiança e suposições do prato, em linhas para a bolha do chat (que respeita quebras de linha).
const nutritionDetails = (nutrition: Nutrition | undefined, quantity: number) => {
  if (nutrition?.state !== "ready") return "";
  const grams = (v: number | null | undefined) => v == null ? "—" : `${Math.round(v * quantity)} g`;
  const lines = [`Proteínas: ${grams(nutrition.protein_g)} · Carboidratos: ${grams(nutrition.carbs_g)} · Gorduras: ${grams(nutrition.fat_g)}`];
  if (nutrition.confidence) {
    const level = { low: "baixa", medium: "média", high: "alta" }[nutrition.confidence];
    lines.push(`Confiança: ${level} (qualitativa, não é probabilidade de acerto)`);
  }
  if (nutrition.revisar && nutrition.motivo_revisao) lines.push(`Atenção: ${nutrition.motivo_revisao}`);
  if (nutrition.portion_basis) lines.push(`Porção considerada: ${nutrition.portion_basis}${quantity > 1 ? ` (× ${quantity})` : ""}`);
  if (nutrition.assumptions.length) lines.push("Suposições:", ...nutrition.assumptions.map(a => `• ${a}`));
  return "\n\n" + lines.join("\n");
};
const restoredPhase = (session: Session): Phase => !session.address ? "address" : session.order ? "ordered" : session.summary ? "confirm" : session.selected && session.mode === "mock" ? "delivery" : "discover";

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [phase, setPhase] = useState<Phase>("discover");
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [activeSearch, setActiveSearch] = useState<string | null>(null);
  const [detail, setDetail] = useState<Candidate | null>(null);
  const [options, setOptions] = useState<SelectedOption[]>([]);
  const [quantity, setQuantity] = useState(1);
  const [choices, setChoices] = useState<CheckoutChoices | null>(null);
  const [delivery, setDelivery] = useState("");
  const actionLock = useRef(false);
  const epoch = useRef(0);
  const announceCalories = useRef(false);  // modo live: avisar as calorias quando o cálculo do prato terminar
  const bottom = useRef<HTMLDivElement>(null);
  const latestTurn = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);

  function say(role: ChatMessage["role"], content: string, recommendations?: Recommendation[]) {
    const id = crypto.randomUUID();
    setMessages(current => [...current, { id, role, text: content, recommendations }].slice(-100));
    return id;
  }
  async function perform<T>(action: () => Promise<T>): Promise<T | undefined> {
    if (actionLock.current) return;
    actionLock.current = true;
    epoch.current++;
    setBusy(true);
    setError("");
    try { return await action(); }
    catch (reason) { setError(errorText(reason)); }
    finally { actionLock.current = false; setBusy(false); }
  }
  async function boot() {
    setLoading(true);
    setError("");
    try {
      let current = await api.session();
      const available = !current.address ? await api.addresses() : [];
      setAddresses(available);
      if (!current.address && available.length === 1 && !current.order) current = await api.address(available[0].id);
      // Mantém os consumos antigos na personalização, sem uma tela de diário.
      if (!consumptionMigrated(current.id)) {
        const saved = await api.consumption();
        const merged = new Map([...loadConsumption(current.id), ...saved].map(e => [`${e.order_id}:${e.item_id}`, e]));
        if (merged.size > saved.length) await api.saveConsumption([...merged.values()]);
        markConsumptionMigrated(current.id);
        try { saveConsumption(current.id, [...merged.values()]); } catch { /* Cache opcional. */ }
      }
      setSession(current);
      setPhase(restoredPhase(current));
      setDelivery(current.summary?.delivery.id ?? "");
      const history: ChatMessage[] = current.messages.map(m => ({ ...m, id: crypto.randomUUID() }));
      if (!history.length) history.push({ id: crypto.randomUUID(), role: "assistant", text: greeting });
      const lastAssistant = [...history].reverse().find(m => m.role === "assistant");
      if (lastAssistant && current.recommendations.length) lastAssistant.recommendations = current.recommendations;
      setActiveSearch(lastAssistant?.id ?? null);
      setMessages(history);
      if (current.selected && !current.order && current.mode === "mock") setChoices(await api.choices());
    } catch (reason) { setError(errorText(reason)); }
    finally { setLoading(false); }
  }
  useEffect(() => { void boot(); }, []);
  useEffect(() => {
    if (phase === 'discover' && messages.at(-1)?.recommendations?.length) latestTurn.current?.scrollIntoView({ block: 'start' });
    else bottom.current?.scrollIntoView({ behavior: "auto", block: "end" });
  }, [messages.length, phase, busy]);

  const pendingNutrition = session?.recommendations.some(r => r.nutrition.state === "pending");
  useEffect(() => {
    if (!pendingNutrition) return;
    let cancelled = false, tries = 0;
    const timer = window.setInterval(async () => {
      if (actionLock.current || ++tries > 40) { if (tries > 40) clearInterval(timer); return; }
      const version = epoch.current;
      try {
        const next = await api.recommendationsNutrition();
        if (cancelled || version !== epoch.current) return;
        setSession(next);
        setMessages(current => current.map(m => m.id === activeSearch ? { ...m, recommendations: next.recommendations } : m));
      } catch { /* A busca continua disponível mesmo sem estimativa. */ }
    }, 3000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [pendingNutrition, activeSearch]);

  const reviewPending = session?.order?.review?.interpretation_state === "pending";
  useEffect(() => {
    if (!reviewPending) return;
    let cancelled = false, tries = 0;
    const timer = window.setInterval(async () => {
      if (actionLock.current || ++tries > 20) { if (tries > 20) clearInterval(timer); return; }
      const version = epoch.current;
      try {
        const next = await api.order();
        if (!cancelled && version === epoch.current) setSession(next);
      } catch { /* A avaliação será consultada no próximo ciclo. */ }
    }, 3000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [reviewPending, session?.order?.id]);

  const selectedNutritionPending = session?.selected?.nutrition.state === "pending";
  useEffect(() => {
    if (!selectedNutritionPending) return;
    let cancelled = false, tries = 0;
    const timer = window.setInterval(async () => {
      if (actionLock.current || ++tries > 40) { if (tries > 40) clearInterval(timer); return; }
      const version = epoch.current;
      try { const next = await api.selectionNutrition(); if (!cancelled && version === epoch.current) setSession(next); }
      catch { /* O pedido não depende da estimativa. */ }
    }, 3000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [selectedNutritionPending, session?.selected?.candidate.item_id]);
  useEffect(() => {
    const selected = session?.selected;
    if (!announceCalories.current || !selected || selected.nutrition.state === "pending") return;
    announceCalories.current = false;
    const kcal = caloriesText(selected.nutrition, selected.quantity);
    say("assistant", kcal ? `Calorias do seu prato: ${kcal}.${nutritionDetails(selected.nutrition, selected.quantity)}`
      : "Não consegui calcular as calorias deste prato agora.");
  }, [session?.selected?.nutrition.state]);

  async function selectAddress(address: Address, echo = true) {
    const next = await perform(() => api.address(address.id));
    if (!next) return;
    setSession(next); setPhase("discover"); setActiveSearch(null);
    if (echo) say("user", `Usar ${address.label}.`);
    say("assistant", "Endereço selecionado. O que você quer comer?");
  }
  async function search(message: string) {
    if (!session) return;
    const next = await perform(() => api.chat(message, crypto.randomUUID()));
    if (!next) return;
    setSession(next);
    const reply = next.messages.at(-1)?.text ?? "Seu contexto foi atualizado.";
    const searched = next.last_chat_action === "search";
    const id = say("assistant", reply, searched ? next.recommendations : undefined);
    if (searched) { setActiveSearch(id); setPhase("discover"); setDetail(null); }
  }
  async function choose(candidate: Candidate, echo = true) {
    if (!session || session.order || phase !== "discover" || busy) return;
    if (echo) say("user", `Quero ${candidate.name}.`);
    const item = await perform(() => api.item(candidate));
    if (!item) return;
    setDetail(item); setOptions([]); setQuantity(1); setPhase("customize");
    say("assistant", item.option_groups.length ? "Vamos montar seu prato. Escolha os complementos abaixo ou escreva o nome da opção. Depois, diga “continuar”." : "Quantas unidades você quer? Pode ajustar aqui ou escrever, por exemplo, “2 unidades”. Depois, diga “continuar”.");
  }
  const optionCount = (group: string) => options.filter(o => o.group_id === group).reduce((sum, o) => sum + o.quantity, 0);
  const validOptions = !!detail && detail.option_groups.every(g => optionCount(g.id) >= g.min_selections && optionCount(g.id) <= g.max_selections);
  function updateOption(groupId: string, optionId: string, count: number) {
    const group = detail?.option_groups.find(g => g.id === groupId);
    if (!group) return;
    const previous = options.find(o => o.group_id === groupId && o.option_id === optionId)?.quantity ?? 0;
    if (optionCount(groupId) - previous + count > group.max_selections) return;
    setOptions(current => [...current.filter(o => !(o.group_id === groupId && o.option_id === optionId)),
      ...(count ? [{ group_id: groupId, option_id: optionId, quantity: count }] : [])]);
  }
  const selectionTotal = detail ? quantity * (detail.price_cents + options.reduce((sum, o) =>
    sum + (detail.option_groups.find(g => g.id === o.group_id)?.options.find(option => option.id === o.option_id)?.price_cents ?? 0) * o.quantity, 0)) : 0;
  async function continueWithDish(echo = true) {
    if (!detail || !validOptions || busy) return;
    if (echo) say("user", `Continuar com ${quantity} unidade${quantity > 1 ? "s" : ""} de ${detail.name}.`);
    await perform(async () => {
      const next = await api.select(detail, quantity, options);
      setSession(next);
      if (next.mode !== "mock") {
        // Sem compra real: volta para a descoberta em vez de travar na fase de entrega sem opções.
        setPhase("discover"); setDetail(null);
        const nutrition = next.selected?.nutrition;
        const kcal = caloriesText(nutrition, quantity);
        announceCalories.current = nutrition?.state === "pending";
        say("assistant", "Seu prato foi selecionado"
          + (kcal ? ` e tem ${kcal}.` : announceCalories.current ? ". Estou calculando as calorias e aviso aqui assim que ficarem prontas." : ".")
          + " A compra real ainda não está habilitada nesta integração; a consulta e as recomendações continuam disponíveis."
          + nutritionDetails(nutrition, quantity));
        return;
      }
      setPhase("delivery"); setDelivery("");
      setChoices(await api.choices());
      say("assistant", "Prato escolhido. Qual opção de entrega você prefere?");
    });
  }
  function chooseDelivery(id: string, echo = true) {
    const option = choices?.delivery.find(d => d.id === id);
    if (!option || busy) return;
    setDelivery(id); setPhase("payment");
    if (echo) say("user", `Entrega: ${option.label} (${money(option.fee_cents)}).`);
    say("assistant", "Como você prefere pagar?");
  }
  async function choosePayment(id: string, echo = true) {
    const option = choices?.payment.find(p => p.id === id);
    if (!option || !delivery || busy) return;
    if (echo) say("user", `Pagamento: ${option.label}.`);
    const next = await perform(() => api.review(delivery, id));
    if (!next) return;
    setSession(next); setPhase("confirm");
    say("assistant", `Confira o pedido abaixo. O total é ${money(next.summary!.total_cents)}. Se estiver tudo certo, use o botão de confirmação ou escreva “confirmar pedido”.`);
  }
  async function confirmOrder() {
    if (!session?.summary || session.order || phase !== "confirm" || session.mode !== "mock" || busy) return;
    const version = session.summary.version;
    say("user", "Confirmar pedido.");
    // Somente uma ação explícita confirma a versão exibida. Sem retry automático.
    const next = await perform(() => api.confirm(version));
    if (!next) return;
    setSession(next); setPhase("ordered");
    const kcal = next.selected ? caloriesText(next.selected.nutrition, next.selected.quantity) : "";
    say("assistant", `Pedido de demonstração confirmado!${kcal ? ` Seu pedido tem ${kcal}.` : ""} Nenhuma cobrança foi realizada. Você pode deixar uma avaliação aqui na conversa: escolha uma nota, escreva um comentário, ou os dois.`
      + (next.selected ? nutritionDetails(next.selected.nutrition, next.selected.quantity) : ""));
  }
  async function startNewOrder() {
    const next = await perform(api.newOrder);
    if (!next) return false;
    setSession(next); setPhase("discover"); setActiveSearch(null); setDetail(null); setChoices(null);
    say("assistant", next.messages.at(-1)!.text);
    return true;
  }
  async function saveOrderReview(value: OrderReviewInput) {
    const next = await perform(() => api.addOrderReview(value));
    if (!next) return false;
    setSession(next); say("assistant", "Avaliação salva. Sua nota e seu comentário vão ajudar a personalizar as próximas sugestões.");
    return true;
  }
  async function send(message: string) {
    if (!session || busy || loading || !message.trim()) return;
    const value = message.trim();
    setText("");
    if (confirmsOrder(value)) {
      if (phase === "confirm") await confirmOrder();
      else { say("user", value); say("assistant", "Antes de confirmar, precisamos escolher o prato, a entrega e o pagamento e revisar o total."); }
      return;
    }
    say("user", value);
    if (wantsNewOrder(value)) { await startNewOrder(); return; }
    if (phase === "ordered" && /^avalia[cç][aã]o\s*:/i.test(value)) {
      const comment = value.replace(/^avalia[cç][aã]o\s*:\s*/i, "");
      if (comment.length > 200 || !comment) say("assistant", "Escreva uma avaliação com até 200 caracteres depois de “avaliação:”.");
      else await saveOrderReview({ rating: null, comment });
      return;
    }
    if (reportsContext(value)) { await search(value); return; }
    if (phase === "address") {
      const option = matchChoice(value, addresses, a => a.label);
      if (option) await selectAddress(option, false);
      else say("assistant", "Escolha um dos endereços já cadastrados no iFood. O cadastro de endereços continua no aplicativo.");
      return;
    }
    if (phase === "customize" && detail) {
      const amount = requestedQuantity(value);
      if (amount) { setQuantity(amount); say("assistant", `Quantidade ajustada para ${amount}. Confira os complementos e diga “continuar”.`); return; }
      if (normalize(value) === 'sem adicionais') {
        setOptions(current => current.filter(o => !!detail.option_groups.find(g => g.id === o.group_id)?.min_selections));
        say('assistant', 'Removi os adicionais opcionais. Confira as escolhas obrigatórias e diga “continuar”.');
        return;
      }
      if (["continuar", "pronto"].includes(normalize(value))) {
        if (validOptions) await continueWithDish(false);
        else say("assistant", "Ainda falta escolher os complementos obrigatórios indicados abaixo.");
        return;
      }
      const allOptions = detail.option_groups.flatMap(group => group.options.map(option => ({ group, option })));
      const found = matchChoice(value, allOptions, o => o.option.name);
      if (found) {
        const count = options.find(o => o.group_id === found.group.id && o.option_id === found.option.id)?.quantity ?? 0;
        if (optionCount(found.group.id) - count + 1 > found.group.max_selections) {
          say("assistant", `O grupo ${found.group.name} já atingiu o limite. Remova uma opção antes de trocar.`);
        } else { updateOption(found.group.id, found.option.id, count ? 0 : 1); say("assistant", `${found.option.name}: ${count ? "removido" : "selecionado"}.`); }
      } else say("assistant", "Escolha um complemento pelo nome, ajuste a quantidade ou diga “continuar”. Para trocar de refeição, escreva “nova busca”.");
      return;
    }
    if (phase === "delivery" || phase === "payment") {
      if (!choices) { say("assistant", "A compra real ainda não está disponível neste ambiente. Você pode iniciar uma nova busca."); return; }
      if (phase === "delivery") {
        const option = matchChoice(value, choices.delivery, d => d.label);
        if (option) chooseDelivery(option.id, false); else say("assistant", "Escolha a entrega pelo nome ou número da opção.");
      } else {
        const option = matchChoice(value, choices.payment, p => p.label);
        if (option) await choosePayment(option.id, false); else say("assistant", "Escolha o pagamento pelo nome ou número da opção.");
      }
      return;
    }
    if (phase === "confirm") { say("assistant", "Confira os valores antes de decidir. Para finalizar, escreva “confirmar pedido”. Você também pode alterar a entrega ou o pagamento abaixo."); return; }
    if (phase === "ordered") {
      if (/^(quero|buscar|recomende|estou|preciso)\b/.test(normalize(value))) {
        if (await startNewOrder()) await search(value);
      } else say("assistant", "Para avaliar, escreva “avaliação: chegou rápido e estava muito bom”. Para outra refeição, diga “novo pedido”.");
      return;
    }
    const recommendation = matchChoice(value, session.recommendations, r => r.candidate.name);
    if (recommendation) await choose(recommendation.candidate, false);
    else await search(value);
  }
  function submit(event: FormEvent) { event.preventDefault(); void send(text); }
  const placeholder = phase === "customize" ? "Ex.: arroz integral, 2 unidades, continuar…" : phase === "delivery" ? "Qual entrega você prefere?" : phase === "payment" ? "Qual forma de pagamento?" : phase === "confirm" ? "Escreva “confirmar pedido” para finalizar…" : phase === "ordered" ? "Avaliação: conte como foi, ou diga “novo pedido”…" : "Conte sua fome, seu objetivo ou o que quer comer…";
  const disabled = busy || loading || !session;

  return <div className="chat-app">
    <a className="skip-link" href="#conversation">Ir para a conversa</a>
    <header className="chat-header"><div className="chat-header-inner">
      <div className="chat-brand"><Brand /><span className="ifood-context">Seu assistente no iFood</span></div>
      <div className="chat-header-actions">
        <span className="host-address" title={session?.address?.formatted}><MapPin size={15} /><span>{session?.address?.label ?? "Endereço do iFood"}</span></span>
        <button className="context-button" aria-label="Preferências da conversa" aria-expanded={preferencesOpen} aria-controls="chat-preferences" disabled={!session}
          onClick={() => setPreferencesOpen(open => !open)}><Settings2 size={17} /><span>Preferências</span><ChevronDown size={13} /></button>
      </div>
    </div></header>
    <main id="conversation" className="chat-main">
      {session?.mode === "mock" && <p className="demo-note">Demonstração: pratos, preços e pedidos fictícios. Sem cobrança.</p>}
      {preferencesOpen && session && <div id="chat-preferences"><ChatPreferences profile={session.profile} busy={busy} onClose={() => setPreferencesOpen(false)}
        onSave={async profile => {
          const next = await perform(() => api.profile(profile));
          if (!next) return false;
          setSession(next); setPreferencesOpen(false); say("assistant", "Preferências salvas. Vou usar esse contexto nas próximas sugestões."); return true;
        }} /></div>}
      <div className="conversation-title"><MessageCircle size={17} /><h1>{phaseLabels[phase]}</h1><span>Macro</span></div>
      {loading && <div className="boot-state"><Spinner text="Preparando sua conversa…" /></div>}
      <div className="chat-transcript" role="log" aria-label="Conversa com o Macro" aria-live="polite" aria-relevant="additions">
        {messages.map((message, index) => <div key={message.id} ref={index === messages.length - 1 ? latestTurn : undefined} className={`chat-turn ${message.role}`}>
          {message.role === "assistant" && <span className="assistant-avatar" aria-hidden="true"><Sparkles size={17} /></span>}
          <div className="turn-content"><div className="message-bubble"><span className="sr-only">{message.role === "assistant" ? "Macro: " : "Você: "}</span>{message.text}</div>
            {!!message.recommendations?.length && <div className="chat-recommendations" aria-label="Pratos recomendados">
              {message.recommendations.map((recommendation, index) => <MealCard key={`${recommendation.candidate.merchant_id}:${recommendation.candidate.item_id}`}
                recommendation={recommendation} index={index} disabled={disabled || phase !== "discover" || activeSearch !== message.id || !!session?.order}
                onSelect={() => void choose(recommendation.candidate)} />)}
            </div>}
          </div>
        </div>)}
      </div>
      {!loading && messages.length === 1 && phase === "discover" && <div className="starter-prompts" aria-label="Exemplos para começar">{prompts.map(prompt =>
        <button key={prompt} disabled={disabled} onClick={() => void send(prompt)}>{prompt}</button>)}</div>}
      {phase === "address" && !loading && <section className="chat-action" aria-label="Endereço do iFood"><h2>Qual endereço do iFood vamos usar?</h2>
        {addresses.map((address, index) => <button className="choice-button" key={address.id} disabled={disabled} onClick={() => void selectAddress(address)}>
          <span>{index + 1}. {address.label}</span><small>{address.formatted}</small></button>)}
        {!addresses.length && <p>Escolha ou cadastre seu endereço no iFood e atualize esta conversa.</p>}
      </section>}
      {phase === "customize" && detail && <section className="chat-action" aria-label="Montar prato">
        <span className="action-caption">Vamos montar seu pedido</span><h2>{detail.name}</h2><p className="muted">{detail.description}</p>
        {detail.option_groups.map(group => <fieldset className="option-group" key={group.id}><legend>{group.name}</legend>
          <p>{group.min_selections ? `Escolha de ${group.min_selections} a ${group.max_selections}` : `Opcional · até ${group.max_selections}`} · {optionCount(group.id)} selecionado(s)</p>
          {group.options.map(option => {
            const count = options.find(o => o.group_id === group.id && o.option_id === option.id)?.quantity ?? 0;
            return <div className="option-row" key={option.id}><span>{option.name}<small>{option.price_cents ? `+ ${money(option.price_cents)}` : "Incluído"}</small></span>
              <Stepper value={count} min={0} max={Math.min(option.max_quantity, count + group.max_selections - optionCount(group.id))}
                label={option.name} onChange={value => updateOption(group.id, option.id, value)} /></div>;
          })}</fieldset>)}
        <div className="quantity-row"><span>Quantidade</span><Stepper value={quantity} label="quantidade de pratos" onChange={setQuantity} /></div>
        <div className="action-footer"><span><strong>{money(selectionTotal)}</strong><small>Entrega calculada na próxima etapa</small></span>
          <button className="primary-button" disabled={disabled || !validOptions} onClick={() => void continueWithDish()}>Continuar com este prato</button></div>
      </section>}
      {phase === "delivery" && choices && <section className="chat-action" aria-label="Escolher entrega"><h2>Qual entrega combina com você?</h2>
        {choices.delivery.map((choice, index) => <button className="choice-button" key={choice.id} disabled={disabled} onClick={() => chooseDelivery(choice.id)}>
          <span>{index + 1}. {choice.label}</span><strong>{money(choice.fee_cents)}</strong></button>)}</section>}
      {phase === "payment" && choices && <section className="chat-action" aria-label="Escolher pagamento"><h2>Como você prefere pagar?</h2>
        {choices.payment.map((choice, index) => <button className="choice-button" key={choice.id} disabled={disabled} onClick={() => void choosePayment(choice.id)}>
          <span>{index + 1}. {choice.label}</span></button>)}</section>}
      {phase === "confirm" && session?.summary && <section className="chat-action" aria-label="Revisão e confirmação do pedido">
        <div className="panel-title"><h2>Vamos conferir?</h2><ShoppingBag size={20} /></div>
        {session.summary.items.map(item => <div key={item.candidate.item_id} className="summary-item"><strong>{item.quantity} × {item.candidate.name}</strong>
          {item.option_labels.length > 0 && <p>{item.option_labels.join(", ")}</p>}
          <SelectedNutrition nutrition={item.nutrition} quantity={item.quantity} /></div>)}
        <dl className="order-details"><div><dt>Entregar em</dt><dd>{session.summary.address.formatted}</dd></div>
          <div><dt>Entrega</dt><dd>{session.summary.delivery.label}</dd></div><div><dt>Pagamento</dt><dd>{session.summary.payment.label}</dd></div>
          <div><dt>Pratos e complementos</dt><dd>{money(session.summary.subtotal_cents)}</dd></div>
          <div><dt>Taxa de entrega</dt><dd>{money(session.summary.delivery.fee_cents)}</dd></div>
          <div className="order-total"><dt>Total</dt><dd>{money(session.summary.total_cents)}</dd></div></dl>
        <div className="summary-adjustments"><button disabled={disabled} onClick={() => setPhase("delivery")}>Alterar entrega</button>
          <button disabled={disabled} onClick={() => setPhase("payment")}>Alterar pagamento</button></div>
        <p className="small muted">Pedido de demonstração. Confirme somente depois de conferir os itens e o total.</p>
        <button className="primary-button confirm-order" disabled={disabled || session.mode !== "mock"} onClick={() => void confirmOrder()}>
          Confirmar pedido · {money(session.summary.total_cents)}</button>
      </section>}
      {phase === "ordered" && session?.order && <section className="chat-action order-receipt" aria-label="Pedido confirmado">
        <div className="receipt-heading"><CheckCircle2 size={25} /><div><h2>Pedido confirmado</h2><p>Demonstração · sem cobrança</p></div></div>
        {session.selected && <div className="summary-item"><p>{session.selected.quantity} × {session.selected.candidate.name}</p>
          {/* session.selected é o que a consulta de calorias atualiza enquanto ainda está "pending". */}
          <SelectedNutrition nutrition={session.selected.nutrition} quantity={session.selected.quantity} /></div>}
        {session.summary && <p className="receipt-total">Total: {money(session.summary.total_cents)}</p>}
        {session.order.review ? <OrderReviewCard review={session.order.review} busy={busy} onSave={async (rating, aspects) => {
          const next = await perform(() => api.editOrderReview(rating, aspects));
          if (!next) return false; setSession(next); say("assistant", "Avaliação ajustada. Sua correção prevalece nas próximas sugestões."); return true;
        }} /> : <QuickReview busy={busy} onSave={saveOrderReview} />}
        <button className="secondary-button" disabled={disabled || reviewPending} onClick={() => void startNewOrder()}>Buscar outra refeição</button>
      </section>}
      {busy && <div className="assistant-working"><Spinner text={phase === "discover" ? "Entendendo seu pedido…" : "Só um instante…"} /></div>}
      {error && <div className="chat-error" role="alert"><p>{error}</p><button disabled={busy} onClick={() => void boot()}>Atualizar conversa</button></div>}
      <div ref={bottom} className="conversation-end" />
    </main>
    <footer className="composer-dock"><form className="chat-composer" onSubmit={submit}>
      <label className="sr-only" htmlFor="chat-message">Mensagem para o Macro</label>
      <textarea ref={composer} id="chat-message" value={text} maxLength={2000} rows={2} disabled={disabled} placeholder={placeholder}
        onChange={event => setText(event.target.value)} onKeyDown={event => {
          if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void send(text); }
        }} />
      <button className="send-message" type="submit" aria-label="Enviar mensagem" disabled={disabled || !text.trim()}><ArrowUp size={21} /></button>
    </form><p>Você escolhe o prato. O pedido só é enviado depois da sua confirmação.</p></footer>
  </div>;
}

function QuickReview({ busy, onSave }: { busy: boolean; onSave: (review: OrderReviewInput) => Promise<boolean> }) {
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (rating != null || comment.trim()) await onSave({ rating, comment: comment.trim() });
  }
  return <form className="quick-review" onSubmit={event => void submit(event)}>
    <h3>Quer deixar uma avaliação?</h3><p>Escreva do seu jeito. Você pode corrigir o que entendermos depois.</p>
    <div className="order-review-stars" role="radiogroup" aria-label="Nota do pedido">{[1, 2, 3, 4, 5].map(n =>
      <button key={n} type="button" role="radio" aria-checked={rating === n} aria-label={`${n} de 5`} disabled={busy}
        className={rating != null && n <= rating ? "filled" : ""} onClick={() => setRating(rating === n ? null : n)}>★</button>)}</div>
    <label className="form-field">Conte como foi <span className="optional">Opcional</span><textarea maxLength={200} rows={3} value={comment}
      onChange={event => setComment(event.target.value)} placeholder="Ex.: demorou um pouco, mas o sabor estava ótimo" disabled={busy} /></label>
    <div className="review-form-footer"><small>{comment.length}/200 · Sua nota escolhida prevalece.</small>
      <button className="primary-button" type="submit" disabled={busy || (rating == null && !comment.trim())}>Salvar avaliação</button></div>
  </form>;
}
