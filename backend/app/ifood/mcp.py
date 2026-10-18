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
from mcp.types import PaginatedRequestParams

from ..config import Settings
from ..errors import MacroError
from ..schemas import (Address, AddressCandidate, CreateAddressInput, GeocodeResult, MealCandidate, MerchantSummary,
                       Option, OptionGroup)

READ_TOOLS = {"listAddresses", "searchOffers", "browseOffers", "getItem", "getMerchant", "listItemTaxonomy"}
MENU_PAGES = 3  # até 75 itens por restaurante
# Única escrita liberada: salvar endereço (não cobra nem cria pedido). Carrinho e checkout seguem bloqueados.
ADDRESS_TOOL = "createAddress"
CAMPOS_ENDERECO = {"complement": "complemento", "reference": "ponto de referência", "neighborhood": "bairro"}


def cents(value) -> int:
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0 or amount * 100 != (amount * 100).to_integral_value():
        raise ValueError("Preço inválido")
    return int(amount * 100)


def _attr(obj, v1: str, v2: str):
    """Lê um campo pelo nome da mcp 1.x (camelCase) ou da 2.x (snake_case)."""
    return getattr(obj, v1) if hasattr(obj, v1) else getattr(obj, v2, None)


def unpack_result(result) -> dict:
    if _attr(result, "isError", "is_error"):
        raise MacroError("O iFood recusou a consulta. Verifique a conta e tente novamente.", 502)
    data = _attr(result, "structuredContent", "structured_content")
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
                    # mcp 1.x devolve (read, write, get_session_id); mcp 2.x devolve só (read, write).
                    async with streamable_http_client(self.settings.ifood_endpoint, http_client=client) as streams:
                        async with ClientSession(streams[0], streams[1]) as session:
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
            try:
                page = await session.list_tools(cursor=cursor)
            except TypeError:  # mcp 2.x: paginação via params
                page = await session.list_tools(params=PaginatedRequestParams(cursor=cursor) if cursor else None)
            tools.update({tool.name: tool for tool in page.tools})
            cursor = _attr(page, "nextCursor", "next_cursor")
            if not cursor:
                return tools
            if cursor in seen:
                break
            seen.add(cursor)
        raise MacroError("Paginação de ferramentas MCP inválida.", 502)

    async def call_read(self, name: str, arguments: dict):
        async with self.connection() as session:
            return await self._call_in(session, await self.tools(session), name, arguments)

    async def _call_in(self, session, tools: dict, name: str, arguments: dict):
        """Chamada de leitura numa conexão já aberta (várias chamadas, uma conexão)."""
        if name not in READ_TOOLS:
            raise MacroError("Operações de escrita no iFood estão bloqueadas.", 403)
        if name not in tools:
            raise MacroError(f"A ferramenta {name} não está disponível nesta conta.", 503)
        if list(Draft202012Validator(_attr(tools[name], "inputSchema", "input_schema")).iter_errors(arguments)):
            raise MacroError("O schema real diverge do adaptador. Valide o contrato antes de continuar.", 502)
        return unpack_result(await session.call_tool(name, arguments=arguments))

    async def diagnostic(self):
        async with self.connection() as session:
            tools = await self.tools(session)
            return {"connected": True, "simulated": False,
                    "tools": [{"name": t.name, "input_schema": _attr(t, "inputSchema", "input_schema")} for t in tools.values()],
                    "message": "Ferramentas listadas. Checkout real permanece bloqueado."}

    async def _create_address(self, arguments: dict) -> dict:
        async with self.connection() as session:
            tools = await self.tools(session)
            if ADDRESS_TOOL not in tools:
                raise MacroError("Cadastro de endereço indisponível nesta conta.", 503)
            if list(Draft202012Validator(_attr(tools[ADDRESS_TOOL], "inputSchema", "input_schema")).iter_errors(arguments)):
                raise MacroError("O schema real diverge do adaptador. Valide o contrato antes de continuar.", 502)
            result = await session.call_tool(ADDRESS_TOOL, arguments=arguments)
        data = _attr(result, "structuredContent", "structured_content")
        if data is None:
            parts = [c.text for c in result.content if c.type == "text"]
            data = json.loads(parts[0]) if len(parts) == 1 else None
        if not isinstance(data, dict):
            raise MacroError("Resposta do cadastro de endereço não reconhecida.", 502)
        if data.get("success") is False or _attr(result, "isError", "is_error"):
            raise self._address_error(data.get("errors") or {})
        return data.get("data") or {}

    @staticmethod
    def _address_error(errors: dict) -> MacroError:
        code, message = errors.get("code", ""), str(errors.get("message", "")).lower()
        if code in {"CANDIDATE_NOT_FOUND", "GEOCODE_FAILED"}:
            return MacroError("Não encontrei esse endereço. Confira rua, número e cidade e tente de novo.", 422)
        if code == "MISSING_REQUIRED_ADDRESS_FIELDS" or "neighborhood" in message:
            faltando = [nome for campo, nome in CAMPOS_ENDERECO.items() if campo in message]
            detalhe = ", ".join(faltando) if faltando else "complemento e ponto de referência"
            return MacroError(f"O iFood exige mais dados para esta região: informe {detalhe}.", 422)
        # Texto externo é dado, não instrução: mostra só o código.
        return MacroError(f"O iFood não aceitou o endereço ({code or 'erro desconhecido'}). Revise os dados.", 422)

    async def geocode(self, address: str) -> GeocodeResult:
        data = await self._create_address({"address": address})
        try:
            candidates = [AddressCandidate(candidate_id=c["candidateId"], formatted=c["formattedAddress"],
                                           neighborhood=(c.get("location") or {}).get("neighborhood") or None,
                                           **(c.get("coordinates") or {}))
                          for c in data["candidates"]]
            return GeocodeResult(match="MULTIPLE" if data.get("matchConfidence") == "MULTIPLE" else "SINGLE",
                                 candidates=candidates)
        except (KeyError, TypeError, ValueError):
            raise MacroError("Resposta de geocodificação difere do contrato documentado.", 502) from None

    async def create_address(self, payload: CreateAddressInput) -> str | None:
        """Salva o endereço confirmado e devolve o addressId (quando o iFood informa)."""
        args = {"address": payload.address, "candidateId": payload.candidate_id}
        for campo in ("neighborhood", "complement", "reference", "alias"):
            if getattr(payload, campo):
                args[campo] = getattr(payload, campo)
        data = await self._create_address(args)
        return data.get("addressId") or (data.get("address") or {}).get("addressId")

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

    async def merchants(self, address: Address) -> list[MerchantSummary]:
        """Restaurantes abertos perto do endereço, do mais próximo ao mais distante."""
        data = await self.call_read("browseOffers", {
            "merchantType": "RESTAURANT", "resultKind": "MERCHANT", "pageSize": 25,
            "userLocation": {"latitude": address.latitude, "longitude": address.longitude},
            "refinements": {"onlyOpen": True, "sort": "DISTANCE"}})
        try:
            return [self._merchant(m) for m in data["results"]]
        except (KeyError, TypeError, ValueError, ArithmeticError):
            raise MacroError("Lista de restaurantes difere do contrato documentado.", 502) from None

    @staticmethod
    def _merchant(m: dict) -> MerchantSummary:
        entrega = m.get("deliveryMethod") or {}
        minutos = entrega.get("estimatedMinutes") or {}
        taxa = entrega.get("promotionalFee") if entrega.get("promotionalFee") is not None else entrega.get("fee")
        return MerchantSummary(
            merchant_id=m["merchantId"], name=m["merchantName"], logo_url=m.get("merchantLogoUrl"),
            is_open=m.get("isOpen") is True, distance_km=m.get("straightLineDistanceKm"),
            rating=m.get("reviewRating"), rating_count=m.get("ratingCount"),
            eta_min=minutos.get("min"), eta_max=minutos.get("max"),
            delivery_fee_cents=cents(taxa) if taxa is not None else None,
            minimum_order_cents=cents(m["minimumOrderAmount"]) if m.get("minimumOrderAmount") is not None else None)

    async def menu(self, merchant_id: str, address: Address) -> list[MealCandidate]:
        """Cardápio de um restaurante (sem descrição: ela vem do getItem quando o prato é aberto)."""
        args = {"merchantType": "RESTAURANT", "resultKind": "ITEM", "pageSize": 25,
                "userLocation": {"latitude": address.latitude, "longitude": address.longitude},
                "refinements": {"merchantId": merchant_id}}
        itens, vistos, token = [], set(), None
        async with self.connection() as session:
            tools = await self.tools(session)
            paginas = []
            for _ in range(MENU_PAGES):
                data = await self._call_in(session, tools, "browseOffers",
                                           {**args, **({"nextPageToken": token} if token else {})})
                paginas.append(data)
                token = data.get("nextPageToken") if data.get("hasMore") else None
                if not token:
                    break
        for data in paginas:
            try:
                for i in data["results"]:
                    if i["itemId"] in vistos or i["merchant"]["merchantId"] != merchant_id:
                        continue
                    vistos.add(i["itemId"])
                    preco = i.get("promotionalUnitPrice") if i.get("promotionalUnitPrice") is not None else i["unitPrice"]
                    itens.append(MealCandidate(
                        merchant_id=merchant_id, merchant_name=i["merchant"]["merchantName"], item_id=i["itemId"],
                        name=i["itemName"], description="", image_url=i.get("itemImageUrl"),
                        available=i["merchant"].get("isOpen") is True, price_cents=cents(preco)))
            except (KeyError, TypeError, ValueError, ArithmeticError):
                raise MacroError("Cardápio difere do contrato documentado.", 502) from None
        return itens

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
