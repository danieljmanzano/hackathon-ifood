import pytest

from app.core.config import Settings
from app.services.ifood_mcp import client_metadata


@pytest.mark.parametrize('uri', ['http://localhost:4000', 'http://localhost:4000/', 'http://localhost:4000/callback'])
def test_oauth_preserves_registered_redirect_exactly(uri):
    settings = Settings(_env_file=None, ifood_redirect_uri=uri)
    metadata = client_metadata(settings)
    assert str(metadata.redirect_uris[0]) == uri


def test_callback_ignores_stale_state_and_favicon():
    import socket
    import time
    from concurrent.futures import ThreadPoolExecutor
    import httpx
    from app.services.ifood_mcp import _wait_for_callback
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]
    uri = f'http://127.0.0.1:{port}'
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_wait_for_callback,uri,'current-session')
        with httpx.Client(trust_env=False,timeout=1) as client:
            for _ in range(100):
                try:
                    response = client.get(uri+'/favicon.ico')
                    break
                except httpx.ConnectError:
                    time.sleep(.01)
            assert response.status_code == 400 and not future.done()
            assert client.get(uri,params={'state':'old-session','code':'old-code'}).status_code == 400
            assert not future.done()
            assert client.get(uri,params={'state':'current-session','code':'new-code'}).status_code == 200
        result = future.result(timeout=2)
        assert (result[0] if isinstance(result,tuple) else result.code) == 'new-code'
