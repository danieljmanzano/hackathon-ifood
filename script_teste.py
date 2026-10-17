import base64, json, requests
import openai

client = openai.ChatCompletion()

def estimar_calorias(item: dict) -> dict:
    # baixa a imagem
    resp = requests.get(item["image_url"], timeout=15)
    resp.raise_for_status()
    img_b64 = base64.standard_b64encode(resp.content).decode()
    media_type = resp.headers.get("Content-Type", "image/jpeg")

    prompt = f"""Estime as calorias deste produto de delivery.

Nome: {item['name']}
Restaurante: {item['restaurant']}
Descrição: {item['description']}
Variações selecionadas: {json.dumps(item.get('variations', []), ensure_ascii=False)}

Considere o tamanho aparente da porção na imagem e os ingredientes citados.
Responda APENAS com JSON, sem texto extra nem markdown, neste formato:
{{
  "calorias_estimadas": <int>,
  "faixa_min": <int>,
  "faixa_max": <int>,
  "confianca": "baixa" | "media" | "alta",
  "justificativa": "<1-2 frases>"
}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": media_type, "data": img_b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )

    texto = msg.content[0].text.strip()
    texto = texto.replace("```json", "").replace("```", "").strip()
    estimativa = json.loads(texto)
    return {**item, "estimativa_calorias": estimativa}


if __name__ == "__main__":
    with open("pedido.json", encoding="utf-8") as f:
        item = json.load(f)
    print(json.dumps(estimar_calorias(item), ensure_ascii=False, indent=2))