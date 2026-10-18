import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  Clock3,
  CreditCard,
  Dumbbell,
  Flame,
  Heart,
  History,
  Home,
  Info,
  Leaf,
  MapPin,
  MessageCircle,
  Pencil,
  Plus,
  Settings2,
  ShieldCheck,
  ShoppingBag,
  SlidersHorizontal,
  Sparkles,
  Target,
  Trash2,
  Truck,
  Utensils,
  X,
} from "lucide-react";
import { api, dayKey, money } from "./api";
import {
  Brand,
  MealCard,
  MealImage,
  Modal,
  NutritionDetails,
  photos,
  Spinner,
  Stepper,
} from "./components";
import { loadConsumption, saveConsumption } from "./storage";
import ChatBar from "./ChatBar";
import type {
  Address,
  Candidate,
  CheckoutChoices,
  Consumption,
  Health,
  Profile,
  Recommendation,
  SelectedOption,
  Session,
  View,
} from "./types";

const nav = [
  { id: "home", name: "Visão geral", icon: Home },
  { id: "chat", name: "Pedir com o Macro", icon: MessageCircle },
  { id: "day", name: "Meu dia", icon: Flame },
  { id: "orders", name: "Meus pedidos", icon: ShoppingBag },
  { id: "profile", name: "Preferências", icon: SlidersHorizontal },
] as const;
const inspirations = [
  {
    title: "O clássico que funciona",
    subtitle: "Frango, uma boa base e muito sabor.",
    photo: photos.chicken,
    query: "Quero frango grelhado até R$ 40",
    tag: "Depois do treino",
    icon: Dumbbell,
  },
  {
    title: "Mais plantas no prato",
    subtitle: "Novos sabores para variar a rotina.",
    photo: photos.plant,
    query: "Quero uma refeição com grão-de-bico até R$ 40",
    tag: "Para variar",
    icon: Leaf,
  },
  {
    title: "Comida que abraça",
    subtitle: "Uma pausa gostosa no seu dia.",
    photo: photos.comfort,
    query: "Quero carne de panela até R$ 40",
    tag: "Sabor de casa",
    icon: Heart,
  },
];

type Dialog = "address" | "item" | "checkout" | "consumption" | "about" | null;

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [view, setView] = useState<View>("home");
  const [dialog, setDialog] = useState<Dialog>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const actionLock = useRef(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [text, setText] = useState("");
  const [detail, setDetail] = useState<Candidate | null>(null);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(
    null,
  );
  const [options, setOptions] = useState<SelectedOption[]>([]);
  const [quantity, setQuantity] = useState(1);
  const [choices, setChoices] = useState<CheckoutChoices | null>(null);
  const [delivery, setDelivery] = useState("");
  const [payment, setPayment] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [entries, setEntries] = useState<Consumption[]>([]);
  const [fraction, setFraction] = useState("1");
  const [feedback, setFeedback] = useState("");
  const [recordDate, setRecordDate] = useState("");
  const composer = useRef<HTMLTextAreaElement>(null);

  async function perform<T>(task: () => Promise<T>): Promise<T | undefined> {
    if (actionLock.current) return;
    actionLock.current = true;
    setBusy(true);
    setError("");
    try {
      return await task();
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Não foi possível concluir a ação. Tente novamente.",
      );
    } finally {
      actionLock.current = false;
      setBusy(false);
    }
  }

  useEffect(() => {
    let active = true;
    async function boot() {
      try {
        const [current, status] = await Promise.all([
          api.session(),
          api.health(),
        ]);
        if (!active) return;
        setSession(current);
        setHealth(status);
        setEntries(loadConsumption(current.id));
        try {
          const list = await api.addresses();
          if (!active) return;
          setAddresses(list);
          if (!current.address && list.length === 1 && !current.order) {
            const updated = await api.address(list[0].id);
            if (active) setSession(updated);
          }
        } catch (e) {
          if (active)
            setError(
              e instanceof Error
                ? e.message
                : "Não foi possível carregar endereços.",
            );
        }
      } catch (e) {
        if (active)
          setError(
            e instanceof Error ? e.message : "Não foi possível iniciar.",
          );
      } finally {
        if (active) setLoading(false);
      }
    }
    void boot();
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (toast) {
      const timer = window.setTimeout(() => setToast(""), 4500);
      return () => clearTimeout(timer);
    }
  }, [toast]);
  useEffect(() => {
    setAccepted(false);
  }, [session?.summary?.version, delivery, payment]);

  function navigate(next: View) {
    setView(next);
    setError("");
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  function open(next: Dialog) {
    setError("");
    setDialog(next);
  }
  async function search(query: string) {
    if (!query.trim() || !session || busy || loading) return;
    setText(query);
    if (session.order) {
      setDialog(null);
      navigate("orders");
      setToast(
        "Este pedido já foi confirmado. Confira os detalhes em Meus pedidos.",
      );
      return;
    }
    if (!session.address) {
      open("address");
      return;
    }
    navigate("chat");
    const next = await perform(() => api.search(query.trim()));
    if (next) {
      setSession(next);
      setDialog(null);
      // Keep text typed while the previous message was being processed.
      setText((current) => (current.trim() === query.trim() ? "" : current));
    }
  }
  async function choose(rec: Recommendation) {
    const item = await perform(() => api.item(rec.candidate));
    if (item) {
      setDetail(item);
      setRecommendation(rec);
      setOptions([]);
      setQuantity(1);
      open("item");
    }
  }
  function updateOption(groupId: string, optionId: string, count: number) {
    setOptions((previous) => [
      ...previous.filter(
        (o) => !(o.group_id === groupId && o.option_id === optionId),
      ),
      ...(count
        ? [{ group_id: groupId, option_id: optionId, quantity: count }]
        : []),
    ]);
  }
  const optionCount = (groupId: string) =>
    options
      .filter((o) => o.group_id === groupId)
      .reduce((sum, o) => sum + o.quantity, 0);
  const validOptions =
    detail?.option_groups.every(
      (g) =>
        optionCount(g.id) >= g.min_selections &&
        optionCount(g.id) <= g.max_selections,
    ) ?? false;
  const selectionTotal = detail
    ? (detail.price_cents +
        options.reduce((sum, choice) => {
          const option = detail.option_groups
            .find((g) => g.id === choice.group_id)
            ?.options.find((o) => o.id === choice.option_id);
          return sum + (option?.price_cents || 0) * choice.quantity;
        }, 0)) *
      quantity
    : 0;

  async function addSelection() {
    if (!detail || !validOptions) return;
    const next = await perform(() => api.select(detail, quantity, options));
    if (next) {
      setSession(next);
      setDialog(null);
      setToast("Prato adicionado. Revise a entrega e o pagamento.");
    }
  }
  async function openCheckout() {
    if (!session?.selected) {
      navigate("chat");
      composer.current?.focus();
      return;
    }
    if (session.mode !== "mock") {
      setError(
        "O checkout real ainda não está disponível. Você pode consultar e escolher os pratos.",
      );
      return;
    }
    const available = await perform(() => api.choices());
    if (available) {
      setChoices(available);
      setDelivery(
        session.summary?.delivery.id || available.delivery[0]?.id || "",
      );
      setPayment(session.summary?.payment.id || available.payment[0]?.id || "");
      setAccepted(false);
      open("checkout");
    }
  }
  async function review() {
    const next = await perform(() => api.review(delivery, payment));
    if (next) {
      setSession(next);
      setAccepted(false);
    }
  }
  async function confirm() {
    if (
      !session?.summary ||
      !accepted ||
      session.mode !== "mock" ||
      session.order
    )
      return;
    // Never retry a submission automatically. A refreshed summary requires a new checkbox event.
    const next = await perform(() => api.confirm(session.summary!.version));
    if (next) {
      setSession(next);
      setDialog(null);
      navigate("orders");
      setToast(
        "Pedido de demonstração confirmado. Nenhuma cobrança foi realizada.",
      );
    }
  }
  function openConsumption() {
    if (
      !session?.order ||
      !session.selected ||
      session.order.status !== "submitted"
    )
      return;
    const existing = entries.find(
      (e) =>
        e.order_id === session.order!.id &&
        e.item_id === session.selected!.candidate.item_id,
    );
    setFraction(String(existing?.fraction || 1));
    setFeedback(existing?.feedback || "");
    setRecordDate(existing?.consumed_at || new Date().toISOString());
    open("consumption");
  }
  function persistConsumption(next: Consumption[]) {
    if (!session) return false;
    try {
      saveConsumption(session.id, next);
      setEntries(next);
      return true;
    } catch {
      setError(
        "O navegador não permitiu salvar o registro. Libere o armazenamento local e tente novamente.",
      );
      return false;
    }
  }
  function recordConsumption() {
    if (
      !session?.order ||
      !session.selected ||
      ![0.25, 0.5, 0.75, 1].includes(Number(fraction))
    )
      return;
    const id = session.selected.candidate.item_id;
    const previous = entries.find(
      (e) => e.order_id === session.order!.id && e.item_id === id,
    );
    // Recommendation estimates are not estimates for a customized plate.
    const nutrition =
      previous?.nutrition ??
      (session.selected.options.length === 0
        ? session.recommendations.find((r) => r.candidate.item_id === id)
            ?.nutrition || null
        : null);
    const entry: Consumption = {
      order_id: session.order.id,
      item_id: id,
      name: session.selected.candidate.name,
      fraction: Number(fraction),
      quantity: session.selected.quantity,
      consumed_at: recordDate,
      nutrition,
      feedback,
    };
    const next = [
      ...entries.filter(
        (e) => !(e.order_id === entry.order_id && e.item_id === id),
      ),
      entry,
    ];
    if (persistConsumption(next)) {
      setDialog(null);
      navigate("day");
      setToast("Consumo confirmado e salvo neste navegador.");
    }
  }
  const today = entries.filter(
    (e) => dayKey(e.consumed_at) === dayKey(new Date()),
  );
  const knownEntries = today.filter((e) => e.nutrition?.state === "ready");
  const knownCalories = knownEntries.reduce(
    (total, e) => total + e.nutrition!.calories! * e.fraction * e.quantity,
    0,
  );
  const goal = session?.profile.daily_calorie_goal;
  const consumed =
    session?.order &&
    entries.some(
      (e) =>
        e.order_id === session.order!.id &&
        e.item_id === session.selected?.candidate.item_id,
    );
  const reviewCurrent =
    session?.summary &&
    session.summary.delivery.id === delivery &&
    session.summary.payment.id === payment;
  const disabled = loading || busy || !session;

  const chatBar = (
    <ChatBar
      value={text}
      onChange={setText}
      onSend={() => void search(text)}
      inputRef={composer}
      busy={busy}
      disabled={disabled}
      inDialog={!!dialog}
    />
  );

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Ir para o conteúdo
      </a>
      <aside className="sidebar">
        <a
          className="brand-link"
          href="#inicio"
          onClick={(e) => {
            e.preventDefault();
            navigate("home");
          }}
          aria-label="Macro, início"
        >
          <Brand />
        </a>
        <div className="sidebar-caption">Comer bem. Seguir em frente.</div>
        <nav aria-label="Navegação principal">
          {nav.map(({ id, name, icon: Icon }) => (
            <button
              key={id}
              onClick={() => navigate(id)}
              className={`nav-item ${view === id ? "active" : ""}`}
              aria-current={view === id ? "page" : undefined}
            >
              <Icon size={19} strokeWidth={1.8} />
              <span>{name}</span>
              {id === "chat" && (
                <span className="nav-spark">
                  <Sparkles size={13} />
                </span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span className="note-icon">
              <Utensils size={20} />
            </span>
            <strong>Uma escolha de cada vez.</strong>
            <p>Seu ritmo, seu gosto e uma refeição que faz sentido.</p>
          </div>
          <button className="sidebar-help" onClick={() => open("about")}>
            <Info size={17} />
            Conheça o Macro
            <ArrowUpRight size={14} />
          </button>
          <button className="user-pill" onClick={() => navigate("profile")}>
            <span className="avatar">V</span>
            <span>
              <strong>Seu espaço</strong>
              <small>Feito para a sua rotina</small>
            </span>
            <Settings2 size={17} />
          </button>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <a
            className="mobile-brand"
            href="#inicio"
            aria-label="Macro, início"
            onClick={(e) => {
              e.preventDefault();
              navigate("home");
            }}
          >
            <Brand />
          </a>
          <div className="breadcrumb">
            Seu espaço
            <ChevronRight size={13} />
            <span>{nav.find((n) => n.id === view)?.name}</span>
          </div>
          <div className="topbar-actions">
            <button
              className="address-button"
              onClick={() => open("address")}
              disabled={disabled || !!session?.order}
            >
              <span className="location-icon">
                <MapPin size={18} />
              </span>
              <span>
                <small>Entregar em</small>
                <strong>
                  {session?.address?.label || "Selecionar endereço"}
                </strong>
              </span>
              <ChevronDown size={14} />
            </button>
            <span className="topbar-divider" />
            <button
              className="bag-button"
              onClick={() =>
                session?.order ? navigate("orders") : void openCheckout()
              }
              disabled={disabled}
              aria-label={
                session?.selected ? "Ver meu pedido" : "Começar um pedido"
              }
            >
              <ShoppingBag size={21} />
              {session?.selected && (
                <span className="bag-count">{session.selected.quantity}</span>
              )}
            </button>
          </div>
        </header>
        <div className="mode-strip">
          <span
            className={`status-dot ${health?.mode === "live" ? "live" : ""}`}
          />
          <span>
            {health?.mode === "live"
              ? "Modo de consulta ao iFood"
              : "Modo demonstração"}
          </span>
          <span className="mode-description">
            {health?.mode === "live"
              ? "Pedidos reais ainda indisponíveis"
              : "Explore à vontade. Nenhum pedido ou cobrança real."}
          </span>
          <button
            onClick={() => open("about")}
            aria-label="Saiba mais sobre o ambiente"
          >
            <Info size={14} />
          </button>
        </div>
        {error && !dialog && (
          <div className="page-error" role="alert">
            <Info size={18} />
            <span>{error}</span>
            <button onClick={() => window.location.reload()}>
              Atualizar dados
            </button>
            <button
              className="icon-button"
              aria-label="Fechar aviso"
              onClick={() => setError("")}
            >
              <X size={16} />
            </button>
          </div>
        )}
        {loading ? (
          <div className="initial-loading">
            <Brand small />
            <Spinner text="Preparando seu espaço…" />
          </div>
        ) : !session ? (
          <div className="empty-page">
            <h1>Vamos reconectar?</h1>
            <p>Inicie o backend para carregar seu perfil e continuar.</p>
            <button
              className="primary-button"
              onClick={() => window.location.reload()}
            >
              Tentar novamente
            </button>
          </div>
        ) : (
          <div
            className={`content-layout ${view === "profile" ? "profile-layout" : ""}`}
          >
            <main className="main-content" id="main-content">
              {(view === "home" || view === "chat") && (
                <>
                  <div className="page-heading">
                    <div>
                      <span className="greeting">
                        Uma pausa para cuidar de você{" "}
                        <span aria-hidden="true">☀</span>
                      </span>
                      <h1>
                        {view === "chat"
                          ? "O que vai bem com o seu dia?"
                          : "Sua próxima boa escolha."}
                      </h1>
                    </div>
                    <div className="date-label">
                      <span className="calendar-day">
                        {new Intl.DateTimeFormat("pt-BR", {
                          day: "2-digit",
                          timeZone: "America/Sao_Paulo",
                        }).format(new Date())}
                      </span>
                      <span>
                        {new Intl.DateTimeFormat("pt-BR", {
                          month: "short",
                          timeZone: "America/Sao_Paulo",
                        })
                          .format(new Date())
                          .replace(".", "")}
                        <small>
                          {new Intl.DateTimeFormat("pt-BR", {
                            weekday: "short",
                            timeZone: "America/Sao_Paulo",
                          })
                            .format(new Date())
                            .replace(".", "")}
                        </small>
                      </span>
                    </div>
                  </div>
                  {view === "home" && (
                    <section className="hero">
                      <div className="hero-copy">
                        <span className="hero-label">
                          <span />
                          <Dumbbell size={14} />
                          Do treino à mesa
                        </span>
                        <h2>
                          Você cuida do treino.
                          <br />A gente facilita
                          <br />o prato.
                        </h2>
                        <p>
                          Conte o que está com vontade. O Macro encontra opções
                          que combinam com você.
                        </p>
                        <button
                          onClick={() => {
                            navigate("chat");
                            requestAnimationFrame(() =>
                              composer.current?.focus(),
                            );
                          }}
                          className="hero-link"
                          aria-label="Encontre sua próxima refeição"
                        >
                          Encontre sua próxima refeição{" "}
                          <span>
                            <ArrowUpRight size={18} />
                          </span>
                        </button>
                      </div>
                      <div className="hero-visual">
                        <span className="hero-orbit orbit-one" />
                        <span className="hero-orbit orbit-two" />
                        <img
                          src={photos.hero}
                          alt="Bowl colorido com vegetais, grãos e folhas, foto ilustrativa"
                          fetchPriority="high"
                          onError={(e) => {
                            e.currentTarget.style.opacity = "0";
                          }}
                        />
                        <span className="floating-leaf">
                          <Leaf size={20} />
                        </span>
                        <div className="hero-sticker">
                          <span>
                            <Check size={14} />
                          </span>
                          Seu gosto vem primeiro.
                        </div>
                      </div>
                    </section>
                  )}
                  <section
                    className="composer-section"
                    aria-label="Converse com o Macro"
                  >
                    <div className="section-label">
                      <span className="mini-spark">
                        <Sparkles size={16} />
                      </span>
                      <h2>
                        {session.messages.length && view === "chat"
                          ? "Continue a conversa"
                          : "Bora encontrar seu próximo prato?"}
                      </h2>
                      <span className="text-only">Por texto, do seu jeito</span>
                    </div>
                    <p className="conversation-hint">
                      Use uma sugestão ou escreva na barra de conversa, sempre
                      disponível abaixo.
                    </p>
                    <div className="quick-prompts">
                      {[
                        {
                          text: "Pós-treino sem complicar",
                          icon: Dumbbell,
                          query: "Quero frango grelhado até R$ 40",
                        },
                        {
                          text: "Hoje vou de vegetal",
                          icon: Leaf,
                          query: "Quero grão-de-bico até R$ 40",
                        },
                        {
                          text: "Até R$ 30",
                          icon: Utensils,
                          query: "Quero uma refeição até R$ 30",
                        },
                      ].map(({ text: label, icon: Icon, query }) => (
                        <button
                          disabled={disabled || !!session.order}
                          onClick={() => void search(query)}
                          key={label}
                        >
                          <Icon size={14} />
                          {label}
                          <Plus size={13} />
                        </button>
                      ))}
                    </div>
                  </section>
                  {busy && (
                    <div className="search-loading">
                      <Brand small />
                      <Spinner text="Consultando opções para você…" />
                    </div>
                  )}
                  {view === "chat" && session.messages.length > 0 && (
                    <section
                      className="conversation"
                      aria-label="Conversa"
                      aria-live="polite"
                    >
                      {session.messages.slice(-6).map((message, i) => (
                        <div
                          className={`message ${message.role}`}
                          key={`${i}-${message.text}`}
                        >
                          {message.role === "assistant" && <Brand small />}
                          <div>
                            <span>
                              {message.role === "assistant" ? "Macro" : "Você"}
                            </span>
                            <p>{message.text}</p>
                          </div>
                        </div>
                      ))}
                    </section>
                  )}
                  {session.recommendations.length > 0 && (
                    <section className="recommendations">
                      <div className="section-heading">
                        <div>
                          <h2>Um prato que combina com você</h2>
                          <p>Escolha o seu e deixe os detalhes com a gente.</p>
                        </div>
                        <span className="result-count">
                          {session.recommendations.length} opções
                        </span>
                      </div>
                      <div className="meal-grid">
                        {session.recommendations.map((r, index) => (
                          <MealCard
                            key={`${r.candidate.merchant_id}-${r.candidate.item_id}`}
                            recommendation={r}
                            index={index}
                            onSelect={() => void choose(r)}
                            disabled={disabled || !!session.order}
                          />
                        ))}
                      </div>
                      <p className="section-footnote">
                        <Info size={13} />O preço final inclui opções e entrega,
                        e aparece na revisão do pedido.
                      </p>
                    </section>
                  )}
                  {view === "chat" &&
                    !session.recommendations.length &&
                    session.messages.length > 0 && (
                      <div className="empty-results">
                        <Utensils size={25} />
                        <h3>Vamos ajustar a busca?</h3>
                        <p>
                          Tente outro prato ou aumente o orçamento. Suas
                          preferências continuam salvas.
                        </p>
                        <button
                          className="secondary-button"
                          onClick={() => composer.current?.focus()}
                        >
                          Editar minha busca
                        </button>
                      </div>
                    )}
                  {!session.recommendations.length && (
                    <section className="inspirations">
                      <div className="section-heading">
                        <div>
                          <h2>Uma inspiração para a sua fome</h2>
                          <p>
                            Escolha um ponto de partida. O resto a gente
                            descobre junto.
                          </p>
                        </div>
                        <span className="illustration-label">
                          Fotos ilustrativas
                        </span>
                      </div>
                      <div className="inspiration-grid">
                        {inspirations.map(
                          ({
                            title,
                            subtitle,
                            photo,
                            query,
                            tag,
                            icon: Icon,
                          }) => (
                            <button
                              className="inspiration-card"
                              aria-label={`Buscar: ${title}`}
                              key={title}
                              disabled={disabled || !!session.order}
                              onClick={() => void search(query)}
                            >
                              <div className="inspiration-photo">
                                <img
                                  src={photo}
                                  alt=""
                                  loading="lazy"
                                  onError={(e) => {
                                    e.currentTarget.style.visibility = "hidden";
                                  }}
                                />
                                <span>
                                  <Icon size={12} />
                                  {tag}
                                </span>
                              </div>
                              <div className="inspiration-copy">
                                <h3>{title}</h3>
                                <p>{subtitle}</p>
                                <span className="inspiration-arrow">
                                  <ArrowUpRight size={18} />
                                </span>
                              </div>
                            </button>
                          ),
                        )}
                      </div>
                    </section>
                  )}
                  <div className="care-note">
                    <ShieldCheck size={17} />
                    <span>Você escolhe. Você revisa. Só depois confirma.</span>
                    <span className="care-line" />
                    <span>Um pedido por vez, no seu controle.</span>
                  </div>
                </>
              )}

              {view === "profile" && (
                <ProfileForm
                  profile={session.profile}
                  busy={busy}
                  onSave={async (profile) => {
                    const next = await perform(() => api.profile(profile));
                    if (next) {
                      setSession(next);
                      setToast(
                        "Preferências salvas. A próxima busca já vai usar seu perfil.",
                      );
                    }
                  }}
                />
              )}

              {view === "day" && (
                <>
                  <div className="page-heading">
                    <div>
                      <span className="greeting">Sua rotina, no seu ritmo</span>
                      <h1>Meu dia.</h1>
                    </div>
                    <span className="heading-icon">
                      <Flame size={24} />
                    </span>
                  </div>
                  <div className="day-intro">
                    <Target size={25} />
                    <div>
                      <h2>Cada refeição conta quando você confirma.</h2>
                      <p>
                        Comprar e comer são momentos diferentes. Registre aqui
                        apenas o que você consumiu.
                      </p>
                    </div>
                  </div>
                  <div className="section-heading">
                    <div>
                      <h2>Refeições de hoje</h2>
                      <p>
                        {new Intl.DateTimeFormat("pt-BR", {
                          dateStyle: "long",
                          timeZone: "America/Sao_Paulo",
                        }).format(new Date())}
                      </p>
                    </div>
                    <span className="result-count">
                      {today.length} registro{today.length !== 1 ? "s" : ""}
                    </span>
                  </div>
                  {today.length ? (
                    <div className="consumption-list">
                      {today.map((entry) => (
                        <article
                          className="consumption-row"
                          key={`${entry.order_id}-${entry.item_id}`}
                        >
                          <span className="consumption-icon">
                            <Utensils size={21} />
                          </span>
                          <div>
                            <h3>{entry.name}</h3>
                            <p>
                              {Math.round(entry.fraction * 100)}% de{" "}
                              {entry.quantity} unidade
                              {entry.quantity > 1 ? "s" : ""} consumida
                              {entry.quantity > 1 ? "s" : ""} ·{" "}
                              {entry.nutrition?.state === "ready"
                                ? `${Math.round(entry.nutrition.minimum! * entry.fraction * entry.quantity)}–${Math.round(entry.nutrition.maximum! * entry.fraction * entry.quantity)} kcal`
                                : "Calorias indisponíveis"}
                            </p>
                            {entry.feedback && (
                              <small>Seu feedback: {entry.feedback}</small>
                            )}
                          </div>
                          <button
                            className="icon-button"
                            aria-label={`Editar consumo de ${entry.name}`}
                            onClick={openConsumption}
                          >
                            <Pencil size={17} />
                          </button>
                          <button
                            className="icon-button danger"
                            aria-label={`Excluir consumo de ${entry.name}`}
                            onClick={() => {
                              if (
                                persistConsumption(
                                  entries.filter(
                                    (e) =>
                                      !(
                                        e.order_id === entry.order_id &&
                                        e.item_id === entry.item_id
                                      ),
                                  ),
                                )
                              )
                                setToast("Registro de consumo excluído.");
                            }}
                          >
                            <Trash2 size={17} />
                          </button>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">
                      <span className="empty-icon">
                        <Utensils size={30} />
                      </span>
                      <h2>Seu dia ainda está em branco.</h2>
                      <p>
                        Depois do seu pedido, conte quanto comeu. Só então ele
                        aparece por aqui.
                      </p>
                      <button
                        className="primary-button"
                        onClick={() =>
                          navigate(session.order ? "orders" : "chat")
                        }
                      >
                        {session.order
                          ? "Ver meu pedido"
                          : "Encontrar uma refeição"}
                        <ArrowRight size={16} />
                      </button>
                    </div>
                  )}
                  {session.order && !consumed && (
                    <div className="pending-consumption">
                      <Clock3 size={20} />
                      <div>
                        <strong>Já fez sua refeição?</strong>
                        <p>
                          Seu pedido está aguardando confirmação de consumo.
                        </p>
                      </div>
                      <button
                        className="secondary-button"
                        onClick={openConsumption}
                        disabled={session.order.status !== "submitted"}
                      >
                        Registrar consumo
                      </button>
                    </div>
                  )}
                  <p className="section-footnote">
                    <Info size={14} />
                    Registros e feedback ficam neste navegador. Sincronização
                    com o servidor ainda pendente.
                  </p>
                </>
              )}

              {view === "orders" && (
                <>
                  <div className="page-heading">
                    <div>
                      <span className="greeting">
                        Do primeiro clique à última garfada
                      </span>
                      <h1>Meus pedidos.</h1>
                    </div>
                    <span className="heading-icon">
                      <ShoppingBag size={24} />
                    </span>
                  </div>
                  {!session.order ? (
                    <div className="empty-state">
                      <span className="empty-icon">
                        <ShoppingBag size={30} />
                      </span>
                      <h2>A próxima refeição começa aqui.</h2>
                      <p>
                        {session.selected
                          ? "Seu prato já está no carrinho. Confira os detalhes para continuar."
                          : "Encontre um prato, personalize e revise tudo antes de confirmar."}
                      </p>
                      <button
                        className="primary-button"
                        onClick={() =>
                          session.selected
                            ? void openCheckout()
                            : navigate("chat")
                        }
                      >
                        {session.selected
                          ? "Revisar meu pedido"
                          : "Pedir com o Macro"}
                        <ArrowRight size={16} />
                      </button>
                    </div>
                  ) : (
                    <article className="order-card">
                      <div className="order-status">
                        <span className="success-icon">
                          <CheckCheck size={24} />
                        </span>
                        <div>
                          <h2>
                            {session.order.status === "uncertain"
                              ? "Aguardando confirmação do pedido"
                              : "Tudo certo com seu pedido!"}
                          </h2>
                          <p>
                            {session.order.simulated
                              ? "Demonstração concluída. Nenhuma compra ou entrega real."
                              : "Pedido recebido. Confira o identificador abaixo."}
                          </p>
                        </div>
                      </div>
                      <div className="order-identifier">
                        <small>Identificador do pedido</small>
                        <code>{session.order.id}</code>
                      </div>
                      {session.selected && (
                        <div className="order-meal">
                          <MealImage item={session.selected.candidate} />
                          <div>
                            <span>
                              {session.selected.candidate.merchant_name}
                            </span>
                            <h3>
                              {session.selected.quantity} ×{" "}
                              {session.selected.candidate.name}
                            </h3>
                            <p>{session.selected.option_labels.join(", ")}</p>
                          </div>
                          <strong>
                            {money(
                              session.selected.quantity *
                                session.selected.unit_total_cents,
                            )}
                          </strong>
                        </div>
                      )}
                      {session.summary && (
                        <div className="order-summary">
                          <div>
                            <MapPin size={18} />
                            <span>{session.summary.address.formatted}</span>
                          </div>
                          <div>
                            <Truck size={18} />
                            <span>{session.summary.delivery.label}</span>
                          </div>
                          <div>
                            <CreditCard size={18} />
                            <span>{session.summary.payment.label}</span>
                          </div>
                          <div className="order-total">
                            <strong>Total</strong>
                            <strong>
                              {money(session.summary.total_cents)}
                            </strong>
                          </div>
                        </div>
                      )}
                      <div className="consumption-callout">
                        <Leaf size={22} />
                        <div>
                          <h3>
                            {consumed
                              ? "Consumo registrado."
                              : "Pediu. Chegou. Comeu?"}
                          </h3>
                          <p>
                            {consumed
                              ? "Você pode corrigir a quantidade no Meu dia."
                              : "O pedido só entra no seu dia quando você confirmar quanto comeu."}
                          </p>
                        </div>
                        <button
                          className="primary-button"
                          onClick={() =>
                            consumed ? navigate("day") : openConsumption()
                          }
                          disabled={session.order.status !== "submitted"}
                        >
                          {consumed ? "Ver meu dia" : "Já comi"}
                          <ArrowRight size={15} />
                        </button>
                      </div>
                    </article>
                  )}
                  <p className="section-footnote">
                    <History size={14} />
                    Esta versão mostra o pedido da sessão atual. O histórico
                    completo será conectado depois.
                  </p>
                </>
              )}
            </main>

            <aside className="day-rail" aria-label="Resumo do dia">
              <section className="daily-card">
                <div className="rail-heading">
                  <h2>Seu dia em equilíbrio</h2>
                  <span className="today-tag">Hoje</span>
                </div>
                <p className="rail-subtitle">
                  Pequenas escolhas, seu próprio ritmo.
                </p>
                <div
                  className="daily-ring"
                  style={
                    {
                      "--progress": `${goal && knownEntries.length ? Math.min(knownCalories / goal, 1) * 100 : 0}%`,
                    } as React.CSSProperties
                  }
                >
                  <div>
                    <Flame size={24} />
                    <strong>
                      {knownEntries.length
                        ? Math.round(knownCalories).toLocaleString("pt-BR")
                        : "—"}
                    </strong>
                    <span>
                      {goal != null
                        ? `de ${goal.toLocaleString("pt-BR")} kcal`
                        : "Sem meta cadastrada"}
                    </span>
                  </div>
                </div>
                {today.some((e) => e.nutrition?.state !== "ready") && (
                  <p className="partial-note">
                    Total parcial: há refeições sem calorias disponíveis.
                  </p>
                )}
                <button
                  className="goal-link"
                  onClick={() => navigate("profile")}
                >
                  <Pencil size={12} />
                  {goal != null ? "Editar minha meta" : "Definir minha meta"}
                </button>
                <div className="macro-rows">
                  {[
                    { label: "Proteínas", color: "orange" },
                    { label: "Carboidratos", color: "blue" },
                    { label: "Gorduras", color: "purple" },
                  ].map((m) => (
                    <div key={m.label}>
                      <span>
                        <i className={m.color} />
                        {m.label}
                      </span>
                      <strong>—</strong>
                    </div>
                  ))}
                </div>
                <p className="nutrition-note">
                  <Info size={13} />
                  Macros ainda indisponíveis. Só somamos consumo confirmado.
                </p>
                <button
                  className="rail-bottom-link"
                  onClick={() => navigate("day")}
                >
                  Acompanhar meu dia
                  <ArrowUpRight size={16} />
                </button>
              </section>
              <section className="preference-card">
                <div className="rail-heading">
                  <h2>
                    <SlidersHorizontal size={16} />
                    Do seu jeito
                  </h2>
                  <button
                    className="icon-button"
                    aria-label="Editar preferências"
                    onClick={() => navigate("profile")}
                  >
                    <Pencil size={14} />
                  </button>
                </div>
                <p>O que importa na hora de escolher.</p>
                <div className="preference-tags">
                  {session.profile.preferences.length ? (
                    session.profile.preferences.slice(0, 4).map((p) => (
                      <span key={p}>
                        <Check size={12} />
                        {p}
                      </span>
                    ))
                  ) : (
                    <span className="neutral-tag">
                      <Heart size={12} />
                      Seu gosto vem primeiro
                    </span>
                  )}
                  {session.profile.default_budget_cents != null && (
                    <span>
                      Até {money(session.profile.default_budget_cents)}
                    </span>
                  )}
                  {session.profile.restrictions.length > 0 && (
                    <span>
                      {session.profile.restrictions.length} restrição(ões)
                    </span>
                  )}
                </div>
                <button
                  className="text-link"
                  onClick={() => navigate("profile")}
                >
                  {session.profile.preferences.length
                    ? "Ajustar preferências"
                    : "Personalizar minhas escolhas"}
                  <ArrowRight size={14} />
                </button>
              </section>
              {session.selected && !session.order && (
                <section className="mini-cart">
                  <span>
                    <ShoppingBag size={18} />
                    Seu próximo prato
                  </span>
                  <strong>{session.selected.candidate.name}</strong>
                  <p>
                    {session.selected.quantity} unidade
                    {session.selected.quantity > 1 ? "s" : ""} ·{" "}
                    {money(
                      session.selected.quantity *
                        session.selected.unit_total_cents,
                    )}
                  </p>
                  <button
                    className="primary-button"
                    onClick={() => void openCheckout()}
                    disabled={disabled}
                  >
                    Revisar pedido
                    <ArrowRight size={15} />
                  </button>
                </section>
              )}
              <div className="ifood-note">
                <span className="ifood-wordmark">
                  iFood<span aria-hidden="true">⌣</span>
                </span>
                <div>
                  <strong>Seu delivery, com mais contexto.</strong>
                  <p>
                    {session.mode === "mock"
                      ? "Integração real em preparação."
                      : "Consulta pelo iFood. Checkout pendente."}
                  </p>
                </div>
              </div>
            </aside>
          </div>
        )}
        <footer className="app-footer">
          <span>
            macro. <span>Uma refeição que combina com a sua vida.</span>
          </span>
          <button onClick={() => open("about")}>
            Feito para o SEMCOMP × iFood
            <ArrowUpRight size={12} />
          </button>
        </footer>
      </div>
      {!dialog && chatBar}
      <nav className="mobile-nav" aria-label="Navegação no celular">
        {nav
          .filter((n) => n.id !== "home")
          .map(({ id, name, icon: Icon }) => (
            <button
              key={id}
              aria-current={view === id ? "page" : undefined}
              className={view === id ? "active" : ""}
              onClick={() => navigate(id)}
            >
              <Icon size={20} />
              <span>{name === "Pedir com o Macro" ? "Pedir" : name}</span>
            </button>
          ))}
      </nav>
      {toast && (
        <div className="toast" role="status">
          <CircleCheck size={18} />
          <span>{toast}</span>
          <button onClick={() => setToast("")} aria-label="Fechar notificação">
            <X size={15} />
          </button>
        </div>
      )}

      {dialog === "about" && (
        <Modal
          footer={chatBar}
          title="Seu próximo prato, com o Macro."
          onClose={() => setDialog(null)}
        >
          <div className="about-content">
            <Brand />
            <p>
              Um assistente para encontrar refeições que combinam com seu gosto,
              orçamento e rotina de treino.
            </p>
            <div className="info-box">
              <ShieldCheck size={21} />
              <div>
                <strong>
                  {health?.mode === "live"
                    ? "Consultas ao iFood"
                    : "Você está em uma demonstração"}
                </strong>
                <p>
                  {health?.mode === "live"
                    ? "O acesso depende de autenticação no servidor. Pedidos reais continuam bloqueados."
                    : "Catálogo, endereço, preços e pedidos são fictícios. Você pode explorar o fluxo sem fazer uma compra."}
                </p>
              </div>
            </div>
            <h3>Transparência em cada escolha</h3>
            <p>
              A conversa atual usa busca por termos e preferências. A
              interpretação por IA e a estimativa nutricional ainda serão
              conectadas.
            </p>
            <p>
              Calorias só aparecem quando disponíveis, com faixa e origem.
              Proteína, carboidratos e gordura não são calculados nesta versão.
            </p>
            <p>
              Consumo e feedback são confirmados por você e ficam neste
              navegador. Pedir não adiciona calorias ao seu dia.
            </p>
          </div>
        </Modal>
      )}

      {dialog === "address" && (
        <Modal
          footer={chatBar}
          title="Onde vai ser sua refeição?"
          onClose={() => setDialog(null)}
          busy={busy}
          error={error}
        >
          <div className="modal-body">
            <p className="muted">
              O endereço ajuda a encontrar os pratos disponíveis para você.
            </p>
            {addresses.length ? (
              <div className="address-list">
                {addresses.map((address) => (
                  <button
                    disabled={busy || !!session?.order}
                    onClick={async () => {
                      const next = await perform(() => api.address(address.id));
                      if (next) {
                        setSession(next);
                        setDialog(null);
                        setToast(
                          "Endereço selecionado. A busca e o carrinho foram atualizados.",
                        );
                      }
                    }}
                    key={address.id}
                    className={`address-choice ${session?.address?.id === address.id ? "selected" : ""}`}
                  >
                    <MapPin size={22} />
                    <span>
                      <strong>{address.label}</strong>
                      <small>{address.formatted}</small>
                    </span>
                    {session?.address?.id === address.id ? (
                      <CircleCheck size={20} />
                    ) : (
                      <ChevronRight size={18} />
                    )}
                  </button>
                ))}
              </div>
            ) : (
              <div className="empty-results">
                <MapPin size={25} />
                <h3>Nenhum endereço disponível</h3>
                <p>
                  Confira a conexão e os endereços cadastrados na sua conta do
                  iFood.
                </p>
                <button
                  className="secondary-button"
                  disabled={busy}
                  onClick={async () => {
                    const list = await perform(() => api.addresses());
                    if (list) setAddresses(list);
                  }}
                >
                  Carregar endereços
                </button>
              </div>
            )}
            <p className="small muted">
              Trocar o endereço limpa a busca e o carrinho para consultar a
              disponibilidade novamente.
            </p>
          </div>
        </Modal>
      )}

      {dialog === "item" && detail && (
        <Modal
          footer={chatBar}
          title="Deixe o prato com a sua cara"
          onClose={() => setDialog(null)}
          busy={busy}
          error={error}
          wide
        >
          <div className="item-modal-intro">
            <MealImage item={detail} />
            <div>
              <span className="merchant">{detail.merchant_name}</span>
              <h3>{detail.name}</h3>
              <p>{detail.description}</p>
              <strong>{money(detail.price_cents)}</strong>
            </div>
          </div>
          <div className="option-groups">
            {detail.option_groups.map((group) => (
              <fieldset key={group.id}>
                <legend>
                  {group.name}
                  <span>
                    {group.min_selections > 0 ? "Obrigatório" : "Opcional"}
                  </span>
                </legend>
                <p>
                  Escolha{" "}
                  {group.min_selections === group.max_selections
                    ? group.max_selections
                    : `de ${group.min_selections} a ${group.max_selections}`}{" "}
                  · {optionCount(group.id)} selecionado(s)
                </p>
                {group.options.map((option) => {
                  const count =
                    options.find(
                      (o) =>
                        o.group_id === group.id && o.option_id === option.id,
                    )?.quantity || 0;
                  return (
                    <div className="option-row" key={option.id}>
                      {option.max_quantity === 1 ? (
                        <label>
                          <input
                            type={
                              group.max_selections === 1 &&
                              group.min_selections > 0
                                ? "radio"
                                : "checkbox"
                            }
                            name={group.id}
                            checked={count > 0}
                            disabled={
                              busy ||
                              (!count &&
                                group.max_selections > 1 &&
                                optionCount(group.id) >= group.max_selections)
                            }
                            onChange={() => {
                              if (group.max_selections === 1)
                                setOptions((previous) => [
                                  ...previous.filter(
                                    (o) => o.group_id !== group.id,
                                  ),
                                  ...(count && group.min_selections === 0
                                    ? []
                                    : [
                                        {
                                          group_id: group.id,
                                          option_id: option.id,
                                          quantity: 1,
                                        },
                                      ]),
                                ]);
                              else
                                updateOption(
                                  group.id,
                                  option.id,
                                  count ? 0 : 1,
                                );
                            }}
                          />
                          <span>{option.name}</span>
                          <strong>
                            {option.price_cents
                              ? `+ ${money(option.price_cents)}`
                              : "Incluso"}
                          </strong>
                        </label>
                      ) : (
                        <>
                          <span>
                            {option.name}
                            <small>
                              {option.price_cents
                                ? `+ ${money(option.price_cents)}`
                                : "Incluso"}
                            </small>
                          </span>
                          <Stepper
                            value={count}
                            min={0}
                            max={Math.min(
                              option.max_quantity,
                              count +
                                group.max_selections -
                                optionCount(group.id),
                            )}
                            label={option.name}
                            onChange={(n) =>
                              updateOption(group.id, option.id, n)
                            }
                          />
                        </>
                      )}
                    </div>
                  );
                })}
              </fieldset>
            ))}
          </div>
          {recommendation && (
            <div className="item-details">
              <details>
                <summary>
                  Por que esta opção?
                  <ChevronDown size={16} />
                </summary>
                <ul>
                  {recommendation.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
                {recommendation.limitations.map((limitation) => (
                  <p className="small muted" key={limitation}>
                    {limitation}
                  </p>
                ))}
              </details>
              {options.length > 0 &&
              recommendation.nutrition.state === "ready" ? (
                <div className="info-box">
                  <Info size={18} />
                  <p>
                    A composição do prato mudou. A estimativa anterior está
                    desatualizada; o cálculo das opções selecionadas ainda não
                    está disponível. Você pode continuar sem estimativa.
                  </p>
                </div>
              ) : (
                <NutritionDetails nutrition={recommendation.nutrition} />
              )}
            </div>
          )}
          <div className="modal-action-bar">
            <Stepper
              value={quantity}
              onChange={setQuantity}
              label="quantidade de pratos"
            />
            <button
              className="primary-button"
              disabled={!validOptions || busy}
              onClick={() => void addSelection()}
            >
              {busy ? (
                <Spinner text="Adicionando…" />
              ) : (
                <>
                  <span>Adicionar ao pedido</span>
                  <strong>{money(selectionTotal)}</strong>
                </>
              )}
            </button>
          </div>
        </Modal>
      )}

      {dialog === "checkout" && session?.selected && choices && (
        <Modal
          footer={chatBar}
          title="Tudo certo com seu pedido?"
          onClose={() => setDialog(null)}
          busy={busy}
          error={error}
          wide
        >
          <div className="checkout-body">
            <div className="checkout-steps">
              <span className="complete">
                <Check size={13} />
                Escolha
              </span>
              <span />
              <span className="current">Revisão</span>
              <span />
              <span>Confirmação</span>
            </div>
            <div className="checkout-item">
              <MealImage item={session.selected.candidate} />
              <div>
                <h3>
                  {session.selected.quantity} ×{" "}
                  {session.selected.candidate.name}
                </h3>
                <p>{session.selected.option_labels.join(" · ")}</p>
                <strong>
                  {money(
                    session.selected.unit_total_cents *
                      session.selected.quantity,
                  )}
                </strong>
              </div>
              <button
                className="icon-button"
                aria-label="Editar prato e complementos"
                disabled={busy}
                onClick={() => {
                  const rec = session.recommendations.find(
                    (r) =>
                      r.candidate.item_id ===
                      session.selected!.candidate.item_id,
                  );
                  if (rec) {
                    setDetail(session.selected!.candidate);
                    setRecommendation(rec);
                    setQuantity(session.selected!.quantity);
                    setOptions(session.selected!.options);
                    open("item");
                  }
                }}
              >
                <Pencil size={17} />
              </button>
            </div>
            <div className="checkout-address">
              <MapPin size={19} />
              <div>
                <strong>{session.address?.label}</strong>
                <p>{session.address?.formatted}</p>
              </div>
            </div>
            <fieldset className="checkout-fieldset">
              <legend>
                <Truck size={17} />
                Entrega
              </legend>
              {choices.delivery.map((d) => (
                <label className="checkout-choice" key={d.id}>
                  <input
                    type="radio"
                    name="delivery"
                    checked={delivery === d.id}
                    onChange={() => setDelivery(d.id)}
                    disabled={busy}
                  />
                  <span>{d.label}</span>
                  <strong>{money(d.fee_cents)}</strong>
                </label>
              ))}
            </fieldset>
            <fieldset className="checkout-fieldset">
              <legend>
                <CreditCard size={17} />
                Pagamento
              </legend>
              {choices.payment.map((p) => (
                <label className="checkout-choice" key={p.id}>
                  <input
                    type="radio"
                    name="payment"
                    checked={payment === p.id}
                    onChange={() => setPayment(p.id)}
                    disabled={busy}
                  />
                  <span>{p.label}</span>
                </label>
              ))}
            </fieldset>
            {reviewCurrent && session.summary ? (
              <>
                <div className="checkout-totals">
                  <div>
                    <span>Prato e complementos</span>
                    <span>{money(session.summary.subtotal_cents)}</span>
                  </div>
                  <div>
                    <span>Entrega</span>
                    <span>{money(session.summary.delivery.fee_cents)}</span>
                  </div>
                  <div className="final-total">
                    <strong>Total do pedido</strong>
                    <strong>{money(session.summary.total_cents)}</strong>
                  </div>
                </div>
                {session.budget_cents != null &&
                  session.summary.total_cents > session.budget_cents && (
                    <div className="budget-warning">
                      <Info size={17} />
                      Com a entrega, o pedido ficou{" "}
                      {money(
                        session.summary.total_cents - session.budget_cents,
                      )}{" "}
                      acima do orçamento. Confira antes de confirmar.
                    </div>
                  )}
                <label className="confirm-checkbox">
                  <input
                    type="checkbox"
                    checked={accepted}
                    onChange={(e) => setAccepted(e.target.checked)}
                    disabled={busy}
                  />
                  <span>
                    Revisei os itens, o endereço, a entrega e o total de{" "}
                    <strong>{money(session.summary.total_cents)}</strong>. Quero
                    confirmar este pedido de demonstração.
                  </span>
                </label>
              </>
            ) : (
              <div className="info-box">
                <Info size={18} />
                <p>
                  Confira a entrega e o pagamento. Em seguida, atualize o resumo
                  para ver o total final e confirmar.
                </p>
              </div>
            )}
          </div>
          <div className="checkout-action">
            <span>
              <ShieldCheck size={14} />
              Demonstração sem cobrança
            </span>
            {reviewCurrent ? (
              <button
                className="primary-button"
                disabled={!accepted || busy}
                onClick={() => void confirm()}
              >
                {busy ? (
                  <Spinner text="Confirmando…" />
                ) : (
                  <>
                    Confirmar pedido de demonstração
                    <Check size={17} />
                  </>
                )}
              </button>
            ) : (
              <button
                className="primary-button"
                disabled={!delivery || !payment || busy}
                onClick={() => void review()}
              >
                {busy ? (
                  <Spinner text="Atualizando…" />
                ) : (
                  <>
                    Revisar total do pedido
                    <ArrowRight size={17} />
                  </>
                )}
              </button>
            )}
          </div>
        </Modal>
      )}

      {dialog === "consumption" && session?.selected && (
        <Modal
          footer={chatBar}
          title="Quanto do pedido você comeu?"
          onClose={() => setDialog(null)}
          error={error}
        >
          <form
            className="modal-body consumption-form"
            onSubmit={(e) => {
              e.preventDefault();
              recordConsumption();
            }}
          >
            <p>
              Considere as {session.selected.quantity} unidade(s) de{" "}
              <strong>{session.selected.candidate.name}</strong>. Registre
              somente a parte que você consumiu.
            </p>
            <fieldset>
              <legend>Quantidade consumida</legend>
              <div className="fraction-options">
                {[
                  { value: "1", label: "Tudo", sub: "100%" },
                  { value: "0.75", label: "Boa parte", sub: "75%" },
                  { value: "0.5", label: "Metade", sub: "50%" },
                  { value: "0.25", label: "Um pouco", sub: "25%" },
                ].map((f) => (
                  <label
                    key={f.value}
                    className={fraction === f.value ? "selected" : ""}
                  >
                    <input
                      type="radio"
                      name="fraction"
                      value={f.value}
                      checked={fraction === f.value}
                      onChange={(e) => setFraction(e.target.value)}
                    />
                    <strong>{f.label}</strong>
                    <span>{f.sub}</span>
                  </label>
                ))}
              </div>
            </fieldset>
            <label className="form-field">
              Como foi a refeição? <span className="optional">Opcional</span>
              <select
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
              >
                <option value="">Prefiro não avaliar agora</option>
                <option>Gostei, pediria de novo</option>
                <option>A porção foi pequena para mim</option>
                <option>A porção foi grande para mim</option>
                <option>Tinha mais molho do que eu gosto</option>
                <option>Não gostei do preparo</option>
              </select>
            </label>
            <p className="small muted">
              O feedback fica registrado para consulta. Suas preferências podem
              ser editadas no perfil; o feedback não altera nutrientes.
            </p>
            <button className="primary-button full-width" type="submit">
              Confirmar consumo
              <Check size={17} />
            </button>
            <p className="small muted centered">
              Você pode editar ou excluir esse registro no Meu dia.
            </p>
          </form>
        </Modal>
      )}
    </div>
  );
}

function ProfileForm({
  profile,
  busy,
  onSave,
}: {
  profile: Profile;
  busy: boolean;
  onSave: (p: Profile) => Promise<void>;
}) {
  const [preferences, setPreferences] = useState(
    profile.preferences.join(", "),
  );
  const [restrictions, setRestrictions] = useState(
    profile.restrictions.join(", "),
  );
  const [dislikes, setDislikes] = useState(profile.dislikes.join(", "));
  const [budget, setBudget] = useState(
    profile.default_budget_cents != null
      ? String(profile.default_budget_cents / 100)
      : "",
  );
  const [goal, setGoal] = useState(
    profile.daily_calorie_goal != null
      ? String(profile.daily_calorie_goal)
      : "",
  );
  const [localError, setLocalError] = useState("");
  const split = (value: string) => [
    ...new Set(
      value
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    ),
  ];
  function submit(e: FormEvent) {
    e.preventDefault();
    setLocalError("");
    const budgetNumber = budget.trim()
      ? Number(budget.replace(",", "."))
      : null;
    const goalNumber = goal.trim() ? Number(goal.replace(",", ".")) : null;
    if (
      (budgetNumber != null &&
        (!Number.isFinite(budgetNumber) ||
          budgetNumber < 0 ||
          budgetNumber > 100000 ||
          Math.abs(budgetNumber * 100 - Math.round(budgetNumber * 100)) >
            0.00001)) ||
      (goalNumber != null && (!Number.isFinite(goalNumber) || goalNumber < 0))
    ) {
      setLocalError(
        "Informe valores válidos e não negativos. Use até duas casas decimais no orçamento.",
      );
      return;
    }
    if (
      [preferences, restrictions, dislikes].some(
        (value) => split(value).length > 30,
      )
    ) {
      setLocalError("Use no máximo 30 itens por campo.");
      return;
    }
    void onSave({
      ...profile,
      preferences: split(preferences),
      restrictions: split(restrictions),
      dislikes: split(dislikes),
      default_budget_cents:
        budgetNumber == null ? null : Math.round(budgetNumber * 100),
      daily_calorie_goal: goalNumber,
    });
  }
  function togglePreference(value: string) {
    const current = split(preferences);
    setPreferences(
      (current.includes(value)
        ? current.filter((p) => p !== value)
        : [...current, value]
      ).join(", "),
    );
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="greeting">Uma rotina que tem a sua cara</span>
          <h1>Seu gosto é o ponto de partida.</h1>
        </div>
      </div>
      <form className="profile-form" onSubmit={submit}>
        <section>
          <div className="form-section-title">
            <span>
              <Heart size={20} />
            </span>
            <div>
              <h2>O que vai bem no seu prato?</h2>
              <p>Ajude o Macro a conhecer suas preferências.</p>
            </div>
          </div>
          <div className="preference-picker">
            {[
              "Frango",
              "Arroz integral",
              "Legumes",
              "Grão-de-bico",
              "Carne",
              "Salada",
            ].map((p) => (
              <button
                type="button"
                aria-pressed={split(preferences).includes(p.toLowerCase())}
                className={
                  split(preferences).includes(p.toLowerCase()) ? "selected" : ""
                }
                key={p}
                onClick={() => togglePreference(p.toLowerCase())}
              >
                {split(preferences).includes(p.toLowerCase()) ? (
                  <Check size={14} />
                ) : (
                  <Plus size={14} />
                )}
                {p}
              </button>
            ))}
          </div>
          <label className="form-field">
            Minhas preferências
            <input
              maxLength={1000}
              value={preferences}
              onChange={(e) => setPreferences(e.target.value)}
              placeholder="Ex.: frango, legumes, arroz integral"
            />
            <small>
              Separe por vírgulas. Vale contar outros ingredientes de que você
              gosta.
            </small>
          </label>
          <label className="form-field">
            Prefiro evitar
            <input
              maxLength={1000}
              value={dislikes}
              onChange={(e) => setDislikes(e.target.value)}
              placeholder="Ex.: cebola, pimenta"
            />
            <small>Gostos pessoais, separados por vírgulas.</small>
          </label>
        </section>
        <section>
          <div className="form-section-title">
            <span className="blue">
              <ShieldCheck size={20} />
            </span>
            <div>
              <h2>Restrições merecem atenção.</h2>
              <p>Elas são diferentes dos ingredientes de que você não gosta.</p>
            </div>
          </div>
          <label className="form-field">
            Alergias e restrições alimentares
            <input
              maxLength={1000}
              value={restrictions}
              onChange={(e) => setRestrictions(e.target.value)}
              placeholder="Ex.: amendoim, lactose"
            />
            <small>
              Separe por vírgulas. A descrição do prato não garante a ausência
              desses ingredientes; confirme com o restaurante.
            </small>
          </label>
        </section>
        <section>
          <div className="form-section-title">
            <span className="purple">
              <Target size={20} />
            </span>
            <div>
              <h2>Seu orçamento e sua meta.</h2>
              <p>Você define. Todos os campos são opcionais.</p>
            </div>
          </div>
          <div className="form-columns">
            <label className="form-field">
              Orçamento por pedido
              <div className="input-unit">
                <span>R$</span>
                <input
                  inputMode="decimal"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  placeholder="40,00"
                  aria-label="Orçamento por pedido em reais"
                />
              </div>
              <small>O total com entrega aparece na revisão.</small>
            </label>
            <label className="form-field">
              Meta diária de calorias
              <div className="input-unit suffix">
                <input
                  inputMode="decimal"
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="Opcional"
                  aria-label="Meta diária de calorias"
                />
                <span>kcal</span>
              </div>
              <small>Cadastre a meta que você já utiliza.</small>
            </label>
          </div>
        </section>
        {localError && (
          <p className="inline-error" role="alert">
            {localError}
          </p>
        )}
        <div className="profile-save">
          <span>
            <ShieldCheck size={15} />
            Salvo no seu perfil, nesta sessão.
          </span>
          <button type="submit" className="primary-button" disabled={busy}>
            {busy ? (
              <Spinner text="Salvando…" />
            ) : (
              <>
                Salvar preferências
                <Check size={17} />
              </>
            )}
          </button>
        </div>
      </form>
    </>
  );
}
