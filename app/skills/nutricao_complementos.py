"""Skill: separar as opções escolhidas em "base" (definem o item) e "adicional" (somam calorias por cima).

Quem usa: etapas/complementos.py -> separar_complementos. Só roda quando o usuário escolheu opções.
Modelo:   LLM de texto (OpenRouter ou OpenAI, com a reserva do outro).
Saída:    por opção, o tipo e, para os adicionais, gramas e kcal (e macros, se souber) de UMA unidade.
          O item base é calculado pelo resto do pipeline; os adicionais são somados no fim, vezes a quantidade.
"""
from . import item_pedido
from .comum import NUM, pedir_json

INSTRUCOES = """Você classifica as opções escolhidas para um item de delivery em dois tipos:
- "base": definem o próprio item e já fazem parte do valor dele: tamanho, sabor, tipo de massa ou de base, ponto da
  carne, remoções ("sem cebola"), trocas ("trocar arroz por salada") e opções sem calorias relevantes (talheres,
  "sem gelo", embalagem).
- "adicional": algo ACRESCENTADO ao item que soma calorias: coberturas, caldas, complementos, recheios extras,
  adicionais pagos, acompanhamentos e bebidas incluídos pela opção.
Para cada adicional, estime gramas e kcal de UMA unidade, na porção usual de delivery no Brasil (ex.: uma cobertura de
açaí costuma ter de 20 a 40 g). Informe proteína, carboidrato e gordura dessa unidade se souber; senão, null.
Não estime o item base. Identifique cada opção pelo número dela na lista (campo "indice")."""

SCHEMA = {
    "type": "object",
    "properties": {
        "opcoes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "indice": {"type": "integer"},
                    "opcao": {"type": "string"},
                    "tipo": {"type": "string", "enum": ["base", "adicional"]},
                    "gramas_por_unidade": NUM,
                    "kcal_por_unidade": NUM,
                    "proteina_g": NUM,
                    "carbo_g": NUM,
                    "gordura_g": NUM,
                },
                "required": ["tipo", "gramas_por_unidade", "kcal_por_unidade"],
            },
        }
    },
    "required": ["opcoes"],
}

PEDIDO = "Classifique as opções escolhidas deste item.\n\n"
OPCOES = "Opções a classificar (número. grupo: opção):\n"


def pedido(item: str, opcoes: list[tuple[str, str]]) -> str:
    """`opcoes`: (nome do grupo, nome da opção), numeradas na ordem; a resposta cita o número (índice)."""
    linhas = "\n".join(f"{i}. {grupo}: {nome}" if grupo else f"{i}. {nome}"
                        for i, (grupo, nome) in enumerate(opcoes))
    return f"{PEDIDO}{item}\n\n{OPCOES}{linhas}"


def exemplo() -> list[tuple[str, str]]:
    item = item_pedido.descrever("Açaí 300ml", "Açaí da Praça", "Copo de açaí cremoso. Monte do seu jeito.",
                                 ["1 × Tradicional", "2 × Nutella", "1 × Paçoca"], [])
    opcoes = [("Escolha o açaí", "Tradicional"), ("Coberturas", "Nutella"), ("Coberturas", "Paçoca")]
    return [("sistema", INSTRUCOES), ("usuário", pedir_json(pedido(item, opcoes), SCHEMA))]
