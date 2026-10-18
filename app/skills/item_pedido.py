"""Skill: como o ITEM do cardápio é descrito ao modelo (nome, restaurante, descrição, opções e peso).

Quem usa: todos os prompts do pipeline de calorias (estimativa A e B, decomposição, juízes e pesquisa na web).
Entrada:  dados do prato vindos do iFood (MCP) + opções escolhidas + peso declarado, se houver.
Saída:    um bloco de texto que é colado dentro do pedido de cada skill de nutrição.
"""

NOME = "Nome: "
RESTAURANTE = "Restaurante: "
DESCRICAO = "Descrição: "
SEM_DESCRICAO = "(sem descrição)"

OPCOES_ESCOLHIDAS = "Opções escolhidas:\n"
OPCOES_NENHUMA = "Opções escolhidas: nenhuma"
# Quando o usuário ainda não escolheu (lista de pratos): o modelo deve cobrir a variação na faixa.
OPCOES_NAO_ESCOLHIDAS = (
    "Opções ainda não escolhidas. Estime para a combinação mais provável e reflita a variação "
    "entre as opções na faixa:\n"
)
GRUPO_OBRIGATORIO = "obrigatório"
GRUPO_OPCIONAL = "opcional"

PESO_DECLARADO = "Peso informado do prato: "


def descrever(
    nome: str,
    restaurante: str,
    descricao: str,
    opcoes: list[str] | None,
    grupos: list[tuple[str, bool, int, list[str]]],
    peso_g: float | None = None,
) -> str:
    """`grupos`: (nome do grupo, obrigatório?, máximo de escolhas, nomes das opções)."""
    if opcoes:
        texto_opcoes = OPCOES_ESCOLHIDAS + "\n".join(f"- {o}" for o in opcoes)
    elif opcoes is None and grupos:
        linhas = []
        for grupo, obrigatorio, maximo, nomes in grupos:
            regra = GRUPO_OBRIGATORIO if obrigatorio else GRUPO_OPCIONAL
            linhas.append(f"- {grupo} ({regra}, até {maximo}): " + ", ".join(nomes))
        texto_opcoes = OPCOES_NAO_ESCOLHIDAS + "\n".join(linhas)
    else:
        texto_opcoes = OPCOES_NENHUMA
    peso = f"\n{PESO_DECLARADO}{peso_g:g} g" if peso_g else ""
    return (
        f"{NOME}{nome}\n"
        f"{RESTAURANTE}{restaurante}\n"
        f"{DESCRICAO}{descricao or SEM_DESCRICAO}\n"
        f"{texto_opcoes}{peso}"
    )


def exemplo() -> list[tuple[str, str]]:
    item = descrever(
        "Pizza Margherita",
        "Pizza Express",
        "Mussarela e manjericão. 35cm, serves 1-2.",
        None,
        [("Borda", False, 1, ["Catupiry", "Cheddar"])],
    )
    escolhido = descrever("Pizza Margherita", "Pizza Express", "", ["Catupiry"], [], 400.0)
    return [("item, opções ainda não escolhidas", item), ("item, com opções e peso", escolhido)]
