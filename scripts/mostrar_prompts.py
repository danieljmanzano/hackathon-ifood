"""Mostra os textos que o sistema envia aos modelos, já montados com dados de exemplo.

Uso: .venv/bin/python -m scripts.mostrar_prompts              # todas as skills
     .venv/bin/python -m scripts.mostrar_prompts web          # só as que têm "web" no nome
     .venv/bin/python -m scripts.mostrar_prompts --lista      # só a lista, com quem usa cada uma
Os arquivos ficam em app/skills/.
"""

import sys

from app.skills import SKILLS


def resumo(modulo) -> str:
    return (modulo.__doc__ or "").strip().splitlines()[0]


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    so_lista = "--lista" in sys.argv
    escolhidas = {n: m for n, m in SKILLS.items() if not args or any(a in n for a in args)}
    if not escolhidas:
        sys.exit(f"Nenhuma skill com {args}. Disponíveis: {', '.join(SKILLS)}")
    for nome, modulo in escolhidas.items():
        print(f"\n{'=' * 78}\n{nome}  (app/skills/{nome}.py)\n{resumo(modulo)}")
        if so_lista:
            continue
        for rotulo, texto in modulo.exemplo():
            print(f"\n--- {rotulo} ({len(texto)} caracteres) ---\n{texto}")


if __name__ == "__main__":
    main()
