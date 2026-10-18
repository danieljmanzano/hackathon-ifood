import { useState, type FormEvent } from "react";
import { Check, MapPin, Plus } from "lucide-react";
import { Spinner } from "./components";
import type { Address, GeocodeResult, NewAddress } from "./types";

/** Escolha do endereço de entrega na conversa, com cadastro de um novo endereço. */
export function AddressPicker({
  addresses,
  current,
  simulated,
  busy,
  disabled,
  adding,
  onAdding,
  onSelect,
  onGeocode,
  onCreate,
  onCancel,
}: {
  addresses: Address[];
  current: Address | null;
  simulated: boolean;
  busy: boolean;
  disabled: boolean;
  adding: boolean;
  onAdding: (open: boolean) => void;
  onSelect: (address: Address) => void;
  onGeocode: (address: string) => Promise<GeocodeResult | undefined>;
  onCreate: (payload: NewAddress) => Promise<boolean>;
  onCancel?: () => void;
}) {
  return (
    <section className="chat-action" aria-label="Endereço de entrega">
      <h2>{current ? "Onde vamos entregar?" : "Qual endereço vamos usar?"}</h2>
      {addresses.map((address, index) => (
        <button
          className={`choice-button ${current?.id === address.id ? "selected" : ""}`}
          key={address.id}
          disabled={disabled}
          aria-pressed={current?.id === address.id}
          onClick={() => onSelect(address)}
        >
          <span>
            {index + 1}. {address.label}
            <small className="address-formatted">{address.formatted}</small>
          </span>
          {current?.id === address.id && <Check size={17} aria-label="Endereço atual" />}
        </button>
      ))}
      {!addresses.length && !adding && (
        <p>Nenhum endereço salvo ainda. Adicione um para receber a entrega.</p>
      )}
      {adding ? (
        <NewAddressForm
          busy={busy}
          disabled={disabled}
          simulated={simulated}
          onGeocode={onGeocode}
          onCreate={onCreate}
          onCancel={() => onAdding(false)}
        />
      ) : (
        <div className="address-actions">
          <button className="secondary-button" disabled={disabled} onClick={() => onAdding(true)}>
            <Plus size={15} />
            Adicionar novo endereço
          </button>
          {onCancel && (
            <button className="secondary-button" disabled={disabled} onClick={onCancel}>
              Manter endereço atual
            </button>
          )}
        </div>
      )}
      {current && (
        <p className="small muted">
          Trocar o endereço limpa a busca e o prato escolhido para consultar a disponibilidade de
          novo.
        </p>
      )}
    </section>
  );
}

/** Cadastro em duas etapas do iFood: localizar o endereço e depois confirmar o local com os detalhes. */
function NewAddressForm({
  busy,
  disabled,
  simulated,
  onGeocode,
  onCreate,
  onCancel,
}: {
  busy: boolean;
  disabled: boolean;
  simulated: boolean;
  onGeocode: (address: string) => Promise<GeocodeResult | undefined>;
  onCreate: (payload: NewAddress) => Promise<boolean>;
  onCancel: () => void;
}) {
  const [text, setText] = useState("");
  const [result, setResult] = useState<GeocodeResult | null>(null);
  const [candidateId, setCandidateId] = useState("");
  const [neighborhood, setNeighborhood] = useState("");
  const [complement, setComplement] = useState("");
  const [reference, setReference] = useState("");
  const [alias, setAlias] = useState<NewAddress["alias"]>("");
  function pick(id: string, found: GeocodeResult) {
    setCandidateId(id);
    setNeighborhood(found.candidates.find((c) => c.candidate_id === id)?.neighborhood || "");
  }
  async function search(event: FormEvent) {
    event.preventDefault();
    if (text.trim().length < 5) return;
    const found = await onGeocode(text.trim());
    if (!found) return;
    setResult(found);
    if (found.candidates.length) pick(found.candidates[0].candidate_id, found);
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!candidateId || !neighborhood.trim()) return;
    await onCreate({
      address: text.trim(),
      candidate_id: candidateId,
      neighborhood: neighborhood.trim(),
      complement: complement.trim(),
      reference: reference.trim(),
      alias,
    });
  }

  return (
    <div className="new-address">
      <form onSubmit={(event) => void search(event)}>
        <label className="form-field">
          Novo endereço
          <input
            autoFocus
            maxLength={300}
            value={text}
            disabled={busy}
            placeholder="Rua, número, cidade e estado"
            onChange={(event) => {
              setText(event.target.value);
              setResult(null);
              setCandidateId("");
            }}
          />
          <small>Ex.: Avenida Paulista, 1578, São Paulo, SP</small>
        </label>
        {!result && (
          <div className="address-actions">
            <button type="button" className="secondary-button" disabled={busy} onClick={onCancel}>
              Cancelar
            </button>
            <button className="primary-button" disabled={disabled || text.trim().length < 5}>
              {busy ? <Spinner text="Procurando…" /> : "Buscar endereço"}
            </button>
          </div>
        )}
      </form>
      {result && (
        <form onSubmit={(event) => void save(event)}>
          <p className="small muted">
            {result.match === "MULTIPLE"
              ? "Encontramos mais de um local. Escolha o certo:"
              : "Confira o local encontrado:"}
          </p>
          {!result.candidates.length && (
            <p className="small">Nenhum local encontrado. Revise rua, número e cidade.</p>
          )}
          <div className="address-candidates">
            {result.candidates.map((c) => (
              <label
                key={c.candidate_id}
                className={`address-choice ${candidateId === c.candidate_id ? "selected" : ""}`}
              >
                <input
                  type="radio"
                  name="address-candidate"
                  checked={candidateId === c.candidate_id}
                  onChange={() => pick(c.candidate_id, result)}
                />
                <MapPin size={18} />
                <strong>{c.formatted}</strong>
              </label>
            ))}
          </div>
          <div className="form-columns">
            <label className="form-field">
              Bairro
              <input
                required
                maxLength={200}
                value={neighborhood}
                onChange={(event) => setNeighborhood(event.target.value)}
                placeholder="Obrigatório"
              />
            </label>
            <label className="form-field">
              Complemento
              <input
                maxLength={200}
                value={complement}
                onChange={(event) => setComplement(event.target.value)}
                placeholder="Apto, bloco, sala…"
              />
            </label>
            <label className="form-field">
              Ponto de referência
              <input
                maxLength={200}
                value={reference}
                onChange={(event) => setReference(event.target.value)}
                placeholder="Portão azul, perto da padaria…"
              />
            </label>
            <label className="form-field">
              Apelido
              <select
                value={alias}
                onChange={(event) => setAlias(event.target.value as NewAddress["alias"])}
              >
                <option value="">Sem apelido</option>
                <option value="CASA">Casa</option>
                <option value="TRABALHO">Trabalho</option>
              </select>
            </label>
          </div>
          <p className="small muted">
            {simulated
              ? "Demonstração: o endereço fica salvo só neste aplicativo."
              : "O endereço fica salvo na sua conta do iFood. Algumas regiões exigem complemento e ponto de referência."}
          </p>
          <div className="address-actions">
            <button type="button" className="secondary-button" disabled={busy} onClick={onCancel}>
              Cancelar
            </button>
            <button
              className="primary-button"
              disabled={disabled || !candidateId || !neighborhood.trim()}
            >
              {busy ? <Spinner text="Salvando…" /> : "Salvar e entregar aqui"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
