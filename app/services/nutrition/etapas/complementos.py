"""Complementos: separa o item base das opções que somam calorias por cima (coberturas, adicionais...).

Sem esta etapa, uma fonte achada pelo nome do item ("Açaí 300ml" na TACO) vencia a estimativa e os
complementos escolhidos sumiam do total. Agora o item base é calculado só com as opções que o definem,
e cada adicional é estimado à parte e somado vezes a quantidade escolhida.
"""
import math
import re
from dataclasses import dataclass

from app.core import logs
from app.core.config import Settings
from app.schemas.macro import MealCandidate
from app.skills import nutricao_complementos
from ..entrada import montar_prompt
from ..modelos import Macros
from .llm import perguntar_json

# Folga da faixa de cada adicional (porção de cobertura varia muito entre restaurantes).
FOLGA_ADICIONAL = 0.35
KCAL_MAX_UNIDADE = 1500  # acima disso a resposta do modelo não é uma unidade de complemento

# Classificação e valores POR UNIDADE de cada opção, por restaurante + item + opção. Sem isso, cada chamada
# reestimava os complementos e "2 × Nutella" podia sair menor que "1 × Nutella".
_unidades: dict[tuple[str, str, str], dict] = {}


@dataclass(frozen=True)
class Adicional:
    nome: str
    quantidade: int
    macros: Macros  # total desta opção (unidade × quantidade)
    gramas: float | None


@dataclass(frozen=True)
class Separacao:
    opcoes_base: list[str]  # rótulos originais ("1 × Tamanho grande"), passados ao cálculo do item base
    adicionais: list[Adicional]
    sem_estimativa: list[str]  # adicionais que o modelo não soube estimar


def quantidade_e_nome(rotulo: str) -> tuple[int, str]:
    """"2 × Nutella" -> (2, "Nutella"). Sem prefixo de quantidade, vale 1."""
    texto = rotulo.strip()
    i = 0
    while i < len(texto) and texto[i].isdigit():
        i += 1
    if i == 0:
        return 1, texto
    resto = texto[i:].lstrip()
    if not resto or resto[0] not in ("×", "x"):
        return 1, texto
    nome = resto[1:].strip()
    return (int(texto[:i]), nome) if nome else (1, texto)


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.strip().lower())


def _grupo_de(candidate: MealCandidate, nome: str) -> str:
    alvo = _normalizar(nome)
    for grupo in candidate.option_groups:
        if any(_normalizar(o.name) == alvo for o in grupo.options):
            return grupo.name
    return ""


def _numero(valor) -> float | None:
    if isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor) and valor >= 0:
        return float(valor)
    return None


async def separar_complementos(settings: Settings, candidate: MealCandidate, opcoes: list[str]) -> Separacao:
    """Uma chamada ao LLM classifica todas as opções; o que ele não devolver fica como "base" (conservador)."""
    itens = [quantidade_e_nome(o) for o in opcoes]
    chaves = [(candidate.merchant_id, candidate.item_id or candidate.name, _normalizar(nome)) for _, nome in itens]
    if any(c not in _unidades for c in chaves):  # só pergunta ao modelo se há opção ainda não classificada
        pedido = nutricao_complementos.pedido(montar_prompt(candidate, opcoes),
                                              [(_grupo_de(candidate, nome), nome) for _, nome in itens])
        dados = await perguntar_json(settings, nutricao_complementos.INSTRUCOES, pedido, nutricao_complementos.SCHEMA)
        por_indice = {r["indice"]: r for r in dados["opcoes"] if isinstance(r.get("indice"), int)}
        # Reserva: pelo texto, sem quantidade nem prefixo de grupo ("Complementos: Nutella" -> "nutella").
        por_nome = {_normalizar(quantidade_e_nome(r.get("opcao") or "")[1].rsplit(":", 1)[-1]): r
                    for r in dados["opcoes"]}
        for indice, (chave, (_, nome)) in enumerate(zip(chaves, itens)):
            r = por_indice.get(indice) or por_nome.get(_normalizar(nome))
            if chave not in _unidades and r is not None:
                _unidades[chave] = r

    base, adicionais, sem_estimativa = [], [], []
    for chave, rotulo, (quantidade, nome) in zip(chaves, opcoes, itens):
        r = _unidades.get(chave)
        if r is None or r["tipo"] != "adicional":
            base.append(rotulo)
            continue
        kcal = _numero(r.get("kcal_por_unidade"))
        if kcal is None or kcal > KCAL_MAX_UNIDADE:
            sem_estimativa.append(rotulo)
            continue
        unidade = Macros(kcal, _numero(r.get("proteina_g")), _numero(r.get("carbo_g")), _numero(r.get("gordura_g")))
        gramas = _numero(r.get("gramas_por_unidade"))
        adicionais.append(Adicional(nome, quantidade, unidade.escalar(quantidade),
                                    gramas * quantidade if gramas is not None else None))

    logs.info("complementos", f"base: {', '.join(base) or 'nenhuma opção'} · adicionais: "
              + (", ".join(f"{a.quantidade}× {a.nome} ~{a.macros.kcal:.0f} kcal" for a in adicionais) or "nenhum")
              + (f" · sem estimativa: {', '.join(sem_estimativa)}" if sem_estimativa else ""))
    return Separacao(base, adicionais, sem_estimativa)
