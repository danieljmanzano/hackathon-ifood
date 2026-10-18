import { useState, type FormEvent } from "react";
import type { OrderAspects, OrderReview, ReviewAspects } from "./types";

const aspects: [keyof ReviewAspects, string][] = [
  ["taste", "Sabor"],
  ["delivery", "Entrega"],
  ["value_for_money", "Custo-benefício"],
  ["portion_size", "Tamanho da porção"],
];

/** Nota e aspectos que valem: os do usuário prevalecem sobre os interpretados. */
export function effectiveReview(review: OrderReview) {
  const inferred = review.interpretation;
  const rating = review.rating ?? inferred?.rating ?? null;
  const scores = Object.fromEntries(aspects.map(([key]) => [key, review.aspects[key] ?? inferred?.aspects[key] ?? null])) as OrderAspects;
  return { rating, scores };
}

export function OrderReviewCard({ review, busy, onSave }: {
  review: OrderReview;
  busy: boolean;
  onSave: (rating: number, aspects: OrderAspects) => Promise<boolean>;
}) {
  const { rating, scores } = effectiveReview(review);
  const [editing, setEditing] = useState(false);
  const [draftRating, setDraftRating] = useState(rating ?? 3);
  const [draftScores, setDraftScores] = useState<OrderAspects>(scores);
  const mentioned = aspects.filter(([key]) => scores[key] != null);
  function startEditing() {
    setDraftRating(rating ?? 3);
    setDraftScores(scores);
    setEditing(true);
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    // Só envia como correção o que difere do interpretado, para a interpretação continuar valendo no resto.
    const changed = Object.fromEntries(aspects
      .filter(([key]) => draftScores[key] != null && draftScores[key] !== (review.interpretation?.aspects[key] ?? null))
      .map(([key]) => [key, draftScores[key]])) as OrderAspects;
    if (await onSave(draftRating, { ...review.aspects, ...changed })) setEditing(false);
  }
  return (
    <section className="order-review-card">
      <h3>Sua avaliação</h3>
      {review.comment && <p className="order-review-quote">“{review.comment}”</p>}
      {review.interpretation_state === "pending" ? (
        <p className="muted small" role="status">Interpretando seu comentário…</p>
      ) : (
        <>
          <p className="order-review-reading">
            {review.interpretation_state === "done" ? "Entendemos: " : ""}
            {rating != null ? <strong>★ {rating}/5</strong> : "Sem nota"}
            {mentioned.map(([key, label]) => ` · ${label} ${scores[key]}`)}
          </p>
          {review.interpretation?.summary && <p className="muted small">{review.interpretation.summary}</p>}
          {!!review.interpretation?.tags.length && (
            <div className="order-review-tags">{review.interpretation.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
          )}
          {review.interpretation_state === "failed" && (
            <p className="muted small">Não conseguimos interpretar o comentário. Valem a nota e o texto que você deixou.</p>
          )}
          {rating == null && (
            <p className="muted small">Sem nota, esta avaliação não ajusta suas próximas sugestões.</p>
          )}
          {editing ? (
            <form onSubmit={(event) => void submit(event)}>
              <label className="form-field">Nota geral
                <select value={draftRating} onChange={(event) => setDraftRating(Number(event.target.value))} disabled={busy}>
                  {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}/5</option>)}
                </select>
              </label>
              <div className="review-aspects">
                {aspects.map(([key, label]) => (
                  <label className="form-field" key={key}>{label}
                    <select value={draftScores[key] ?? ""} disabled={busy}
                      onChange={(event) => setDraftScores({ ...draftScores, [key]: event.target.value ? Number(event.target.value) : null })}>
                      <option value="">Não avaliado</option>
                      {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}/5</option>)}
                    </select>
                  </label>
                ))}
              </div>
              <div className="order-review-actions">
                <button className="primary-button" type="submit" disabled={busy}>Salvar ajuste</button>
                <button className="secondary-button" type="button" onClick={() => setEditing(false)} disabled={busy}>Cancelar</button>
              </div>
            </form>
          ) : (
            <button className="secondary-button" type="button" onClick={startEditing}>
              {review.interpretation_state === "done" ? "Não foi isso? Ajustar" : rating == null ? "Dar uma nota" : "Ajustar nota"}
            </button>
          )}
        </>
      )}
    </section>
  );
}
