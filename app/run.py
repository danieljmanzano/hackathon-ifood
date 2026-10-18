"""Sobe o backend escolhendo o provedor de LLM na linha de comando.

Uso: python -m app.run [--llm openrouter|openai] [--log off|resumo|detalhe] [--host 127.0.0.1] [--port 8000] [--reload] [--check]

--llm openrouter: LLM de texto pelo OpenRouter, sem busca na web e sem leitura das imagens.
--llm openai (padrão): texto, imagens e busca na web (web_search) pela OpenAI; exige OPENAI_API_KEY no .env.
A web só é consultada se as bases de dados não acharem.
--check: só valida a configuração e mostra o resumo, sem subir o servidor.
"""
import argparse
import os
import sys

from app.core.config import get_settings


def resumo(settings) -> str:
    texto = settings.nutrition_model if settings.nutrition_provider == "openai" else settings.openrouter_model
    openai = settings.nutrition_provider == "openai"
    web = "OpenAI web_search" if openai else "desligada (só com openai)"
    return (f"Provedor de texto: {settings.nutrition_provider} ({texto}) · chave: {'sim' if settings.llm_api_key else 'NÃO'}\n"
            f"Busca na web: {web} · só se as bases não acharem · chave: {'sim' if settings.web_api_key else 'NÃO'}\n"
            f"Logs do pipeline: {settings.calorias_log}\n"
            f"Imagens: {f'OpenAI ({settings.nutrition_model})' if openai else 'desligadas (só com openai)'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sobe o backend Macro.")
    parser.add_argument("--llm", choices=["openrouter", "openai"], help="provedor de LLM (padrão: NUTRITION_PROVIDER do .env, openai)")
    parser.add_argument("--log", choices=["off", "resumo", "detalhe"],
                        help="verbosidade dos logs do pipeline (padrão: CALORIAS_LOG do .env, resumo)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--check", action="store_true", help="só valida a configuração")
    args = parser.parse_args(argv)

    if args.llm:
        os.environ["NUTRITION_PROVIDER"] = args.llm  # herdado pelo processo do uvicorn --reload
    if args.log:
        os.environ["CALORIAS_LOG"] = args.log
    get_settings.cache_clear()
    settings = get_settings()
    print(resumo(settings))

    if settings.nutrition_provider == "openai" and not settings.openai_api_key.get_secret_value():
        print("\nErro: --llm openai exige OPENAI_API_KEY no .env.", file=sys.stderr)
        return 2
    if not settings.nutrition_enabled:
        print("\nAviso: sem chaves de LLM, a nutrição ficará 'unavailable'.", file=sys.stderr)
    if args.check:
        return 0

    import uvicorn
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
