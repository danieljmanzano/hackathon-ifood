"""Entrada do pipeline: prompt do item, imagem e leitura do JSON dos modelos."""
import json
import re

import httpx

from app.core import logs
from app.schemas.macro import MealCandidate
from app.skills import item_pedido

MAX_IMAGEM_BYTES = 5 * 1024 * 1024
RESTAURANTES_INVALIDOS = {"", "não informado", "nao informado", "desconhecido", "n/a", "na", "null", "none", "-"}


def restaurante_valido(candidate: MealCandidate) -> bool:
    nome = candidate.merchant_name.strip().lower()
    return not candidate.simulated and nome not in RESTAURANTES_INVALIDOS


def foto_ilustrativa(candidate: MealCandidate) -> bool:
    return "ilustrativ" in candidate.description.lower()


def montar_prompt(candidate: MealCandidate, opcoes: list[str] | None, peso_g: float | None = None) -> str:
    """Texto do prato que vai nos pedidos ao modelo (o formato fica em app/skills/item_pedido.py)."""
    grupos = [(g.name, bool(g.min_selections), g.max_selections, [o.name for o in g.options])
              for g in candidate.option_groups]
    return item_pedido.descrever(candidate.name, candidate.merchant_name, candidate.description, opcoes, grupos, peso_g)


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
