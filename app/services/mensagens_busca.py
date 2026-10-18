"""Mensagens ao usuário quando a busca não tem o que mostrar: cada motivo tem a sua, e todas pedem outra coisa.

Ordem de decisão (a primeira que valer):
  1. nada veio do iFood                       -> não achei isso perto de você
  2. veio, mas todos os restaurantes fechados -> não há nada aberto agora
  3. há abertos, mas todos acima do orçamento -> nenhum cabe no orçamento (diz o preço mais baixo)
  4. há abertos, mas só sobrou o que já foi mostrado -> peça outro sabor/estilo
  5. há abertos, mas os filtros cortaram tudo -> restrições/preferências
"""
from app.schemas.macro import MealCandidate

PEDIR_OUTRA_COISA = "Peça outra coisa, como um prato específico (pizza, hambúrguer, marmita) ou outro tipo de comida."

GENERICAS = {"refeição", "refeicao", "comida", ""}


def _reais(centavos: int) -> str:
    return f"R$ {centavos / 100:.2f}".replace(".", ",")


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def sem_resultado(candidates: list[MealCandidate], budget_cents: int | None, consultas: list[str],
                  ja_mostrados: int = 0) -> str:
    """Texto para quando nenhuma recomendação sobrou."""
    if not candidates:
        alvo = next((c for c in consultas if c.strip().lower() not in GENERICAS), "")
        procurado = f"“{alvo}”" if alvo else "opções"
        return f"Não encontrei {procurado} perto de você agora. {PEDIR_OUTRA_COISA}"

    abertos = [c for c in candidates if c.available]
    if not abertos:
        restaurantes = len({c.merchant_id for c in candidates})
        return (f"Encontrei {_plural(len(candidates), 'item', 'itens')} de "
                f"{_plural(restaurantes, 'restaurante', 'restaurantes')}, mas todos estão fechados agora, "
                f"então não há opções abertas para esse pedido. {PEDIR_OUTRA_COISA} "
                "Ou tente de novo quando abrirem.")

    if ja_mostrados and ja_mostrados >= len(abertos):  # pediu "diferente" e só sobrou o que já viu
        return ("Já mostrei todas as opções abertas que encontrei para esse pedido. "
                f"Peça outro sabor ou estilo, ou {PEDIR_OUTRA_COISA[0].lower()}{PEDIR_OUTRA_COISA[1:]}")

    if budget_cents is not None and all(c.price_cents > budget_cents for c in abertos):
        mais_barato = min(c.price_cents for c in abertos)
        return (f"Há opções abertas, mas nenhuma cabe no orçamento de {_reais(budget_cents)}: a mais barata custa "
                f"{_reais(mais_barato)}. Aumente o orçamento ou peça outra coisa.")

    return ("Há opções abertas, mas nenhuma passou pelos seus filtros (restrições ou alimentos que você evita). "
            f"Ajuste suas preferências ou {PEDIR_OUTRA_COISA[0].lower()}{PEDIR_OUTRA_COISA[1:]}")
