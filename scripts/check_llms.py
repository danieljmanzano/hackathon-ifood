"""Verifica se os LLMs configurados no .env respondem: OpenRouter (texto), Gemini (texto e imagem).

Uso: .venv/bin/python -m scripts.check_llms
Sai com código 1 se algum falhar. Cada checagem faz uma chamada mínima (gasta quase nada de cota).
"""
import asyncio
import sys
import time

from app.core.config import get_settings
from app.services.gemini import analyze_image, generate_text
from app.services.openrouter import chat_completion

# PNG 1x1 branco, só para exercitar o caminho com imagem.
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8"
                    "ffff3f0005fe02fea7d6a0560000000049454e44ae426082")


async def verificar(nome: str, chave: str, chamada) -> bool:
    if not chave:
        print(f"[PULADO] {nome}: chave não configurada")
        return True
    inicio = time.perf_counter()
    try:
        resposta = await chamada()
    except Exception as e:  # qualquer falha conta como "fora do ar"
        print(f"[FALHOU] {nome} ({time.perf_counter() - inicio:.1f} s): {e}")
        return False
    print(f"[OK]     {nome} ({time.perf_counter() - inicio:.1f} s): {resposta.strip()[:60]!r}")
    return True


async def main() -> int:
    s = get_settings()
    pedido = "Responda apenas: ok"
    resultados = [
        await verificar("OpenRouter texto", s.openrouter_api_key,
                        lambda: chat_completion([{"role": "user", "content": pedido}], max_tokens=10, settings=s)),
        await verificar("Gemini texto", s.gemini_api_key, lambda: generate_text(pedido, settings=s)),
        await verificar("Gemini imagem", s.gemini_api_key,
                        lambda: analyze_image(PNG, "Que cor é esta imagem? Uma palavra.", mime_type="image/png",
                                              settings=s)),
    ]
    return 0 if all(resultados) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
