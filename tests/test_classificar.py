import asyncio
import json

from app.core.config import Settings
from app.services.nutrition.etapas import classificar as mod

FOTO = (b"\xff\xd8fake", "image/jpeg")
RESPOSTA = {"tipo_item": "industrializado", "marca": "Dona Maria", "motivo": "marca na embalagem"}


def test_foto_le_marca_da_embalagem(monkeypatch):
    chamadas = {}

    async def fake_image(imagem, prompt, **kw):
        chamadas["prompt"] = prompt
        return json.dumps(RESPOSTA)

    async def sem_texto(*a, **k):
        raise AssertionError("não devia cair para o texto")

    monkeypatch.setattr(mod, "analyze_image", fake_image)
    monkeypatch.setattr(mod, "perguntar_json", sem_texto)
    r = asyncio.run(mod.classificar_item(Settings(gemini_api_key="x"), "Bolo Recheado", FOTO))
    assert r["marca"] == "Dona Maria" and "LEIA" in chamadas["prompt"]


def test_gemini_falha_cai_para_texto(monkeypatch):
    async def quebra(*a, **k):
        raise RuntimeError("429")

    async def texto(*a, **k):
        return {"tipo_item": "prato", "marca": "", "motivo": "sem pista"}

    monkeypatch.setattr(mod, "analyze_image", quebra)
    monkeypatch.setattr(mod, "perguntar_json", texto)
    r = asyncio.run(mod.classificar_item(Settings(gemini_api_key="x"), "Bolo Recheado", FOTO))
    assert r["tipo_item"] == "prato"
