"""Entrada do pipeline: prompt do item, imagem e leitura do JSON dos modelos."""
import json
import re

import httpx

from app.core import logs
from app.schemas.macro import MealCandidate

MAX_IMAGEM_BYTES = 5 * 1024 * 1024
RESTAURANTES_INVALIDOS = {"", "não informado", "nao informado", "desconhecido", "n/a", "na", "null", "none", "-"}


def restaurante_valido(candidate: MealCandidate) -> bool:
    nome = candidate.merchant_name.strip().lower()
    return not candidate.simulated and nome not in RESTAURANTES_INVALIDOS


def foto_ilustrativa(candidate: MealCandidate) -> bool:
    return "ilustrativ" in candidate.description.lower()


def montar_prompt(candidate: MealCandidate, opcoes: list[str] | None, peso_g: float | None = None) -> str:
    if opcoes:
        texto_opcoes = "Opções escolhidas:\n" + "\n".join(f"- {o}" for o in opcoes)
    elif opcoes is None and candidate.option_groups:
        grupos = []
        for g in candidate.option_groups:
            regra = "obrigatório" if g.min_selections else "opcional"
            grupos.append(f"- {g.name} ({regra}, até {g.max_selections}): " + ", ".join(o.name for o in g.options))
        texto_opcoes = ("Opções ainda não escolhidas. Estime para a combinação mais provável e reflita a variação "
                        "entre as opções na faixa:\n" + "\n".join(grupos))
    else:
        texto_opcoes = "Opções escolhidas: nenhuma"
    peso = f"\nPeso informado do prato: {peso_g:g} g" if peso_g else ""
    return (f"Nome: {candidate.name}\n"
            f"Restaurante: {candidate.merchant_name}\n"
            f"Descrição: {candidate.description or '(sem descrição)'}\n"
            f"{texto_opcoes}{peso}")


async def baixar_imagem(url: str | None, timeout: float) -> tuple[bytes, str] | None:
    """Imagem (bytes, tipo MIME), ou None se não houver ou o download falhar."""
    if not url or not url.startswith("https://"):
        return None
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0"}) as http:
            resp = await http.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logs.aviso("imagem", f"download falhou: {logs.curto(e, 120)}")
        return None
    tipo = resp.headers.get("Content-Type", "").split(";")[0]
    if not tipo.startswith("image/") or len(resp.content) > MAX_IMAGEM_BYTES:
        return None
    return resp.content, tipo


def extrair_json(texto: str) -> dict:
    """JSON da resposta do modelo, tolerando cercas de markdown e texto ao redor."""
    texto = texto.strip()
    cercado = re.search(r"```(?:json)?\s*(.*?)```", texto, re.DOTALL)
    if cercado:
        texto = cercado.group(1).strip()
    elif not texto.startswith("{"):
        inicio, fim = texto.find("{"), texto.rfind("}")
        if inicio != -1 and fim > inicio:
            texto = texto[inicio:fim + 1]
    return json.loads(texto)
