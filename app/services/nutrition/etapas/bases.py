"""Bases de dados: carga da TACO, busca por título (fuzzy) e juiz com abstenção."""
import csv
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz, process

from app.core import logs
from app.core.config import Settings
from app.schemas.macro import MealCandidate
from ..modelos import InfoOnline, Macros
from app.skills import nutricao_bases
from .llm import perguntar_json


@dataclass(frozen=True)
class Alimento:
    nome: str
    categoria: str
    macros: Macros  # por 100 g


def normalizar_texto(texto: str) -> str:
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", sem_acento.lower())).strip()


def _opcional(valor: str) -> float | None:
    try:
        return float(valor)
    except ValueError:
        return None


@lru_cache(maxsize=4)
def carregar_taco(pasta: str) -> tuple[Alimento, ...]:
    """Alimentos da TACO (valores por 100 g). Vazio se o arquivo não existir."""
    arquivo = Path(pasta) / "taco.csv"
    if not arquivo.exists():
        return ()
    with arquivo.open(encoding="utf-8", newline="") as f:
        return tuple(
            Alimento(r["nome"], r["categoria"], Macros(float(r["kcal"]), _opcional(r["proteina_g"]),
                                                       _opcional(r["carbo_g"]), _opcional(r["gordura_g"])))
            for r in csv.DictReader(f) if _opcional(r["kcal"]) is not None
        )


def _pontuar(consulta: str, nome: str, **_) -> float:
    """Palavras em comum (token_set) + bônus quando o alimento principal (1ª palavra) coincide.

    Os nomes da TACO começam pelo alimento ("Arroz, tipo 1, cozido"), então a 1ª palavra pesa mais.
    """
    c, n = consulta.split(), nome.split()
    bonus = 20 if c and n and fuzz.ratio(c[0], n[0]) >= 80 else 0
    return min(100, fuzz.token_set_ratio(consulta, nome) * 0.8 + bonus)


def candidatos(alimentos: tuple[Alimento, ...] | list[Alimento], consulta: str, n: int = 8,
               minimo: float = 60) -> list[Alimento]:
    """Melhores alimentos por similaridade de título (rapidfuzz), do mais para o menos parecido."""
    if not alimentos or not normalizar_texto(consulta):
        return []
    nomes = [normalizar_texto(a.nome) for a in alimentos]
    achados = process.extract(normalizar_texto(consulta), nomes, scorer=_pontuar, limit=n, score_cutoff=minimo)
    return [alimentos[indice] for _, _, indice in achados]


async def escolher_alimento(settings: Settings, descricao: str, opcoes: list[Alimento]) -> Alimento | None:
    """Juiz LLM: escolhe um candidato ou se abstém (None)."""
    if not opcoes:
        return None
    pedido = nutricao_bases.pedido(descricao, [(a.nome, a.categoria) for a in opcoes])
    dados = await perguntar_json(settings, nutricao_bases.INSTRUCOES, pedido, nutricao_bases.SCHEMA)
    escolha = dados["escolha"]
    if escolha is None or not 0 <= escolha < len(opcoes):
        logs.info("bases", f"juiz se absteve: {logs.curto(dados['motivo'], 160)}")
        return None
    logs.info("bases", f"juiz escolheu: {opcoes[escolha].nome} ({logs.curto(dados['motivo'], 120)})")
    return opcoes[escolha]


async def consultar_bases(settings: Settings, candidate: MealCandidate, descricao: str) -> InfoOnline | None:
    """Procura o item pelo título nas bases locais; só devolve se o juiz confirmar."""
    alimentos = carregar_taco(str(settings.calorias_dados_dir))
    if not alimentos:
        logs.aviso("bases", f"taco.csv não encontrado em {settings.calorias_dados_dir}")
        return None
    achados = candidatos(alimentos, candidate.name)
    if not achados:
        logs.info("bases", f"nenhum candidato parecido com \"{candidate.name}\" entre {len(alimentos)} alimentos da TACO")
        return None
    logs.info("bases", f"{len(achados)} candidatos na TACO para \"{candidate.name}\"")
    logs.detalhe("bases", "candidatos: " + "; ".join(a.nome for a in achados))
    alimento = await escolher_alimento(settings, descricao, achados)
    if alimento is None:
        return None
    m = alimento.macros
    return InfoOnline(
        macros=m, base="100g", porcao_base="100 g", fonte_nome="TACO", fonte_url=None, method="database",
        evidencia=f"“{alimento.nome}” ({alimento.categoria}): {m.kcal:g} kcal por 100 g na Tabela TACO.",
    )
