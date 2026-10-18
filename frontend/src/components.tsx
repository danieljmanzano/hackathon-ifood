import { useEffect, useId, useRef } from "react";
import {
  ArrowUpRight,
  Check,
  Flame,
  Info,
  LoaderCircle,
  Minus,
  Plus,
  Sparkles,
  X,
} from "lucide-react";
import { money, safeUrl } from "./api";
import type { Candidate, Nutrition, Recommendation } from "./types";

export function Brand({ small = false }: { small?: boolean }) {
  return (
    <span className={`brand ${small ? "brand-small" : ""}`}>
      <span className="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 36 32">
          <path
            d="M4 26V7h6l8 10 8-10h6v19h-7V17l-7 9-7-9v9z"
            fill="currentColor"
          />
        </svg>
      </span>
      {!small && (
        <span>
          macro<span className="brand-dot">.</span>
        </span>
      )}
    </span>
  );
}
export function Spinner({ text = "Carregando…" }: { text?: string }) {
  return (
    <span className="loading-label" role="status">
      <LoaderCircle className="spin" size={18} />
      {text}
    </span>
  );
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
  busy = false,
  error,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
  busy?: boolean;
  error?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const element = ref.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? "modal-wide" : ""}`}
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <div className="modal-header">
        <h2 id={titleId}>{title}</h2>
        <button
          className="icon-button"
          onClick={onClose}
          disabled={busy}
          aria-label="Fechar janela"
        >
          <X size={21} />
        </button>
      </div>
      {error && (
        <div className="inline-error" role="alert">
          {error}
        </div>
      )}
      {children}
    </dialog>
  );
}
export function Stepper({
  value,
  max = 20,
  min = 1,
  onChange,
  label,
}: {
  value: number;
  max?: number;
  min?: number;
  onChange: (n: number) => void;
  label: string;
}) {
  return (
    <div className="stepper" role="group" aria-label={label}>
      <button
        type="button"
        aria-label={`Diminuir ${label}`}
        disabled={value <= min}
        onClick={() => onChange(value - 1)}
      >
        <Minus size={15} />
      </button>
      <span aria-live="polite">{value}</span>
      <button
        type="button"
        aria-label={`Aumentar ${label}`}
        disabled={value >= max}
        onClick={() => onChange(value + 1)}
      >
        <Plus size={15} />
      </button>
    </div>
  );
}
export const photos = {
  hero: "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=85",
  chicken:
    "https://images.unsplash.com/photo-1532550907401-a500c9a57435?auto=format&fit=crop&w=700&q=85",
  plant:
    "https://images.unsplash.com/photo-1511690743698-d9d85f2fbf38?auto=format&fit=crop&w=700&q=85",
  comfort:
    "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=700&q=85",
};
export function itemPhoto(item: Candidate) {
  if (safeUrl(item.image_url)) return safeUrl(item.image_url);
  if (!item.simulated) return undefined;
  return item.item_id === "demo-frango"
    ? photos.chicken
    : item.item_id === "demo-vegetal"
      ? photos.plant
      : photos.comfort;
}
export function MealImage({
  item,
  className = "",
}: {
  item: Candidate;
  className?: string;
}) {
  const src = itemPhoto(item);
  return (
    <div className={`meal-image ${className}`}>
      {src ? (
        <img
          src={src}
          alt={
            item.simulated ? "Inspiração de apresentação do prato" : item.name
          }
          loading="lazy"
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
      ) : (
        <span className="image-placeholder">
          <Sparkles size={28} />
          Sem foto disponível
        </span>
      )}
      {item.simulated && (
        <span className="photo-caption">Foto ilustrativa</span>
      )}
    </div>
  );
}
const nutritionLabels = {
  pending: "Estimativa em andamento",
  ready: "Informação disponível",
  unavailable: "Nutrição indisponível",
  error: "Estimativa indisponível",
};
export function NutritionBadge({ nutrition }: { nutrition: Nutrition }) {
  return (
    <span className={`nutrition-badge ${nutrition.state}`}>
      <Flame size={13} />
      {nutrition.state === "ready"
        ? `${Math.round(nutrition.minimum!)}–${Math.round(nutrition.maximum!)} kcal`
        : nutritionLabels[nutrition.state]}
    </span>
  );
}
export function NutritionDetails({ nutrition }: { nutrition: Nutrition }) {
  return (
    <div className="nutrition-details">
      <h3>
        <Info size={17} />
        Sobre a informação nutricional
      </h3>
      {nutrition.state === "ready" ? (
        <>
          <p>
            <strong>
              {Math.round(nutrition.minimum!)}–{Math.round(nutrition.maximum!)}{" "}
              kcal
            </strong>{" "}
            ·{" "}
            {nutrition.method === "published"
              ? "Informação publicada"
              : "Estimativa"}{" "}
            por {nutrition.portion_basis}.
          </p>
          {nutrition.confidence && (
            <p>
              Confiança qualitativa{" "}
              {
                { low: "baixa", medium: "média", high: "alta" }[
                  nutrition.confidence
                ]
              }
              . Não representa uma probabilidade de acerto.
            </p>
          )}
          {nutrition.source_name && (
            <p>
              Fonte:{" "}
              {safeUrl(nutrition.source_url) ? (
                <a
                  href={safeUrl(nutrition.source_url)}
                  target="_blank"
                  rel="noreferrer"
                >
                  {nutrition.source_name} <ArrowUpRight size={12} />
                </a>
              ) : (
                nutrition.source_name
              )}
            </p>
          )}
          {nutrition.evidence && <p>{nutrition.evidence}</p>}
          {nutrition.assumptions.length > 0 && (
            <ul>
              {nutrition.assumptions.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <p>
          {nutrition.state === "pending"
            ? "Você pode escolher o prato enquanto a estimativa é preparada."
            : "Não há dados suficientes para mostrar calorias deste prato. Você pode continuar o pedido."}
        </p>
      )}
      <p className="muted small">
        Proteínas, carboidratos e gorduras ainda não estão disponíveis. A foto
        não comprova o tamanho da porção.
      </p>
    </div>
  );
}
export function MealCard({
  recommendation,
  index,
  onSelect,
  disabled,
}: {
  recommendation: Recommendation;
  index: number;
  onSelect: () => void;
  disabled: boolean;
}) {
  const { candidate: item, nutrition, reasons } = recommendation;
  return (
    <article className="meal-card">
      <div className="meal-card-photo">
        <MealImage item={item} />
        {index === 0 && (
          <span className="match-tag">
            <Sparkles size={12} />
            Primeira sugestão
          </span>
        )}
      </div>
      <div className="meal-card-body">
        <span className="merchant">{item.merchant_name}</span>
        <h3>{item.name}</h3>
        <p className="meal-description">{item.description}</p>
        <NutritionBadge nutrition={nutrition} />
        <p className="reason">
          <Check size={14} />
          {reasons[0]}
        </p>
        <div className="meal-card-footer">
          <div>
            <strong>{money(item.price_cents)}</strong>
            <span>+ entrega e adicionais</span>
          </div>
          <button
            onClick={onSelect}
            disabled={disabled}
            className="select-meal"
            aria-label={`Escolher ${item.name}`}
          >
            <Plus size={20} />
          </button>
        </div>
      </div>
    </article>
  );
}
