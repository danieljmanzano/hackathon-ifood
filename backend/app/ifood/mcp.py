"""Read-only MCP boundary. No write-tool dispatcher is exposed, even in live mode.

Response normalization follows the locally archived documentation and remains
provisional until tested with an authenticated account. Arguments must validate
against tools/list from the actual server before any tools/call.
"""
import asyncio
from contextlib import asynccontextmanager
from decimal import Decimal
import json

import httpx
from jsonschema import Draft202012Validator
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from ..config import Settings
from ..errors import MacroError
from ..schemas import Address, MealCandidate, Option, OptionGroup

READ_TOOLS = {"listAddresses", "searchOffers", "getItem", "getMerchant", "listItemTaxonomy"}


def cents(value) -> int:
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0 or amount * 100 != (amount * 100).to_integral_value():
        raise ValueError("Preço inválido")
    return int(amount * 100)


def unpack_result(result) -> dict:
    if result.isError:
        raise MacroError("O iFood recusou a consulta. Verifique a conta e tente novamente.", 502)
    data = result.structuredContent
    if data is None:
        parts = [c.text for c in result.content if c.type == "text"]
        if len(parts) != 1:
            raise MacroError("Formato MCP não reconhecido. Integração precisa ser validada.", 502)
        data = json.loads(parts[0])
    if not isinstance(data, dict):
        raise MacroError("Resposta MCP não reconhecida.", 502)
    if data.get("errors") or data.get("error") or data.get("errorType"):
        # External text is data, not operational instructions or permission.
        raise MacroError("O iFood retornou erro na consulta. Revise a seleção ou a autenticação.", 502)
    return data


class MCPIFood:
    simulated = False

    def __init__(self, settings: Settings):
        self.settings = settings

    @asynccontextmanager
    async def connection(self):
        token = self.settings.ifood_access_token.get_secret_value()
        if not token:
            raise MacroError("Configure MACRO_IFOOD_ACCESS_TOKEN no backend para consultar o iFood.", 503)
        try:
            async with asyncio.timeout(self.settings.mcp_timeout_seconds):
                async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"},
                                             timeout=self.settings.mcp_timeout_seconds) as client:
                    async with streamable_http_client(self.settings.ifood_endpoint, http_client=client) as (read, write, _):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            yield session
        except MacroError:
            raise
        except Exception:
            # Do not expose headers, personal payloads, or raw exception groups.
            raise MacroError("Não foi possível consultar o MCP. Verifique token, escopos e conexão; nenhuma compra foi enviada.", 503) from None

    async def tools(self, session):
        tools, cursor, seen = {}, None, set()
        for _ in range(20):
            page = await session.list_tools(cursor=cursor)
            tools.update({tool.name: tool for tool in page.tools})
            cursor = page.nextCursor
            if not cursor:
                return tools
            if cursor in seen:
                break
            seen.add(cursor)
        raise MacroError("Paginação de ferramentas MCP inválida.", 502)

    async def call_read(self, name: str, arguments: dict):
        if name not in READ_TOOLS:
            raise MacroError("Operações de escrita no iFood estão bloqueadas.", 403)
        async with self.connection() as session:
            tools = await self.tools(session)
            if name not in tools:
                raise MacroError(f"A ferramenta {name} não está disponível nesta conta.", 503)
            if list(Draft202012Validator(tools[name].inputSchema).iter_errors(arguments)):
                raise MacroError("O schema real diverge do adaptador. Valide o contrato antes de continuar.", 502)
            return unpack_result(await session.call_tool(name, arguments=arguments))

    async def diagnostic(self):
        async with self.connection() as session:
            tools = await self.tools(session)
            return {"connected": True, "simulated": False,
                    "tools": [{"name": t.name, "input_schema": t.inputSchema} for t in tools.values()],
                    "message": "Ferramentas listadas. Checkout real permanece bloqueado."}

    async def addresses(self):
        data = await self.call_read("listAddresses", {})
        try:
            return [Address(id=a["addressId"], label=a.get("alias") or "Endereço salvo", formatted=a["formattedAddress"],
                            **a["coordinates"]) for a in data["results"]]
        except (KeyError, TypeError, ValueError):
            raise MacroError("Resposta de endereço difere do contrato documentado.", 502) from None

    async def search(self, query: str, address: Address, budget_cents: int | None):
        refinements = {"onlyOpen": True}
        if budget_cents is not None:
            refinements["maxItemPrice"] = budget_cents / 100
        data = await self.call_read("searchOffers", {
            "query": query, "resultKind": "ITEM", "merchantType": "RESTAURANT", "pageSize": 10,
            "userLocation": {"latitude": address.latitude, "longitude": address.longitude}, "refinements": refinements})
        try:
            return [MealCandidate(merchant_id=i["merchant"]["merchantId"], merchant_name=i["merchant"]["merchantName"],
                                  item_id=i["itemId"], name=i["itemName"], description="Consulte os detalhes para ver a composição.",
                                  image_url=i.get("itemImageUrl"), available=i["merchant"].get("isOpen") is True,
                                  price_cents=cents(i.get("promotionalUnitPrice") if i.get("promotionalUnitPrice") is not None else i["unitPrice"]))
                    for i in data["results"]]
        except (KeyError, TypeError, ValueError, ArithmeticError):
            raise MacroError("Resultado de busca difere do contrato documentado.", 502) from None

    async def item(self, merchant_id: str, item_id: str, address: Address):
        args = {"merchantId": merchant_id, "userLocation": {"latitude": address.latitude, "longitude": address.longitude}}
        merchant = await self.call_read("getMerchant", args)
        if merchant.get("isOpen") is not True:
            raise MacroError("Restaurante indisponível. Escolha outra opção.")
        data = await self.call_read("getItem", {**args, "itemId": item_id})
        try:
            if data["merchantId"] != merchant_id or data["itemId"] != item_id:
                raise ValueError("Identidade divergente")
            groups = [OptionGroup(id=g["optionGroupId"], name=g["name"], min_selections=g["minSelections"],
                                  max_selections=g["maxSelections"],
                                  options=[Option(id=o["optionId"], name=o["name"], price_cents=cents(o["additionalPrice"]))
                                           for o in g["options"]]) for g in data["optionGroups"]]
            return MealCandidate(merchant_id=merchant_id, item_id=item_id, merchant_name=data["merchantName"],
                                 name=data["itemName"], description=data["itemDescription"], image_url=data.get("itemImageUrl"),
                                 price_cents=cents(data.get("promotionalUnitPrice") if data.get("promotionalUnitPrice") is not None else data["unitPrice"]),
                                 option_groups=groups)
        except (KeyError, TypeError, ValueError, ArithmeticError):
            raise MacroError("Detalhes do item diferem do contrato documentado.", 502) from None
