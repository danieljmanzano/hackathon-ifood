"""Teste manual (offline, sem LLM) do índice de alimentos: mostra os candidatos da TACO para um título.

Uso: .venv/bin/python -m scripts.try_bases "arroz branco cozido"
"""
import sys

from app.core.config import get_settings
from app.services.nutrition.etapas.bases import candidatos, carregar_taco


def main() -> None:
    consulta = " ".join(sys.argv[1:]) or "arroz branco cozido"
    alimentos = carregar_taco(str(get_settings().calorias_dados_dir))
    print(f"{len(alimentos)} alimentos na TACO. Consulta: {consulta!r}\n")
    for a in candidatos(alimentos, consulta):
        m = a.macros
        print(f"- {a.nome} ({a.categoria}): {m.kcal:g} kcal · P {m.proteina_g} · C {m.carbo_g} · G {m.gordura_g} /100 g")


if __name__ == "__main__":
    main()
