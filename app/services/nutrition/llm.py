"""Provedores de modelo da pipeline nutricional: OpenAI (GPT) ou OpenRouter (modelos gratuitos).

Os dois recebem as mesmas instruções e o mesmo JSON Schema e devolvem o mesmo formato de dados,
então o resto da pipeline não sabe qual está em uso. Escolha em NUTRITION_PROVIDER no .env.
"""

import json
import logging
import re
from dataclasses import dataclass, field

import httpx
from jsonschema import Draft202012Validator
from openai import AsyncOpenAI, OpenAIError

from app.core.config import Settings

log = logging.getLogger(__name__)

# Vale tentar o próximo modelo: limite de uso, modelo sem endpoint (ex.: sem suporte a imagem), falha do provedor.
RETRYABLE_STATUS = {404, 408, 429, 500, 502, 503, 504}


class LLMError(Exception):
    """Nenhum modelo devolveu uma resposta utilizável."""


@dataclass
class Resposta:
    dados: dict
    urls: set[str] = field(default_factory=set)  # sites que a busca na web realmente consultou
    usou_imagem: bool = False


class OpenAIBackend:
    """GPT pela Responses API: JSON Schema estrito e busca na web nativa."""

    web_search = True

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.nutrition_timeout_seconds,
            max_retries=1,
        )

    async def json(
        self,
        *,
        nome: str,
        schema: dict,
        instrucoes: str,
        texto: str,
        imagem: str | None = None,
        buscar_na_web: bool = False,
    ) -> Resposta:
        conteudo = [{"type": "input_text", "text": texto}]
        if imagem:
            conteudo.append({"type": "input_image", "image_url": imagem})
        extra = (
            {"tools": [{"type": "web_search"}], "include": ["web_search_call.action.sources"]}
            if buscar_na_web
            else {}
        )
        try:
            resposta = await self.client.responses.create(
                model=self.settings.nutrition_model,
                instructions=instrucoes,
                input=[{"role": "user", "content": conteudo}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": nome,
                        "schema": schema,
                        "strict": True,
                    }
                },
                **extra,
            )
        except OpenAIError as e:
            raise LLMError(f"OpenAI: {e}") from e
        return Resposta(
            json.loads(resposta.output_text), _urls_openai(resposta), usou_imagem=bool(imagem)
        )


def _urls_openai(resposta) -> set[str]:
    urls = set()
    for saida in resposta.output:
        if saida.type == "web_search_call":
            for fonte in getattr(getattr(saida, "action", None), "sources", None) or []:
                url = fonte.get("url") if isinstance(fonte, dict) else getattr(fonte, "url", None)
                if url:
                    urls.add(url)
        elif saida.type == "message":
            for parte in saida.content:
                for anotacao in getattr(parte, "annotations", None) or []:
                    if getattr(anotacao, "type", None) == "url_citation":
                        urls.add(anotacao.url)
    return urls


class OpenRouterBackend:
    """OpenRouter (API de chat compatível com OpenAI), com troca automática entre modelos.

    Modelos gratuitos variam: alguns não aceitam imagem e outros ignoram o JSON Schema. Por isso o
    formato também vai no texto, a resposta é validada contra o schema, e o que falhar passa para o
    próximo modelo da lista. Se nenhum aceitar imagem, a estimativa é refeita só com o texto.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.modelos = list(
            dict.fromkeys(
                [
                    settings.nutrition_openrouter_model,
                    *settings.nutrition_openrouter_fallback_models,
                ]
            )
        )
        # O plugin de busca do OpenRouter é cobrado por uso, mesmo com modelo gratuito.
        self.web_search = settings.nutrition_openrouter_web_search

    async def json(
        self,
        *,
        nome: str,
        schema: dict,
        instrucoes: str,
        texto: str,
        imagem: str | None = None,
        buscar_na_web: bool = False,
    ) -> Resposta:
        erros: list[str] = []
        async with httpx.AsyncClient(
            base_url=self.settings.openrouter_base_url,
            timeout=self.settings.nutrition_timeout_seconds,
        ) as http:
            for com_imagem in [True, False] if imagem else [False]:
                for modelo in self.modelos:
                    resposta = await self._tentar(
                        http,
                        modelo,
                        nome,
                        schema,
                        instrucoes,
                        texto,
                        imagem if com_imagem else None,
                        buscar_na_web,
                        erros,
                    )
                    if resposta:
                        resposta.usou_imagem = com_imagem
                        return resposta
        raise LLMError("OpenRouter: todos os modelos falharam: " + " | ".join(erros[-6:]))

    async def _tentar(
        self, http, modelo, nome, schema, instrucoes, texto, imagem, buscar_na_web, erros
    ):
        conteudo = [
            {
                "type": "text",
                "text": f"{texto}\n\nResponda somente com um objeto JSON válido que siga "
                f"este JSON Schema, sem texto antes ou depois:\n{json.dumps(schema)}",
            }
        ]
        if imagem:
            conteudo.append({"type": "image_url", "image_url": {"url": imagem}})
        payload = {
            "model": modelo,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": instrucoes},
                {"role": "user", "content": conteudo},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": nome, "strict": True, "schema": schema},
            },
        }
        if buscar_na_web:
            payload["plugins"] = [{"id": "web", "max_results": 5}]
        for tentativa in ("com schema", "sem schema"):
            try:
                r = await http.post(
                    "/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                        "X-Title": "Macro",
                    },
                )
            except httpx.HTTPError as e:
                erros.append(f"{modelo}: rede ({e})")
                return None
            if r.status_code == 400 and tentativa == "com schema":
                payload.pop(
                    "response_format"
                )  # modelo sem suporte a JSON Schema: o formato segue no texto
                continue
            if r.status_code != 200:
                erros.append(f"{modelo}: {r.status_code} {r.text[:120]}")
                return None
            try:
                mensagem = r.json()["choices"][0]["message"]
                dados = _extrair_json(mensagem.get("content") or "")
            except (KeyError, IndexError, ValueError) as e:
                erros.append(f"{modelo}: resposta inválida ({e})")
                return None
            invalidos = [e.message for e in Draft202012Validator(schema).iter_errors(dados)]
            if invalidos:
                erros.append(f"{modelo}: fora do formato ({invalidos[0][:80]})")
                return None
            urls = {
                a["url_citation"]["url"]
                for a in mensagem.get("annotations") or []
                if a.get("type") == "url_citation" and a.get("url_citation", {}).get("url")
            }
            return Resposta(dados, urls)
        return None


def _extrair_json(texto: str) -> dict:
    """Primeiro objeto JSON do texto (modelos gratuitos às vezes cercam com ```json ou comentários)."""
    texto = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.M).strip()
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio < 0 or fim < inicio:
        raise ValueError("sem objeto JSON")
    dados = json.loads(texto[inicio : fim + 1])
    if not isinstance(dados, dict):
        raise ValueError("JSON não é um objeto")
    return dados


def criar_backend(settings: Settings) -> OpenAIBackend | OpenRouterBackend | None:
    """Provedor escolhido em NUTRITION_PROVIDER, ou None se a chave dele não estiver configurada."""
    if settings.nutrition_provider == "openrouter":
        return OpenRouterBackend(settings) if settings.openrouter_api_key else None
    return OpenAIBackend(settings) if settings.openai_api_key.get_secret_value() else None
