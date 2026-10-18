"""Gera app/services/nutrition/dados/taco.csv a partir dos CSVs da TACO (food, categories, nutrients).

Fonte usada: repositório público raulfdm/taco-api (references/csv/). Valores por 100 g de alimento.
Uso: .venv/bin/python -m scripts.importar_taco PASTA_COM_CSVS
"""
import csv
import sys
from pathlib import Path

DESTINO = Path(__file__).resolve().parents[1] / "app/services/nutrition/dados/taco.csv"


def numero(valor: str) -> str:
    """'Tr' (traço), 'NA' e vazio viram vazio; o resto precisa ser número."""
    try:
        return str(float(valor.replace(",", ".")))
    except ValueError:
        return ""


def main(pasta: Path) -> None:
    categorias = {r["id"]: r["name"] for r in csv.DictReader((pasta / "categories.csv").open(encoding="utf-8"))}
    nutrientes = {r["foodId"]: r for r in csv.DictReader((pasta / "nutrients.csv").open(encoding="utf-8"))}
    linhas = []
    for alimento in csv.DictReader((pasta / "food.csv").open(encoding="utf-8")):
        n = nutrientes.get(alimento["id"])
        if not n:
            continue
        valores = [numero(n[c]) for c in ("kcal", "protein", "carbohydrates", "lipids")]
        if not valores[0]:
            continue
        linhas.append([alimento["name"], categorias.get(alimento["categoryId"], ""), *valores])
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with DESTINO.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["nome", "categoria", "kcal", "proteina_g", "carbo_g", "gordura_g"])
        escritor.writerows(linhas)
    print(f"{len(linhas)} alimentos gravados em {DESTINO}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
