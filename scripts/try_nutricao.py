"""Teste manual da pipeline de calorias (usa Gemini e OpenRouter de verdade).

Uso: .venv/bin/python -m scripts.try_nutricao [item.json] [--opcao "Catupiry"]... [--forcar]
                                              [--economico] [--sem-web] [--sem-bases]

item.json: payload do getItem (padrão: tests/fixtures/getItem_pizza.json).
Sem --forcar passa pela base local: rode duas vezes e a 2ª deve voltar na hora, sem chamar nada.
--forcar: ignora a base e recalcula (nada é gravado). --economico: só estima se bases e web falharem.
"""
import argparse
import asyncio
import time

from app.core.config import get_settings
from app.services.nutrition import pipeline, service
from scripts._item import carregar_item


def imprimir(r) -> None:
    print(f"\n## {r.state.upper()}  ·  método: {r.method}  ·  confiança: {r.confidence}")
    if r.state != "ready":
        print(r.evidence)
        return
    print(f"- **{r.calories:.0f} kcal** (faixa {r.minimum:.0f}–{r.maximum:.0f}) por {r.portion_basis}")
    print(f"- proteína {r.protein_g} g · carboidrato {r.carbs_g} g · gordura {r.fat_g} g · peso {r.portion_grams} g")
    if r.source_name:
        print(f"- fonte: {r.source_name} {r.source_url or ''}")
    print(f"- evidência: {r.evidence}")
    if r.revisar:
        print(f"- ⚠ REVISAR: {r.motivo_revisao}")
    for a in r.assumptions:
        print(f"  · {a}")


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("item", nargs="?")
    p.add_argument("--opcao", action="append", default=None)
    p.add_argument("--forcar", action="store_true")
    p.add_argument("--economico", action="store_true")
    p.add_argument("--sem-web", action="store_true")
    p.add_argument("--sem-bases", action="store_true")
    args = p.parse_args()

    settings = get_settings().model_copy(update={
        "calorias_estimar_sempre": not args.economico,
        "calorias_busca_web": not args.sem_web,
        "calorias_buscar_bases": not args.sem_bases,
    })
    item = carregar_item(args.item)
    print(f"Item: {item.name} ({item.merchant_name}) · opções: {args.opcao or 'nenhuma'}")
    inicio = time.perf_counter()
    if args.forcar:
        resultado = await pipeline.calcular(settings, item, args.opcao)
    else:
        resultado = await service.estimate_nutrition(item, settings)
    imprimir(resultado)
    print(f"\n({time.perf_counter() - inicio:.1f} s)")


if __name__ == "__main__":
    asyncio.run(main())
