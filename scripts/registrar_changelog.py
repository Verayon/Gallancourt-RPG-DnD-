#!/usr/bin/env python3
"""Acrescenta uma versão ao changelog sem precisar abrir o Painel do Mestre no navegador.

Uso, a partir da raiz do projeto:

    python scripts/registrar_changelog.py <versao> <data AAAA-MM-DD> "<mudanca 1>" ["<mudanca 2>" ...]

Exemplo:

    python scripts/registrar_changelog.py 0.5 2026-11-03 "Combat Tracker completo" "Favoritos em habilidades/magias"

Chama a mesma função que o formulário do Painel usa (admin/wiki_data.py
adicionar_versao_changelog), escrevendo direto em dados/changelog.yml — sem HTTP, sem login,
sem precisar do servidor rodando. O selo de versão e a página /changelog/ pegam a mudança no
próximo `mkdocs build` (ou na próxima publicação feita pelo Painel).
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "admin"))
import wiki_data as wd  # noqa: E402


def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        raise SystemExit(1)
    versao, data, *mudancas = sys.argv[1:]
    novo_id = wd.adicionar_versao_changelog(RAIZ, versao, data, mudancas)
    print(f"Changelog: versão {versao} registrada (id {novo_id}, {len(mudancas)} mudança(s)).")


if __name__ == "__main__":
    main()
