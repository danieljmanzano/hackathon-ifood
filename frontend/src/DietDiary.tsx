import { useState, type FormEvent } from "react";
import { Plus, Trash2, Utensils } from "lucide-react";
import type { DailyFoodDiary, DailyNutrients } from "./types";

const fields = [
  ["calories", "Calorias", "kcal"], ["protein_g", "Proteína", "g"],
  ["carbs_g", "Carboidratos", "g"], ["fat_g", "Gordura", "g"],
] as const;

export function DietDiary({ diary, busy, onAdd, onRemove }: {
  diary: DailyFoodDiary | null;
  busy: boolean;
  onAdd: (description: string, nutrition: DailyNutrients) => Promise<boolean>;
  onRemove: (id: string) => Promise<void>;
}) {
  const [description, setDescription] = useState("");
  const [values, setValues] = useState({ calories: "", protein_g: "", carbs_g: "", fat_g: "" });
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    const nutrition = Object.fromEntries(fields.map(([key]) => [key,
      values[key].trim() ? Number(values[key].replace(",", ".")) : null,
    ])) as unknown as DailyNutrients;
    if (!description.trim() || Object.values(nutrition).some(value => value !== null && (!Number.isFinite(value) || value < 0))) {
      setError("Descreva o que comeu e preencha apenas os valores nutricionais que você conhece.");
      return;
    }
    if (await onAdd(description.trim(), nutrition)) {
      setDescription("");
      setValues({ calories: "", protein_g: "", carbs_g: "", fat_g: "" });
    }
  }
  return <section aria-label="Alimentação informada no dia">
    <form className="profile-form" onSubmit={event => void submit(event)}>
      <section>
        <div className="form-section-title">
          <span><Utensils size={20} /></span>
          <div><h2>O que você já comeu hoje?</h2>
            <p>Inclua refeições de casa e de outros lugares. Isso ajuda a escolher o próximo prato.</p></div>
        </div>
        <label className="form-field">Alimentos já consumidos
          <textarea value={description} maxLength={2000} required rows={3}
            onChange={event => setDescription(event.target.value)}
            placeholder="Ex.: Só comi banana e maçã hoje. Ou: almocei arroz, feijão e frango." />
        </label>
        <details><summary>Informar calorias e macros desta refeição (opcional)</summary>
          <p>Use valores que você já conhece, para a quantidade que realmente comeu.</p>
          <div className="form-columns">
            {fields.map(([key, label, unit]) => <label className="form-field" key={key}>
              {label}<div className="input-unit suffix">
                <input inputMode="decimal" maxLength={12} placeholder="Não informado" value={values[key]}
                  aria-label={`${label} no registro`} onChange={event => setValues(current => ({ ...current, [key]: event.target.value }))} />
                <span>{unit}</span>
              </div>
            </label>)}
          </div>
        </details>
        <small>Uma descrição não gera calorias ou macros automaticamente. Evite registrar aqui uma refeição que já confirmou no pedido.</small>
        {error && <p className="inline-error" role="alert">{error}</p>}
      </section>
      <div className="profile-save"><span>Salvo no servidor, no seu perfil atual.</span>
        <button className="primary-button" type="submit" disabled={busy || !description.trim()}>
          <Plus size={16} /> Registrar o que comi
        </button>
      </div>
    </form>
    {diary?.entries.map(entry => <article className="consumption-row" key={entry.id}>
      <span className="consumption-icon"><Utensils size={20} /></span>
      <div><h3>{entry.description}</h3>
        <p>{fields.filter(([key]) => entry.nutrition[key] != null).map(([key, label, unit]) =>
          `${label}: ${entry.nutrition[key]} ${unit}`).join(" · ") || "Quantidades nutricionais não informadas"}</p>
      </div>
      <button type="button" className="icon-button danger" disabled={busy}
        aria-label={`Excluir alimento ${entry.description}`} onClick={() => void onRemove(entry.id)}><Trash2 size={17} /></button>
    </article>)}
    {diary && <div className="day-intro"><div>
      <h2>Contexto para sua próxima busca</h2>
      {diary.context.reasons.map(reason => <p key={reason}>{reason}</p>)}
      {!diary.context.reasons.length && <p>Cadastre seu objetivo em Preferências e conte o que já comeu.</p>}
      <p>Totais conhecidos: {fields.map(([key, label, unit]) =>
        `${label}: ${diary.context.known_intake[key] == null ? "não informado" : `${Math.round(diary.context.known_intake[key]!)} ${unit}`}`).join(" · ")}</p>
      {fields.filter(([key]) => diary.context.targets[key] !== null).map(([key, label, unit]) => <p key={key}>
        Sua meta diária de {label.toLowerCase()}: {diary.context.targets[key]} {unit}.
        {diary.context.remaining[key] !== null && ` Diferença em relação aos registros: ${Math.round(diary.context.remaining[key]!)} ${unit}.`}
      </p>)}
      {diary.context.limitations.map(limitation => <p key={limitation}>{limitation}</p>)}
    </div></div>}
  </section>;
}
