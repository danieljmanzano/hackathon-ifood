/** Comandos locais para as etapas de compra. A confirmação nunca é inferida por LLM. */
export const normalize = (text: string) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
export const confirmsOrder = (text: string) => /^(?:confirmar|confirmo|pode confirmar)(?: o)? pedido[.!]?$/.test(normalize(text));
export const wantsNewOrder = (text: string) => /^(?:novo pedido|nova busca|buscar outra refeicao|recomecar)[.!]?$/.test(normalize(text));
export const reportsContext = (text: string) => /\b(?:comi|consumi|tomei|almocei|jantei|objetivo|ganhar massa|hipertrofia|emagrecer|perder peso|manter (?:o )?peso)\b/.test(normalize(text));

export function matchChoice<T>(text: string, items: T[], label: (item: T) => string): T | undefined {
  const value = normalize(text).replace(/^(?:quero|escolho|escolher|opcao|a opcao|o prato)\s+/, "");
  if (/^[1-9]\d?$/.test(value)) return items[Number(value) - 1];
  const matches = items.filter(item => normalize(label(item)) === value);
  return matches.length === 1 ? matches[0] : undefined;
}

export function requestedQuantity(text: string): number | undefined {
  const match = /^(?:quero\s+|quantidade\s+)?(\d+)\s*(?:unidades?|pratos?)$/.exec(normalize(text));
  if (!match) return undefined;
  const value = Number(match[1]);
  return value >= 1 && value <= 20 ? value : undefined;
}
