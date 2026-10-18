from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "mock"
    assert data["simulated"] is True


def test_api_session_lifecycle():
    # 1. Obter sessão inicial
    response = client.get("/api/session")
    assert response.status_code == 200
    session_data = response.json()
    assert "id" in session_data
    session_id = session_data["id"]

    # Cookie da sessão deve ser setado
    assert "macro_session" in response.cookies
    cookie = {"macro_session": session_id}

    # 2. Listar endereços
    addr_resp = client.get("/api/addresses", cookies=cookie)
    assert addr_resp.status_code == 200
    addresses = addr_resp.json()
    assert len(addresses) > 0
    address_id = addresses[0]["id"]

    # 3. Definir endereço na sessão
    set_addr_resp = client.put(
        "/api/session/address",
        json={"address_id": address_id},
        cookies=cookie,
    )
    assert set_addr_resp.status_code == 200
    assert set_addr_resp.json()["address"]["id"] == address_id

    # 4. Buscar refeições
    search_resp = client.post(
        "/api/search",
        json={"text": "Quero um frango grelhado até 35 reais"},
        cookies=cookie,
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert len(search_data["recommendations"]) > 0
