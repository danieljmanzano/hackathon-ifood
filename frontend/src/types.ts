export interface NutritionPreferences {
  min_calories: number | null;
  max_protein_g: number | null;
  min_carbs_g: number | null;
  min_fat_g: number | null;
  goals: ("high_protein" | "low_carb" | "low_fat" | "low_calorie")[];
  max_calories: number | null;
  min_protein_g: number | null;
  max_carbs_g: number | null;
  max_fat_g: number | null;
}
export interface Profile {
  id: string;
  preferences: string[];
  restrictions: string[];
  dislikes: string[];
  default_budget_cents: number | null;
  daily_calorie_goal: number | null;
  nutrition_preferences: NutritionPreferences;
  diet_plan: DietPlan;
}
export type DietGoal = "gain_muscle" | "lose_weight" | "maintain_weight" | "performance" | "balanced";
export interface DietPlan {
  goal: DietGoal | null;
  details: string;
  daily_protein_g: number | null;
  daily_carbs_g: number | null;
  daily_fat_g: number | null;
}
export interface DailyNutrients {
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
}
export interface DietContext {
  date: string;
  goal: DietGoal | null;
  meal_count: number;
  foods: string[];
  known_intake: DailyNutrients;
  targets: DailyNutrients;
  remaining: DailyNutrients;
  known_counts: Record<string, number>;
  reasons: string[];
  limitations: string[];
}
export interface FoodDiaryEntry {
  id: string;
  description: string;
  consumed_at: string;
  nutrition: DailyNutrients;
}
export interface DailyFoodDiary {
  entries: FoodDiaryEntry[];
  context: DietContext;
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
export interface MealFeatures {
  portion_size: "small" | "regular" | "large" | "sharing" | null;
  serves: number | null;
  weight_grams: number | null;
  tags: string[];
  eta_max_minutes: number | null;
}
export interface MealIntent {
  diet_context: DietContext | null;
  nutrition_preferences: NutritionPreferences;
  interpretation_source: "llm" | "rules";
  context_summary: string | null;
  inferences: string[];
  inferred_goals: string[];
  fallback_reason: string | null;
  goals: string[];
  labels: string[];
  party_size: number | null;
  max_delivery_minutes: number | null;
  food_query: string;
}
export interface Candidate {
  features?: MealFeatures;
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
export interface ReviewSignal {
  simulated?: boolean;
  source: "personalized" | "community" | "unavailable";
  score: number;
  history_count: number;
  review_count: number;
  community_rating: number | null;
  cuisine_affinity: number;
  personal_rating: number | null;
}
export interface Recommendation {
  approximate_match?: boolean;
  match_confidence?: "normal" | "low";
  review_signal?: ReviewSignal | null;
  candidate: Candidate;
  nutrition: Nutrition;
  reasons: string[];
  limitations: string[];
}
export interface Assembly {
  id: string;
  state: "running" | "ready" | "impossible" | "failed";
  candidate: Candidate | null;
  options: SelectedOption[];
  quantity: number;
  attempt: number;
  events: string[];
  message: string | null;
  nutrition?: Nutrition | null;
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
export type OrderAspects = { [K in keyof ReviewAspects]?: number | null };
export interface ReviewInterpretation {
  rating: number | null;
  aspects: OrderAspects;
  summary: string;
  tags: string[];
}
export interface OrderReviewInput {
  rating: number | null;
  comment: string;
}
export interface OrderReview extends OrderReviewInput {
  aspects: OrderAspects;
  interpretation: ReviewInterpretation | null;
  interpretation_state: "none" | "pending" | "done" | "failed";
}
export interface Order {
  id: string;
  cart_id: string;
  status: "submitted" | "uncertain";
  simulated: boolean;
  created_at: string;
  review?: OrderReview | null;
}
export interface Session {
  pending_preference_update?: {source_message: string} | null;
  nutrition_search?: {id: string; state: "pending" | "complete"; tested: number; accepted: number; approximate?: number; batches: number; reason: string | null} | null;
  last_chat_action?: "search" | "context" | "preferences" | "assembly" | null;
  assembly?: Assembly | null;
  request_intent?: MealIntent | null;
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
export interface ReviewAspects {
  taste: number;
  delivery: number;
  value_for_money: number;
  portion_size: number;
}
export interface ReviewInput {
  merchant_id: string;
  item_id: string;
  rating: number;
  comment: string;
  aspects: ReviewAspects;
}
export interface UserReview extends ReviewInput {
  id: string;
  user_id: string;
  merchant_name: string | null;
  item_name: string | null;
  created_at: string;
  simulated: boolean;
}

export interface UserTastes {
  user_id: string;
  simulated: boolean;
  preferences: string[];
  dislikes: string[];
  restrictions: string[];
  cuisine_affinities: Record<string, number>;
  trait_interests: Record<string, number>;
  aspect_importance: Record<string, number>;
  history_count: number;
  updated_at: string;
}
