"""Classifica o item (produto de marca x prato) antes de escolher onde procurar os valores nutricionais."""
from jsonschema import validate

from app.core import logs
from app.core.config import Settings
from app.services.gemini import analyze_image
from app.skills import nutricao_classificar
from app.skills.comum import pedir_json
from ..entrada import extrair_json
from .llm import perguntar_json


async def classificar_item(settings: Settings, descricao: str, imagem: tuple[bytes, str] | None = None) -> dict:
    """{"tipo_item": "industrializado"|"prato", "marca": str, "motivo": str}. Levanta os erros de LLM de sempre.

    Com foto e chave do Gemini, o VLM lê a embalagem (a marca pode estar só na foto: nome "Bolo Recheado").
    Se o Gemini falhar, cai para o classificador só de texto.
    """
    dados = None
    if imagem is not None and settings.gemini_api_key:
        try:
            prompt = (f"{nutricao_classificar.INSTRUCOES}\n\n"
                      f"{pedir_json(nutricao_classificar.pedido(descricao), nutricao_classificar.SCHEMA)}")
            texto = await analyze_image(imagem[0], prompt, mime_type=imagem[1], json_mode=True, settings=settings)
            dados = extrair_json(texto)
            validate(dados, nutricao_classificar.SCHEMA)
            logs.info("classificar", "com a foto (o modelo lê a embalagem)")
        except Exception as exc:  # noqa: BLE001 - a foto é um extra; o texto basta para classificar
            logs.aviso("classificar", f"foto não ajudou ({logs.curto(str(exc), 100)}); classificando só pelo texto")
            dados = None
    if dados is None:
        dados = await perguntar_json(settings, nutricao_classificar.INSTRUCOES,
                                     nutricao_classificar.pedido(descricao), nutricao_classificar.SCHEMA)
    marca = f" · marca: {dados['marca']}" if dados["marca"].strip() else ""
    logs.info("classificar", f"{dados['tipo_item']}{marca} · {logs.curto(dados['motivo'], 140)}")
    return dados
