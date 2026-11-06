#!/usr/bin/env python3
"""Importa `docs/lugares/*.md` para `banco.Lugar` — Master's Shield (2026-11-05), ver
alembic/versions/7b2e4c9a1f6d. One-off, idempotente (não duplica por `slug`, então rodar de novo
só adiciona páginas novas desde a última vez).

Uso:
    python scripts/importar_lugares.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "admin"))

import banco  # noqa: E402
import wiki_data as wd  # noqa: E402


def main() -> None:
    engine = banco.criar_engine(RAIZ)
    Sessao = banco.fabrica_sessao(engine)
    s = Sessao()

    existentes = {l.slug for l in s.query(banco.Lugar).all()}
    novos = 0
    for item in wd.listar_lugares_detalhado(RAIZ):
        if item["slug"] in existentes:
            continue
        s.add(banco.Lugar(
            nome=item["nome"], slug=item["slug"], pagina_rel_docs=item["rel_docs"], canonico=True,
        ))
        novos += 1

    s.commit()
    print(f"{novos} lugar(es) importado(s) de docs/lugares/.")


if __name__ == "__main__":
    main()
