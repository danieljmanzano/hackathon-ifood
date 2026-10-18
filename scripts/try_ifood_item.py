"""Teste manual: chama getItem no MCP do iFood e imprime a resposta crua (para conferir o formato real).

Uso: .venv/bin/python -m scripts.try_ifood_item MERCHANT_ID ITEM_ID LATITUDE LONGITUDE
"""
import asyncio
import json
import sys

from app.services.ifood_mcp import ifood_session


async def main() -> None:
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    merchant_id, item_id, lat, lon = sys.argv[1:]
    async with ifood_session() as session:
        resposta = await session.call_tool("getItem", {
            "merchantId": merchant_id, "itemId": item_id,
            "userLocation": {"latitude": float(lat), "longitude": float(lon)},
        })
        for bloco in resposta.content:
            texto = getattr(bloco, "text", None)
            if texto:
                try:
                    print(json.dumps(json.loads(texto), indent=2, ensure_ascii=False))
                except ValueError:
                    print(texto)


if __name__ == "__main__":
    asyncio.run(main())
