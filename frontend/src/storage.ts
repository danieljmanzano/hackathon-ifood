import type { Consumption, Nutrition } from "./types";

const key = (id: string) => `macro:consumption:v1:${id}`;
// Local fallback until the backend exposes the consumption contract. Never stores credentials.
export function loadConsumption(id: string): Consumption[] {
  try {
    const data: unknown = JSON.parse(localStorage.getItem(key(id)) || "[]");
    if (!Array.isArray(data)) return [];
    return data
      .filter(
        (entry): entry is Consumption =>
          !!entry &&
          typeof entry === "object" &&
          typeof entry.order_id === "string" &&
          typeof entry.item_id === "string" &&
          typeof entry.name === "string" &&
          typeof entry.fraction === "number" &&
          Number.isFinite(entry.fraction) &&
          entry.fraction > 0 &&
          entry.fraction <= 1 &&
          Number.isInteger(entry.quantity) &&
          entry.quantity > 0 &&
          typeof entry.consumed_at === "string" &&
          Number.isFinite(Date.parse(entry.consumed_at)) &&
          typeof entry.feedback === "string",
      )
      .map((entry) => ({
        ...entry,
        nutrition: validNutrition(entry.nutrition),
      }));
  } catch {
    return [];
  }
}
function validNutrition(value: Nutrition | null): Nutrition | null {
  if (value?.state !== "ready") return null;
  const { minimum, calories, maximum } = value;
  return typeof minimum === "number" &&
    typeof calories === "number" &&
    typeof maximum === "number" &&
    [minimum, calories, maximum].every(Number.isFinite) &&
    minimum >= 0 &&
    minimum <= calories &&
    calories <= maximum
    ? value
    : null;
}
export function saveConsumption(id: string, entries: Consumption[]) {
  localStorage.setItem(key(id), JSON.stringify(entries));
}
