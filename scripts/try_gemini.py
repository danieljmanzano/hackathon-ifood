"""Teste manual do Gemini: descreve uma imagem.

Uso: .venv/bin/python -m scripts.try_gemini caminho/da/foto.jpg ["pergunta"]
"""
import asyncio
import mimetypes
import sys
from pathlib import Path

from app.services.gemini import analyze_image


async def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Uso: python -m scripts.try_gemini foto.jpg [pergunta]")
    path = Path(sys.argv[1])
    prompt = " ".join(sys.argv[2:]) or "Descreva o prato e estime as calorias."
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    print(await analyze_image(path.read_bytes(), prompt, mime_type=mime))


if __name__ == "__main__":
    asyncio.run(main())
