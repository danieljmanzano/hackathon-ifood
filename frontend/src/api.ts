import type {
  Address,
  Candidate,
  CheckoutChoices,
  Health,
  MerchantSummary,
  Profile,
  SelectedOption,
  Session,
} from "./types";

async function request<T>(
  path: string,
  body?: unknown,
  method = "POST",
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method: body === undefined ? "GET" : method,
      credentials: "same-origin",
      headers:
        body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(30_000),
    });
  } catch {
    throw new Error(
      "Não foi possível conectar. Verifique se o servidor está disponível e tente novamente.",
    );
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : "Não foi possível concluir. Atualize os dados e tente novamente.",
    );
  }
  return response.json() as Promise<T>;
}
export const api = {
  session: () => request<Session>("/session"),
  health: () => request<Health>("/health"),
  addresses: () => request<Address[]>("/addresses"),
  address: (address_id: string) =>
    request<Session>("/session/address", { address_id }, "PUT"),
  profile: (profile: Profile) => request<Session>("/profile", profile, "PUT"),
  search: (text: string) => request<Session>("/search", { text }),
  merchants: () => request<MerchantSummary[]>("/merchants"),
  menu: (merchantId: string) =>
    request<Candidate[]>(`/merchants/${encodeURIComponent(merchantId)}/menu`),
  selectionNutrition: () => request<Session>("/selection/nutrition"),
  item: (item: Candidate) =>
    request<Candidate>(
      `/items/${encodeURIComponent(item.merchant_id)}/${encodeURIComponent(item.item_id)}`,
    ),
  select: (item: Candidate, quantity: number, options: SelectedOption[]) =>
    request<Session>(
      "/selection",
      {
        merchant_id: item.merchant_id,
        item_id: item.item_id,
        quantity,
        options,
      },
      "PUT",
    ),
  choices: () => request<CheckoutChoices>("/checkout/choices"),
  review: (delivery_id: string, payment_id: string) =>
    request<Session>("/checkout/review", { delivery_id, payment_id }),
  confirm: (version: string) =>
    request<Session>("/checkout/confirm", { version, confirmed: true }),
};

export const money = (cents: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    cents / 100,
  );
export const dayKey = (value: string | Date) =>
  new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(
    new Date(value),
  );
export const safeUrl = (url: string | null | undefined) => {
  try {
    const u = new URL(url || "");
    return u.protocol === "https:" ? u.href : undefined;
  } catch {
    return undefined;
  }
};
