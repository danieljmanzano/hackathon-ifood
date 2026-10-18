import type { Nutrition, Recommendation, Session } from "./types";

export type Phase =
  "address" | "discover" | "customize" | "delivery" | "payment" | "confirm" | "ordered";
export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  recommendations?: Recommendation[];
};
export const greeting =
  "Oi! Me conte o que você quer comer e como está seu dia. Posso considerar seus gostos, suas avaliações e seu objetivo para encontrar um prato que combine com você.";
export const prompts = [
  "Treinei hoje e estou com muita fome",
  "Quero algo leve até R$ 30",
  "Meu objetivo é ganhar massa e hoje só comi frutas",
];
export const phaseLabels: Record<Phase, string> = {
  address: "Endereço de entrega",
  discover: "Sua próxima refeição",
  customize: "Seu prato",
  delivery: "Entrega",
  payment: "Pagamento",
  confirm: "Revisão do pedido",
  ordered: "Pedido confirmado",
};
export const errorText = (error: unknown) =>
  error instanceof Error ? error.message : "Não foi possível concluir. Tente novamente.";
// Frase com as calorias do prato montado (vezes a quantidade), ou "" se ainda não estão prontas.
export const caloriesText = (nutrition: Nutrition | undefined, quantity: number) =>
  nutrition?.state === "ready" && nutrition.calories != null
    ? `cerca de ${Math.round(nutrition.calories * quantity)} kcal` +
      (nutrition.minimum != null && nutrition.maximum != null
        ? ` (entre ${Math.round(nutrition.minimum * quantity)} e ${Math.round(nutrition.maximum * quantity)} kcal)`
        : "")
    : "";
// Macros, confiança e suposições do prato, em linhas para a bolha do chat (que respeita quebras de linha).
export const nutritionDetails = (nutrition: Nutrition | undefined, quantity: number) => {
  if (nutrition?.state !== "ready") return "";
  const grams = (v: number | null | undefined) =>
    v == null ? "—" : `${Math.round(v * quantity)} g`;
  const lines = [
    `Proteínas: ${grams(nutrition.protein_g)} · Carboidratos: ${grams(nutrition.carbs_g)} · Gorduras: ${grams(nutrition.fat_g)}`,
  ];
  if (nutrition.confidence) {
    const level = { low: "baixa", medium: "média", high: "alta" }[nutrition.confidence];
    lines.push(`Confiança: ${level} (qualitativa, não é probabilidade de acerto)`);
  }
  if (nutrition.revisar && nutrition.motivo_revisao)
    lines.push(`Atenção: ${nutrition.motivo_revisao}`);
  if (nutrition.portion_basis)
    lines.push(
      `Porção considerada: ${nutrition.portion_basis}${quantity > 1 ? ` (× ${quantity})` : ""}`,
    );
  if (nutrition.assumptions.length)
    lines.push("Suposições:", ...nutrition.assumptions.map((a) => `• ${a}`));
  return "\n\n" + lines.join("\n");
};
export const restoredPhase = (session: Session): Phase =>
  !session.address
    ? "address"
    : session.order
      ? "ordered"
      : session.summary
        ? "confirm"
        : session.selected && session.mode === "mock"
          ? "delivery"
          : "discover";
