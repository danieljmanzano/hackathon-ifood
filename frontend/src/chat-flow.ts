/** Comandos locais para as etapas de compra. A confirmação nunca é inferida por LLM. */
export const normalize = (text: string) =>
  text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
export const confirmsOrder = (text: string) =>
  /^(?:confirmar|confirmo|pode confirmar)(?: o)? pedido[.!]?$/.test(normalize(text));
export const wantsNewOrder = (text: string) =>
  /^(?:novo pedido|nova busca|buscar outra refeicao|recomecar)[.!]?$/.test(normalize(text));
/** Toda resposta à pergunta pendente passa pela validação de confirmação do backend. */
export function preferenceReply(text: string, pending: boolean): boolean {
  return pending && !!normalize(text) && !confirmsOrder(text);
}
/** "add" abre o cadastro; "change" abre a lista de endereços para trocar. */
export function addressIntent(text: string): "add" | "change" | undefined {
  const value = normalize(text).replace(/[.!?]$/, "");
  if (
    /^(?:quero )?(?:adicionar|cadastrar|incluir|novo|criar)(?: um)?(?: novo)? endereco(?: de entrega)?$/.test(
      value,
    )
  )
    return "add";
  if (
    /^(?:quero )?(?:trocar|mudar|alterar|escolher|selecionar|ver)(?: o| de| meu| meus)? enderecos?(?: de entrega)?$/.test(
      value,
    ) ||
    /^(?:entregar|entrega) em outro (?:endereco|lugar)$/.test(value) ||
    /^(?:outro|meus) enderecos?$/.test(value)
  )
    return "change";
  return undefined;
}
export const reportsContext = (text: string) =>
  /\b(?:comi|consumi|tomei|almocei|jantei|objetivo|ganhar massa|hipertrofia|emagrecer|perder peso|manter (?:o )?peso)\b/.test(
    normalize(text),
  );

export function matchChoice<T>(
  text: string,
  items: T[],
  label: (item: T) => string,
): T | undefined {
  const value = normalize(text).replace(/^(?:quero|escolho|escolher|opcao|a opcao|o prato)\s+/, "");
  if (/^[1-9]\d?$/.test(value)) return items[Number(value) - 1];
  const matches = items.filter((item) => normalize(label(item)) === value);
  return matches.length === 1 ? matches[0] : undefined;
}

export function requestedQuantity(text: string): number | undefined {
  const match = /^(?:quero\s+|quantidade\s+)?(\d+)\s*(?:unidades?|pratos?)$/.exec(normalize(text));
  if (!match) return undefined;
  const value = Number(match[1]);
  return value >= 1 && value <= 20 ? value : undefined;
}

/** Encaminha mensagens sobre o perfil para o agente decidir se deve salvar, buscar ou esclarecer. */
export function preferenceCommand(text: string): boolean {
  const value = normalize(text);
  const scope =
    /(?:meu|minha)\s+(?:minim[oa]|maxim[oa])|preferencias?|perfil|metas?|objetivo|limites?|orcamento|restricoes|alergias|(?:ingredientes?|alimentos?|coisas) (?:que|preferidos|favoritos)|gostos?/;
  const persistent =
    /\b(?:de agora em diante|daqui (?:para|pra) frente|a partir de agora|nas proximas sugestoes|sempre|passe a evitar|passe a preferir)\b/;
  const personal =
    /\b(?:gosto de|nao como|prefiro evitar|nao quero mais|sou alergic[oa]|tenho alergia|sou intolerante)\b/;
  if (
    /^(?:como|onde|qual|posso)\b/.test(value) ||
    /^nao (?:salve|salvar|altere|alterar|mude|mudar)\b/.test(value)
  )
    return false;
  return scope.test(value) || persistent.test(value) || personal.test(value);
}
