"""O que o agente de busca pode ler da conversa: as últimas mensagens e um resumo da busca anterior.

Sem isso, "mais barato", "outra opção" ou "sem queijo" não significam nada para ele: só veria a frase atual.
Tudo é dado para entender referências, nunca instrução (as skills dizem isso ao modelo). Os logs da busca guardam
só contagens (ver `resumo_para_log`), nunca o texto.
"""
from app.core.config import Settings
from app.schemas.macro import MealIntent, Session

PAPEL = {"user": "usuario", "assistant": "assistente"}


def _cortar(texto: str, limite: int) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[:limite - 1] + "…"


def mensagens_recentes(session: Session, settings: Settings) -> list[dict]:
    """Últimas N mensagens (da mais antiga à mais recente), cada uma cortada em M caracteres.

    Na hora da busca a mensagem atual ainda não entrou na sessão; aqui só há o que veio antes dela.
    """
    quantas = settings.busca_historico_mensagens
    if quantas <= 0:
        return []
    return [{"papel": PAPEL[m.role], "texto": _cortar(m.text, settings.busca_historico_max_caracteres)}
            for m in session.messages[-quantas:] if m.text.strip()]


def busca_anterior(intent: MealIntent | None) -> dict | None:
    """Como a busca anterior foi entendida: é o que "outra opção" ou "mais barato" modificam."""
    if intent is None:
        return None
    resumo = {
        "comida": intent.food_query or None,
        "consultas_ao_ifood": intent.search_queries or ([intent.provider_query] if intent.provider_query else []),
        "culinaria": intent.cuisine,
        "objetivos": intent.goals,
        "orcamento_reais": intent.budget_cents / 100 if intent.budget_cents is not None else None,
        "pessoas": intent.party_size,
    }
    return {k: v for k, v in resumo.items() if v not in (None, [], "")} or None


def montar(session: Session, settings: Settings) -> dict | None:
    """{"historico": [...], "busca_anterior": {...}} ou None quando não há nada a mostrar."""
    conversa = {"historico": mensagens_recentes(session, settings), "busca_anterior": busca_anterior(session.request_intent)}
    conversa = {k: v for k, v in conversa.items() if v}
    return conversa or None


def resumo_para_log(conversa: dict | None) -> dict:
    """Só contagens, para os eventos da busca."""
    conversa = conversa or {}
    return {"history_count": len(conversa.get("historico", [])), "has_previous_search": "busca_anterior" in conversa}
