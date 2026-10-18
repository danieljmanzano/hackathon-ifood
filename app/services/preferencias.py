"""Preferências do cliente (gostos, aversões, restrições) em texto, para entregar aos modelos.

Valor fixo por enquanto: a feature de preferências troca `preferencias_do_cliente` por um texto montado a partir do
perfil (e do que o cliente já avaliou). Quem usa: interpretação do pedido (llm_meal_intent) e montagem do pedido.
"""

from app.schemas.macro import UserProfile

PREFERENCIAS_DO_CLIENTE = "Sem preferências registradas."


def preferencias_do_cliente(profile: UserProfile | None = None) -> str:
    return PREFERENCIAS_DO_CLIENTE
