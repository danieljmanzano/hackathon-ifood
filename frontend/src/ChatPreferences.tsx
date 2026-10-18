import { useState, type FormEvent } from "react";
import { Check, X } from "lucide-react";
import type { DietGoal, NutritionPreferences, Profile } from "./types";

const nutritionGoals: [NutritionPreferences["goals"][number], string][] = [
  ["high_protein", "Mais proteína"], ["low_carb", "Menos carboidratos"],
  ["low_fat", "Menos gordura"], ["low_calorie", "Menos calorias"],
];
const advancedFields = [
  ['max_carbs_g', 'Máximo de carboidratos por prato (g)'], ['max_fat_g', 'Máximo de gordura por prato (g)'],
  ['daily_calorie_goal', 'Meta diária de calorias (kcal)'], ['daily_protein_g', 'Meta diária de proteína (g)'],
  ['daily_carbs_g', 'Meta diária de carboidratos (g)'], ['daily_fat_g', 'Meta diária de gordura (g)'],
] as const;
export function ChatPreferences({ profile, busy, onSave, onClose }: {
  profile: Profile; busy: boolean; onSave: (profile: Profile) => Promise<boolean>; onClose: () => void;
}) {
  const [preferences, setPreferences] = useState(profile.preferences.join(", "));
  const [restrictions, setRestrictions] = useState(profile.restrictions.join(", "));
  const [dislikes, setDislikes] = useState(profile.dislikes.join(", "));
  const [goal, setGoal] = useState<DietGoal | "">(profile.diet_plan.goal ?? "");
  const [budget, setBudget] = useState(profile.default_budget_cents == null ? "" : String(profile.default_budget_cents / 100));
  const [goals, setGoals] = useState(profile.nutrition_preferences.goals);
  const [maxCalories, setMaxCalories] = useState(profile.nutrition_preferences.max_calories?.toString() ?? "");
  const [minProtein, setMinProtein] = useState(profile.nutrition_preferences.min_protein_g?.toString() ?? "");
  const [details, setDetails] = useState(profile.diet_plan.details);
  const [advanced, setAdvanced] = useState<Record<string, string>>(() => Object.fromEntries([
    ['max_carbs_g', profile.nutrition_preferences.max_carbs_g], ['max_fat_g', profile.nutrition_preferences.max_fat_g],
    ['daily_calorie_goal', profile.daily_calorie_goal], ['daily_protein_g', profile.diet_plan.daily_protein_g],
    ['daily_carbs_g', profile.diet_plan.daily_carbs_g], ['daily_fat_g', profile.diet_plan.daily_fat_g],
  ].map(([key, value]) => [key, value?.toString() ?? ''])));
  const [error, setError] = useState("");
  const split = (value: string) => [...new Set(value.split(",").map(v => v.trim()).filter(Boolean))];
  const number = (value: string) => value.trim() ? Number(value.replace(",", ".")) : null;
  async function submit(event: FormEvent) {
    event.preventDefault();
    const amount = number(budget), calories = number(maxCalories), protein = number(minProtein);
    const values = Object.fromEntries(advancedFields.map(([key]) => [key, number(advanced[key])]));
    if ([amount, calories, protein, ...Object.values(values)].some(v => v !== null && (!Number.isFinite(v) || v < 0))
      || [preferences, restrictions, dislikes].some(v => split(v).length > 30)
      || (amount != null && Math.abs(amount * 100 - Math.round(amount * 100)) > .00001)) {
      setError("Confira os valores. Use até 30 ingredientes por campo e duas casas decimais no orçamento.");
      return;
    }
    await onSave({ ...profile, preferences: split(preferences), restrictions: split(restrictions), dislikes: split(dislikes),
      default_budget_cents: amount == null ? null : Math.round(amount * 100),
      daily_calorie_goal: values.daily_calorie_goal,
      diet_plan: { ...profile.diet_plan, goal: goal || null, details, daily_protein_g: values.daily_protein_g,
        daily_carbs_g: values.daily_carbs_g, daily_fat_g: values.daily_fat_g },
      nutrition_preferences: { ...profile.nutrition_preferences, goals, max_calories: calories, min_protein_g: protein,
        max_carbs_g: values.max_carbs_g, max_fat_g: values.max_fat_g },
    });
  }
  return <section className="context-settings" aria-label="Preferências da conversa">
    <div className="panel-title"><div><h2>Seu contexto</h2><p>O que vale para suas próximas sugestões.</p></div>
      <button type="button" className="icon-button" onClick={onClose} aria-label="Fechar preferências"><X size={18} /></button></div>
    <form onSubmit={event => void submit(event)}>
      <div className="form-columns">
        <label className="form-field">Objetivo de dieta<select value={goal} onChange={e => setGoal(e.target.value as DietGoal | "")}>
          <option value="">Sem objetivo definido</option><option value="gain_muscle">Ganhar massa muscular</option>
          <option value="lose_weight">Perder peso</option><option value="maintain_weight">Manter o peso</option>
          <option value="performance">Desempenho nos treinos</option><option value="balanced">Alimentação equilibrada</option>
        </select></label>
        <label className="form-field">Orçamento por prato (R$)<input inputMode="decimal" value={budget} maxLength={12} onChange={e => setBudget(e.target.value)} placeholder="Opcional" /></label>
        <label className="form-field">Ingredientes que gosto<input value={preferences} maxLength={1000} onChange={e => setPreferences(e.target.value)} placeholder="Frango, legumes…" /></label>
        <label className="form-field">Prefiro evitar<input value={dislikes} maxLength={1000} onChange={e => setDislikes(e.target.value)} placeholder="Cebola, pimenta…" /></label>
      </div>
      <label className="form-field">Alergias e restrições<input value={restrictions} maxLength={1000} onChange={e => setRestrictions(e.target.value)} placeholder="Separe por vírgulas" /></label>
      <div className="preference-picker" aria-label="Preferências nutricionais">{nutritionGoals.map(([value, label]) =>
        <button key={value} type="button" aria-pressed={goals.includes(value)} className={goals.includes(value) ? "selected" : ""}
          onClick={() => setGoals(current => current.includes(value) ? current.filter(g => g !== value) : [...current, value])}>{goals.includes(value) && <Check size={13} />}{label}</button>)}</div>
      <details><summary>Limites e metas nutricionais opcionais</summary><div className="form-columns">
        <label className="form-field">Máximo de calorias (kcal)<input inputMode="decimal" maxLength={12} value={maxCalories} onChange={e => setMaxCalories(e.target.value)} placeholder="Opcional" /></label>
        <label className="form-field">Mínimo de proteína (g)<input inputMode="decimal" maxLength={12} value={minProtein} onChange={e => setMinProtein(e.target.value)} placeholder="Opcional" /></label>
        {advancedFields.map(([key, label]) => <label className="form-field" key={key}>{label}
          <input inputMode="decimal" maxLength={12} value={advanced[key]} onChange={e => setAdvanced(current => ({ ...current, [key]: e.target.value }))} placeholder="Opcional" />
        </label>)}
      </div><label className="form-field">Orientações da dieta<textarea value={details} rows={2} maxLength={1000} onChange={e => setDetails(e.target.value)} /></label>
      <p className="muted small">Cadastre apenas metas que você já utiliza. Elas orientam sugestões; não são prescritas pelo aplicativo.</p></details>
      <p className="muted small">Você também pode contar seu objetivo e o que já comeu pelo chat. Restrições precisam ser confirmadas com o restaurante.</p>
      {error && <p className="inline-error" role="alert">{error}</p>}
      <button className="primary-button" disabled={busy} type="submit">Salvar preferências</button>
    </form>
  </section>;
}
