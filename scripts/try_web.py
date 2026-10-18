"""Teste manual da busca na web (Gemini + Google Search) e do juiz de correspondência.

Uso: .venv/bin/python -m scripts.try_web [item.json]
"""
import asyncio
import sys

from app.core.config import get_settings
from app.services.nutrition.etapas.web import buscar_na_web
from scripts._item import carregar_item


async def main() -> None:
    item = carregar_item(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"Buscando: {item.name} ({item.merchant_name})")
    info = await buscar_na_web(get_settings(), item, None)
    print(info if info else "Nada confiável encontrado (fonte ausente, fora das consultadas ou juiz rejeitou).")


if __name__ == "__main__":
    asyncio.run(main())
