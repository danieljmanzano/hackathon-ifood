from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.core.config import get_settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def offline_intent():
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(update={"intent_llm_enabled": False})
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


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


def test_mock_address_registration_and_selection():
    cookie = {"macro_session": client.get("/api/session").json()["id"]}
    other = {"macro_session": TestClient(app).get("/api/session").json()["id"]}

    found = client.post("/api/addresses/geocode", json={"address": "Avenida São Carlos, 400"}, cookies=cookie)
    assert found.status_code == 200
    candidate = found.json()["candidates"][0]

    created = client.post("/api/addresses", json={
        "address": "Avenida São Carlos, 400", "candidate_id": candidate["candidate_id"],
        "neighborhood": "Centro", "complement": "Apto 12", "alias": "TRABALHO",
    }, cookies=cookie)
    assert created.status_code == 200
    body = created.json()
    new_address = body["session"]["address"]
    assert new_address["label"] == "Trabalho"
    assert "Avenida São Carlos, 400" in new_address["formatted"]
    assert [a["id"] for a in body["addresses"]][-1] == new_address["id"]

    # O cadastro fica disponível para trocar de endereço depois, só para o mesmo usuário.
    listed = client.get("/api/addresses", cookies=cookie).json()
    assert len(listed) == 2 and new_address["id"] in {a["id"] for a in listed}
    assert new_address["id"] not in {a["id"] for a in client.get("/api/addresses", cookies=other).json()}
    assert client.put("/api/session/address", json={"address_id": listed[0]["id"]}, cookies=cookie).json()["address"]["id"] == listed[0]["id"]
    assert client.put("/api/session/address", json={"address_id": new_address["id"]}, cookies=other).status_code == 422
