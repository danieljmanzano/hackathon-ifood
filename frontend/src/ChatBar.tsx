import type { RefObject } from "react";
import { ArrowUp, MessageCircle } from "lucide-react";

interface ChatBarProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  busy: boolean;
  disabled: boolean;
  inDialog: boolean;
}

export default function ChatBar({
  value,
  onChange,
  onSend,
  inputRef,
  busy,
  disabled,
  inDialog,
}: ChatBarProps) {
  const canSend = !disabled && !busy && !!value.trim();

  return (
    <section
      className={`chat-dock${inDialog ? " chat-dock-dialog" : ""}`}
      aria-label="Conversa sempre disponível"
    >
      <div className="chat-dock-inner">
        <div className="chat-dock-heading">
          <label htmlFor="macro-message">
            <MessageCircle size={15} />
            Converse com o Macro
          </label>
          <span>{busy ? "Consultando opções…" : "Sempre por aqui"}</span>
        </div>
        <form
          className="chat-dock-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (canSend) onSend();
          }}
        >
          <textarea
            id="macro-message"
            ref={inputRef}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Conte o que você quer comer…"
            rows={2}
            maxLength={2000}
            aria-describedby="macro-message-help"
            onKeyDown={(event) => {
              if (
                event.key === "Enter" &&
                !event.shiftKey &&
                !event.nativeEvent.isComposing
              ) {
                event.preventDefault();
                if (canSend) onSend();
              }
            }}
          />
          <button
            type="submit"
            className="chat-send"
            disabled={!canSend}
            aria-label="Enviar mensagem ao Macro"
          >
            {busy ? <span className="button-spinner" /> : <ArrowUp size={21} />}
          </button>
        </form>
        <p id="macro-message-help" className="chat-dock-help">
          Enter envia. Shift + Enter quebra a linha. Você sempre revisa antes de
          confirmar um pedido.
        </p>
      </div>
    </section>
  );
}
