"""Run with python -m backend.diagnose_mcp. Never prints tokens or personal data."""
import asyncio
import json

from .app.config import Settings
from .app.errors import MacroError
from .app.ifood.mcp import MCPIFood


async def main():
    provider = MCPIFood(Settings())
    try:
        result = await provider.diagnostic()
        addresses = await provider.addresses()
        print(json.dumps({**result, "address_count": len(addresses)}, ensure_ascii=False, indent=2))
    except MacroError as exc:
        print(json.dumps({"connected": False, "message": exc.message}, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
