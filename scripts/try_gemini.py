"""Teste manual: estima calorias de uma foto de prato usando Google Gemini (ou fallback OpenRouter).

Uso:
    .venv/bin/python -m scripts.try_gemini foto_prato.jpg ["Estime as calorias deste prato"]
"""
import base64
import json
import mimetypes
import os
from pathlib import Path
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

SYSTEM_INSTRUCTION = """Você é um nutricionista especialista em estimativa calórica e macronutrientes de refeições a partir de fotos.
Analise a imagem da refeição e as instruções do usuário.
Responda EXCLUSIVAMENTE em formato JSON com o seguinte schema:
{
  "calorias_estimadas": <inteiro em kcal>,
  "faixa_min": <inteiro em kcal>,
  "faixa_max": <inteiro em kcal>,
  "confianca": "<baixa | media | alta>",
  "justificativa": "<texto detalhado explicando os alimentos identificados, porções estimadas e método>",
  "alimentos_identificados": [
    {"nome": "<nome do alimento>", "porcao_estimada": "<ex: 150g>", "calorias": <inteiro>}
  ]
}
A faixa mínima e máxima deve refletir a incerteza real com base na clareza visual e porções.
"""


def load_image(source: str) -> tuple[str, str]:
    if source.startswith(("http://", "https://")):
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(source)
            resp.raise_for_status()
            content = resp.content
            mime_type = resp.headers.get("content-type", "").split(";")[0] or "image/jpeg"
            return base64.b64encode(content).decode("utf-8"), mime_type

    image_path = Path(source)
    if not image_path.exists():
        raise FileNotFoundError(f"Arquivo '{image_path}' não encontrado.")
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if not mime_type:
        mime_type = "image/jpeg"
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return encoded, mime_type


def call_gemini_api(api_key: str, image_b64: str, mime_type: str, prompt: str) -> dict:
    models = ["gemini-flash-latest", "gemini-3.8-flash", "gemini-3.5-flash"]
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_b64,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2,
        },
    }
    last_error = None
    with httpx.Client(timeout=60.0) as client:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(raw_text)
            except Exception as e:
                last_error = e
                continue
    raise last_error or RuntimeError("Todos os modelos Gemini falharam.")


def call_openrouter_api(api_key: str, image_b64: str, mime_type: str, prompt: str) -> dict:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                    },
                ],
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"]
        return json.loads(raw_text)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Uso: .venv/bin/python -m scripts.try_gemini <caminho_imagem> [prompt]")
        print("Exemplo: .venv/bin/python -m scripts.try_gemini foto_prato.jpg 'Estime as calorias deste prato'")
        sys.exit(1)

    source = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else "Estime as calorias desta refeição e descreva os alimentos visíveis."

    gemini_key = os.getenv("GEMINI_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if not gemini_key and not openrouter_key:
        print("❌ Nenhuma chave de API encontrada!")
        print("Configure GEMINI_API_KEY ou OPENROUTER_API_KEY no arquivo .env para executar a estimativa visual.")
        sys.exit(1)

    try:
        image_b64, mime_type = load_image(source)
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo de imagem '{source}' não encontrado.")
        print("💡 Dica: Verifique se o caminho do arquivo está correto ou se a imagem está na raiz do projeto.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao carregar imagem: {e}")
        sys.exit(1)

    print(f"📸 Imagem: {source}")
    print(f"💬 Pergunta: {prompt}\n")
    print("⏳ Analisando refeição com Gemini...")

    try:
        if gemini_key:
            resultado = call_gemini_api(gemini_key, image_b64, mime_type, prompt)
        else:
            resultado = call_openrouter_api(openrouter_key, image_b64, mime_type, prompt)

        print("\n" + "=" * 50)
        print("🥗 RESULTADO DA ESTIMATIVA CALÓRICA")
        print("=" * 50)
        print(f"🔥 Calorias Estimadas: {resultado.get('calorias_estimadas', 'N/A')} kcal")
        print(f"📊 Faixa de Incerteza: {resultado.get('faixa_min', 'N/A')} a {resultado.get('faixa_max', 'N/A')} kcal")
        print(f"🎯 Nível de Confiança: {str(resultado.get('confianca', 'N/A')).upper()}")
        print(f"📝 Justificativa: {resultado.get('justificativa', '')}\n")

        alimentos = resultado.get("alimentos_identificados", [])
        if alimentos:
            print("🍽️ Alimentos Identificados:")
            for item in alimentos:
                nome = item.get("nome", "Item")
                porcao = item.get("porcao_estimada", "")
                kcal = item.get("calorias", "")
                print(f"  • {nome} ({porcao}): ~{kcal} kcal")

        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Falha na chamada da API: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
