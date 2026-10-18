"""Provedor real do iFood (modo live), sobre o login OAuth de app.services.ifood_mcp.

Somente leitura, mais o cadastro de endereço. Carrinho, pagamento e pedido seguem bloqueados.
Os argumentos são validados contra o tools/list do servidor antes de cada chamada.
"""
import asyncio
from contextlib import asynccontextmanager
from decimal import Decimal
import json
from pathlib import Path
import time

import httpx
from jsonschema import Draft202012Validator
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client
from mcp.shared.auth import OAuthClientMetadata, OAuthToken
from mcp.types import PaginatedRequestParams

from app.core import logs
from app.core.config import Settings
from app.core.exceptions import MacroError
from app.schemas.macro import (Address, AddressCandidate, CreateAddressInput, GeocodeResult, MealCandidate,
                               MerchantSummary, Option, OptionGroup)
from app.services.ifood_mcp import FileTokenStorage

READ_TOOLS = {"listAddresses", "searchOffers", "browseOffers", "getItem", "getMerchant", "listItemTaxonomy"}
MAX_CONSULTAS = 4  # consultas por busca (cada uma é uma chamada ao iFood)
RESTAURANTES_RESERVA = 3  # restaurantes lidos quando nenhum item aparece
MENU_PAGES = 3  # até 75 itens por restaurante
# Única escrita liberada: salvar endereço (não cobra nem cria pedido). Carrinho e checkout seguem bloqueados.
ADDRESS_TOOL = "createAddress"
CAMPOS_ENDERECO = {"complement": "complemento", "reference": "ponto de referência", "neighborhood": "bairro"}
TOKEN_MARGIN_SECONDS = 120  # renova um pouco antes de vencer
_refresh_lock = asyncio.Lock()
_token_endpoint: str | None = None


class LoginRequired(Exception):
    """O iFood pediu login de novo; no servidor isso não pode abrir navegador."""


async def _no_browser(*_):
    raise LoginRequired


def _has(exc: BaseException, kind: type) -> bool:
    if isinstance(exc, kind):
        return True
    return isinstance(exc, BaseExceptionGroup) and any(_has(e, kind) for e in exc.exceptions)


async def _discover_token_endpoint(settings: Settings, http: httpx.AsyncClient) -> str:
    """Endpoint de token anunciado pelo próprio iFood (metadados públicos do recurso e do servidor de login)."""
    global _token_endpoint
    if _token_endpoint:
        return _token_endpoint
    base, _, path = settings.ifood_mcp_url.partition("://")[2].partition("/")
    prm = (await http.get(f"https://{base}/.well-known/oauth-protected-resource/{path}")).json()
    auth_server = prm["authorization_servers"][0].rstrip("/")
    meta = (await http.get(f"{auth_server}/.well-known/openid-configuration")).json()
    _token_endpoint = meta["token_endpoint"]
    return _token_endpoint


async def refresh_if_expired(settings: Settings) -> None:
    """Renova o access token pelo refresh token quando o salvo já venceu.

    A biblioteca MCP não sabe quando um token carregado do arquivo vence: ao receber 401 ela
    parte direto para login no navegador, sem tentar o refresh. Por isso a renovação é feita aqui.
    """
    path = Path(settings.ifood_token_file)
    async with _refresh_lock:
        tokens = OAuthToken.model_validate_json(path.read_text())
        if not tokens.expires_in or time.time() < path.stat().st_mtime + tokens.expires_in - TOKEN_MARGIN_SECONDS:
            return
        if not tokens.refresh_token:
            raise LoginRequired
        async with httpx.AsyncClient(timeout=settings.mcp_timeout_seconds) as http:
            data = {"grant_type": "refresh_token", "refresh_token": tokens.refresh_token,
                    "client_id": settings.ifood_client_id}
            if settings.ifood_client_secret:
                data["client_secret"] = settings.ifood_client_secret
            response = await http.post(await _discover_token_endpoint(settings, http), data=data)
        if response.status_code != 200:
            raise LoginRequired
        novo = OAuthToken.model_validate(response.json())
        if not novo.refresh_token:  # alguns servidores não rotacionam o refresh token
            novo = novo.model_copy(update={"refresh_token": tokens.refresh_token})
        await FileTokenStorage(settings).set_tokens(novo)


@asynccontextmanager
async def live_session(settings: Settings):
    """Sessão MCP autenticada com os tokens salvos, sem fluxo interativo de login."""
    auth = OAuthClientProvider(
        server_url=settings.ifood_mcp_url,
        client_metadata=OAuthClientMetadata(
            client_name="hackaton-ifood", redirect_uris=[settings.ifood_redirect_uri],
            grant_types=["authorization_code", "refresh_token"], response_types=["code"],
            scope=settings.ifood_scopes,
            token_endpoint_auth_method="client_secret_post" if settings.ifood_client_secret else "none"),
        storage=FileTokenStorage(settings),
        redirect_handler=_no_browser,
        callback_handler=_no_browser,
    )
    http_client = create_mcp_http_client(auth=auth)
    async with http_client, streamable_http_client(settings.ifood_mcp_url, http_client=http_client) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            yield session


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
        login = MacroError("Login do iFood expirado ou ausente. Rode `python -m app.services.ifood_mcp` "
                           "no backend para entrar de novo.", 503)
        if not Path(self.settings.ifood_token_file).exists():
            raise login
        try:
            async with asyncio.timeout(self.settings.mcp_timeout_seconds):
                await refresh_if_expired(self.settings)
                async with live_session(self.settings) as session:
                    yield session
        except MacroError:
            raise
        except Exception as e:
            if _has(e, LoginRequired):
                raise login from None
            # Não expõe cabeçalhos, dados pessoais nem grupos de exceção brutos.
            raise MacroError("Não foi possível consultar o MCP. Verifique o login do iFood e a conexão; "
                             "nenhuma compra foi enviada.", 503) from None

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

    def _q(self, texto: str) -> str:
        """Consulta nos logs: derivada do pedido do usuário, então só aparece com BUSCA_LOG_CONTEUDO=true."""
        return f"“{texto}”" if self.settings.busca_log_conteudo else "(oculta)"

    async def search(self, query: str, address: Address, budget_cents: int | None):
        return await self.search_many([query], address, budget_cents)

    @staticmethod
    def _itens(data: dict) -> list[MealCandidate]:
        try:
            return [MealCandidate(merchant_id=i["merchant"]["merchantId"], merchant_name=i["merchant"]["merchantName"],
                                  item_id=i["itemId"], name=i["itemName"], description="Consulte os detalhes para ver a composição.",
                                  image_url=i.get("itemImageUrl"), available=i["merchant"].get("isOpen") is True,
                                  price_cents=cents(i.get("promotionalUnitPrice") if i.get("promotionalUnitPrice") is not None else i["unitPrice"]))
                    for i in data["results"]]
        except (KeyError, TypeError, ValueError, ArithmeticError):
            raise MacroError("Resultado de busca difere do contrato documentado.", 502) from None

    async def _buscar_itens(self, session, tools, query: str, address: Address, budget_cents: int | None,
                            somente_abertos: bool = True):
        refinements = {"onlyOpen": True} if somente_abertos else {}
        if budget_cents is not None:
            refinements["maxItemPrice"] = budget_cents / 100
        logs.info("ifood", f"searchOffers ITEM consulta {self._q(query)} · {'só abertos' if somente_abertos else 'inclui fechados'}"
                           f" · preço máx.={refinements.get('maxItemPrice', 'sem limite')}")
        data = await self._call_in(session, tools, "searchOffers", {
            "query": query, "resultKind": "ITEM", "merchantType": "RESTAURANT", "pageSize": 10,
            "userLocation": {"latitude": address.latitude, "longitude": address.longitude}, "refinements": refinements})
        itens = self._itens(data)
        logs.info("ifood", f"consulta {self._q(query)} → {len(itens)} itens")
        return itens

    async def _itens_de_restaurantes(self, session, tools, termo: str, address: Address) -> list[MealCandidate]:
        """Reserva: acha restaurantes abertos pelo termo (culinária) e lê um trecho do cardápio de cada um."""
        local = {"latitude": address.latitude, "longitude": address.longitude}
        logs.info("ifood", f"nenhum item achado; procurando RESTAURANTES para {self._q(termo)}")
        data = await self._call_in(session, tools, "searchOffers", {
            "query": termo, "resultKind": "MERCHANT", "merchantType": "RESTAURANT", "pageSize": 10,
            "userLocation": local, "refinements": {"onlyOpen": True}})
        try:
            abertos = [m for m in data["results"] if m.get("isOpen") is True][:RESTAURANTES_RESERVA]
        except (KeyError, TypeError):
            raise MacroError("Resultado de busca difere do contrato documentado.", 502) from None
        logs.info("ifood", f"{len(abertos)} restaurantes abertos: " + ", ".join(m["merchantName"] for m in abertos))

        async def cardapio(m: dict) -> list[MealCandidate]:
            dados = await self._call_in(session, tools, "browseOffers", {
                "merchantType": "RESTAURANT", "resultKind": "ITEM", "pageSize": 25, "userLocation": local,
                "refinements": {"merchantId": m["merchantId"]}})
            return [c for c in self._itens(dados) if c.merchant_id == m["merchantId"]]

        paginas = await asyncio.gather(*(cardapio(m) for m in abertos), return_exceptions=True)
        itens = [c for p in paginas if not isinstance(p, BaseException) for c in p]
        logs.info("ifood", f"{len(itens)} itens lidos dos cardápios desses restaurantes")
        return itens

    async def search_many(self, queries: list[str], address: Address, budget_cents: int | None,
                          cuisine: str | None = None) -> list[MealCandidate]:
        """Várias consultas numa só conexão (em paralelo), sem repetidos. Sem itens, tenta restaurantes."""
        queries = list(dict.fromkeys(q for q in queries if q.strip()))[:MAX_CONSULTAS] or ["refeição"]
        async with self.connection() as session:
            tools = await self.tools(session)
            respostas = await asyncio.gather(
                *(self._buscar_itens(session, tools, q, address, budget_cents) for q in queries),
                return_exceptions=True)
            erros = [r for r in respostas if isinstance(r, BaseException)]
            if len(erros) == len(respostas):
                raise erros[0]
            for e in erros:
                logs.aviso("ifood", f"uma consulta falhou: {logs.curto(e)}")
            vistos, itens = set(), []
            for lista in respostas:
                for c in [] if isinstance(lista, BaseException) else lista:
                    if (c.merchant_id, c.item_id) not in vistos:
                        vistos.add((c.merchant_id, c.item_id))
                        itens.append(c)
            logs.info("ifood", f"{len(itens)} itens distintos em {len(queries)} consultas")
            if not itens:
                itens = await self._itens_de_restaurantes(session, tools, cuisine or queries[0], address)
            if not itens:
                itens = await self._itens_fechados(session, tools, queries, address, budget_cents)
            return itens

    async def _itens_fechados(self, session, tools, queries: list[str], address: Address,
                              budget_cents: int | None) -> list[MealCandidate]:
        """Nada aberto: confere se o item existe com o restaurante fechado, para avisar o usuário com precisão.

        Os itens voltam com available=False; o ranking os descarta e a mensagem diz "todos fechados".
        """
        logs.info("ifood", "nada aberto; conferindo se existem itens em restaurantes fechados")
        respostas = await asyncio.gather(
            *(self._buscar_itens(session, tools, q, address, budget_cents, somente_abertos=False)
              for q in queries[:2]), return_exceptions=True)
        vistos, itens = set(), []
        for lista in respostas:
            for c in [] if isinstance(lista, BaseException) else lista:
                if (c.merchant_id, c.item_id) not in vistos:
                    vistos.add((c.merchant_id, c.item_id))
                    itens.append(c)
        if itens:
            logs.info("ifood", f"{len(itens)} itens existem, mas os restaurantes estão fechados")
        return itens

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
