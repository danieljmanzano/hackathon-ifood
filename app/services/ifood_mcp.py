"""Client do MCP do iFood (OAuth 2.1 + PKCE, client pré-registrado)."""

import asyncio
import time
import webbrowser
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider

try:  # MCP 2.x inclui issuer no retorno; MCP 1.x espera (code, state).
    from mcp.client.auth import AuthorizationCodeResult
except ImportError:
    AuthorizationCodeResult = None
from mcp.client.auth import oauth2 as _sdk_oauth2
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from app.core.config import Settings, get_settings

_sdk_validate_issuer = _sdk_oauth2.validate_metadata_issuer


def _validate_issuer(metadata, expected_issuer: str) -> None:
    # iFood anuncia issuer "https://id.ifood.com.br/3p" enquanto o recurso aponta
    # para "https://id.ifood.com.br"; aceita só esse par, o resto segue estrito.
    if (
        expected_issuer.rstrip("/") == "https://id.ifood.com.br"
        and str(metadata.issuer) == f"{expected_issuer.rstrip('/')}/3p"
    ):
        return
    _sdk_validate_issuer(metadata, expected_issuer)


_sdk_oauth2.validate_metadata_issuer = _validate_issuer


def client_metadata(settings: Settings) -> OAuthClientMetadata:
    metadata = OAuthClientMetadata(
        client_name="hackaton-ifood",
        redirect_uris=[settings.ifood_redirect_uri],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope=settings.ifood_scopes,
        token_endpoint_auth_method="client_secret_post" if settings.ifood_client_secret else "none",
    )
    # A validação acima confirma a URL; preserve sua grafia cadastrada no OAuth.
    # AnyUrl normaliza http://localhost:4000 para ...:4000/, mas o servidor exige igualdade exata.
    return metadata.model_copy(update={"redirect_uris": [settings.ifood_redirect_uri]})


class FileTokenStorage:
    """Tokens em arquivo; client info vem das credenciais pré-registradas (sem DCR)."""

    def __init__(self, settings: Settings):
        self._path = Path(settings.ifood_token_file)
        self._client_info = OAuthClientInformationFull(
            client_id=settings.ifood_client_id,
            client_secret=settings.ifood_client_secret or None,
            redirect_uris=[settings.ifood_redirect_uri],
            token_endpoint_auth_method="client_secret_post"
            if settings.ifood_client_secret
            else "none",
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope=settings.ifood_scopes,
        )

    async def get_tokens(self) -> OAuthToken | None:
        if not self._path.exists():
            return None
        return OAuthToken.model_validate_json(self._path.read_text())

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self._path.write_text(tokens.model_dump_json())
        self._path.chmod(0o600)

    async def get_client_info(self) -> OAuthClientInformationFull:
        return self._client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        pass


def _wait_for_callback(redirect_uri: str, expected_state: str | None = None):
    parsed = urlparse(redirect_uri)
    result: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
            if (not query.get("code") and not query.get("error")) or (
                expected_state and query.get("state") != expected_state
            ):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Tentativa antiga ou invalida. Use a aba de login mais recente.")
                return
            result.update(query)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Autenticado. Pode fechar esta aba.")

        def log_message(self, *_):
            pass

    server = HTTPServer((parsed.hostname or "localhost", parsed.port or 80), Handler)
    server.timeout = 1
    deadline = time.monotonic() + 600
    try:
        while not result and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    if "code" not in result:
        raise RuntimeError(f"Callback OAuth sem code: {result}")
    if AuthorizationCodeResult is not None:
        return AuthorizationCodeResult(
            code=result["code"], state=result.get("state"), iss=result.get("iss")
        )
    return result["code"], result.get("state")


@asynccontextmanager
async def ifood_session(settings: Settings | None = None):
    settings = settings or get_settings()
    if not settings.ifood_client_id:
        raise RuntimeError("IFOOD_CLIENT_ID não configurado")

    expected_state = None

    async def redirect_handler(url: str) -> None:
        nonlocal expected_state
        expected_state = parse_qs(urlparse(url).query).get("state", [None])[0]
        print(f"Abra para autenticar:\n{url}")
        webbrowser.open(url)

    async def callback_handler():
        return await asyncio.to_thread(
            _wait_for_callback, settings.ifood_redirect_uri, expected_state
        )

    auth = OAuthClientProvider(
        server_url=settings.ifood_mcp_url,
        client_metadata=client_metadata(settings),
        storage=FileTokenStorage(settings),
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )
    http_client = create_mcp_http_client(auth=auth)
    async with (
        http_client,
        streamable_http_client(settings.ifood_mcp_url, http_client=http_client) as streams,
    ):
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def _main() -> None:
    async with ifood_session() as session:
        tools = await session.list_tools()
        for tool in tools.tools:
            print(
                f"- {tool.name}: {(tool.description or '').splitlines()[0] if tool.description else ''}"
            )


if __name__ == "__main__":
    asyncio.run(_main())
