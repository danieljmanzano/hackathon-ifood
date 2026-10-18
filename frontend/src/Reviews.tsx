import { useEffect, useState, type FormEvent } from "react";
import type { Candidate, ReviewAspects, ReviewInput, UserReview, UserTastes } from "./types";

const aspects: [keyof ReviewAspects, string][] = [
  ["taste", "Sabor"],
  ["delivery", "Entrega"],
  ["value_for_money", "Custo-benefício"],
  ["portion_size", "Tamanho da porção"],
];

export function ReviewHistory({ reviews, simulated }: { reviews: UserReview[]; simulated: boolean }) {
  return (
    <section className="review-history">
      <h2>Suas avaliações</h2>
      <p className="muted">
        Suas notas ajudam a ordenar as próximas sugestões.
        {simulated && " Na demonstração, começamos com seis avaliações fictícias que você pode atualizar."}
      </p>
      {reviews.length === 0 && <p>Seu histórico está vazio. Abra um prato que você já provou para avaliá-lo.</p>}
      <div className="review-history-list">
        {reviews.map((review) => (
          <article key={`${review.merchant_id}-${review.item_id}`}>
            <strong>{review.merchant_name || "Restaurante avaliado"}</strong>
            <span aria-label={`Nota ${review.rating} de 5`}>★ {review.rating}/5</span>
            {review.item_name && <p>{review.item_name}</p>}
            <p>{review.comment}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function ReviewEditor({ item, previous, busy, onSave }: {
  item: Candidate;
  previous?: UserReview;
  busy: boolean;
  onSave: (input: ReviewInput) => Promise<boolean>;
}) {
  const [rating, setRating] = useState(previous?.rating || 3);
  const [comment, setComment] = useState(previous?.comment || "");
  const [scores, setScores] = useState<ReviewAspects>(previous?.aspects || {
    taste: 3, delivery: 3, value_for_money: 3, portion_size: 3,
  });
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    if (!previous) return;
    setRating(previous.rating);
    setComment(previous.comment);
    setScores(previous.aspects);
  }, [previous]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!comment.trim() || busy) return;
    const ok = await onSave({ merchant_id: item.merchant_id, item_id: item.item_id,
      rating, comment: comment.trim(), aspects: scores });
    setSaved(ok);
  }
  return (
    <details className="review-editor">
      <summary>Já provou? {previous ? "Atualize sua avaliação" : "Avalie este prato"}</summary>
      <form onSubmit={(event) => void submit(event)} onChange={() => setSaved(false)}>
        <p className="muted small">Sua avaliação fica salva nesta sessão e influencia a próxima busca.</p>
        <label className="form-field">Nota geral
          <select value={rating} onChange={(event) => setRating(Number(event.target.value))} disabled={busy}>
            {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}/5</option>)}
          </select>
        </label>
        <div className="review-aspects">
          {aspects.map(([key, label]) => (
            <label className="form-field" key={key}>{label}
              <select value={scores[key]} onChange={(event) => setScores({ ...scores, [key]: Number(event.target.value) })} disabled={busy}>
                {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}/5</option>)}
              </select>
            </label>
          ))}
        </div>
        <label className="form-field">Conte como foi
          <textarea required maxLength={2000} value={comment} onChange={(event) => setComment(event.target.value)} disabled={busy} />
        </label>
        <button className="primary-button" type="submit" disabled={busy || !comment.trim()}>Salvar avaliação</button>
        {saved && <p role="status">Avaliação salva. Sua próxima busca usará esta nota.</p>}
      </form>
    </details>
  );
}


export function TasteSummary({ tastes }: { tastes: UserTastes }) {
  const liked = Object.entries(tastes.cuisine_affinities).filter(([, value]) => value > 0).sort((a, b) => b[1] - a[1]);
  const avoided = Object.entries(tastes.cuisine_affinities).filter(([, value]) => value < 0);
  const labels: Record<string, string> = {
    freshness: "frescor dos ingredientes", lightness: "comida com pouco óleo",
    portion: "tamanho da porção", delivery: "rapidez da entrega", value: "custo-benefício",
  };
  return (
    <section className="review-history">
      <h2>Gostos aprendidos e salvos</h2>
      <p className="muted">Com base em {tastes.history_count} avaliações. Atualizamos estas afinidades quando você avalia um prato.</p>
      {liked.length > 0 ? <p><strong>Cozinhas com maior afinidade: </strong>{liked.map(([name]) => name).join(", ")}.</p>
        : <p>Ainda não há sinais suficientes para indicar suas cozinhas favoritas.</p>}
      {avoided.length > 0 && <p><strong>Menor afinidade: </strong>{avoided.map(([name]) => name).join(", ")}.</p>}
      {Object.keys(tastes.trait_interests).length > 0 && <p><strong>Aspectos que você mencionou: </strong>{Object.keys(tastes.trait_interests).map((key) => labels[key] || key).join(", ")}.</p>}
      <p className="muted small">Esses sinais são estimativas. As preferências e restrições que você informa ficam separadas. {tastes.simulated && "Inclui avaliações fictícias da demonstração."}</p>
    </section>
  );
}
