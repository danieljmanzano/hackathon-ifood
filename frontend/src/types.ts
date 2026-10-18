export interface Profile {
  id: string;
  preferences: string[];
  restrictions: string[];
  dislikes: string[];
  default_budget_cents: number | null;
  daily_calorie_goal: number | null;
}
export interface Address {
  id: string;
  label: string;
  formatted: string;
  latitude: number;
  longitude: number;
}
export interface AddressCandidate {
  candidate_id: string;
  formatted: string;
  neighborhood: string | null;
  latitude: number | null;
  longitude: number | null;
}
export interface GeocodeResult {
  match: "SINGLE" | "MULTIPLE";
  candidates: AddressCandidate[];
}
export interface NewAddress {
  address: string;
  candidate_id: string;
  neighborhood: string;
  complement: string;
  reference: string;
  alias: "" | "CASA" | "TRABALHO";
}
export interface Option {
  id: string;
  name: string;
  price_cents: number;
  max_quantity: number;
}
export interface OptionGroup {
  id: string;
  name: string;
  min_selections: number;
  max_selections: number;
  options: Option[];
}
export interface Candidate {
  merchant_id: string;
  merchant_name: string;
  item_id: string;
  name: string;
  description: string;
  image_url: string | null;
  price_cents: number;
  currency: "BRL";
  option_groups: OptionGroup[];
  available: boolean;
  simulated: boolean;
}
export interface Nutrition {
  state: "pending" | "ready" | "unavailable" | "error";
  portion_basis: string | null;
  calories: number | null;
  minimum: number | null;
  maximum: number | null;
  confidence: "low" | "medium" | "high" | null;
  method: "published" | "estimated" | "database" | "web" | "consensus" | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  portion_grams?: number | null;
  revisar?: boolean;
  motivo_revisao?: string | null;
  source_url: string | null;
  source_name: string | null;
  evidence: string | null;
  assumptions: string[];
  pipeline_version: string;
  obtained_at: string | null;
}
export interface Recommendation {
  candidate: Candidate;
  nutrition: Nutrition;
  reasons: string[];
  limitations: string[];
}
export interface SelectedOption {
  group_id: string;
  option_id: string;
  quantity: number;
}
export interface SelectedItem {
  candidate: Candidate;
  quantity: number;
  options: SelectedOption[];
  option_labels: string[];
  unit_total_cents: number;
  nutrition: Nutrition;
}
export interface MerchantSummary {
  merchant_id: string;
  name: string;
  logo_url: string | null;
  is_open: boolean;
  distance_km: number | null;
  rating: number | null;
  rating_count: number | null;
  eta_min: number | null;
  eta_max: number | null;
  delivery_fee_cents: number | null;
  minimum_order_cents: number | null;
  simulated: boolean;
}
export interface Delivery {
  id: string;
  label: string;
  fee_cents: number;
}
export interface Payment {
  id: string;
  label: string;
}
export interface CheckoutChoices {
  delivery: Delivery[];
  payment: Payment[];
}
export interface Summary {
  cart_id: string;
  items: SelectedItem[];
  address: Address;
  delivery: Delivery;
  payment: Payment;
  subtotal_cents: number;
  total_cents: number;
  currency: "BRL";
  version: string;
  simulated: boolean;
}
export interface Order {
  id: string;
  cart_id: string;
  status: "submitted" | "uncertain";
  simulated: boolean;
  created_at: string;
}
export interface Session {
  id: string;
  mode: "mock" | "live";
  profile: Profile;
  address: Address | null;
  messages: { role: "user" | "assistant"; text: string }[];
  recommendations: Recommendation[];
  selected: SelectedItem | null;
  summary: Summary | null;
  order: Order | null;
  budget_cents: number | null;
}
export interface Health {
  status: string;
  mode: "mock" | "live";
  simulated: boolean;
  live_orders_enabled: boolean;
  nutrition: string;
  issues: string[];
}
export interface Consumption {
  order_id: string;
  item_id: string;
  name: string;
  fraction: number;
  quantity: number;
  consumed_at: string;
  nutrition: Nutrition | null;
  feedback: string;
}
export type View =
  | "home"
  | "chat"
  | "restaurants"
  | "day"
  | "orders"
  | "profile";
