#!/usr/bin/env python3
"""Preenche Equipamento.tipo_acao / Magia.tipo_acao / Habilidade.tipo_acao a partir dos dados já
existentes no catálogo (ver `admin/banco.py::TIPOS_ACAO`). One-off: roda uma vez depois da migração
`37903f5c1000_adiciona_tipo_acao_e_favorito_de_.py`, idempotente (só preenche onde `tipo_acao` é
nulo, então rodar de novo não sobrescreve ajustes manuais feitos depois pelo Painel).

Uso:
    python scripts/preencher_tipo_acao.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "admin"))

import banco  # noqa: E402

RE_BONUS = re.compile(r"b[oô]nus", re.IGNORECASE)
RE_REACAO = re.compile(r"rea[cç][aã]o", re.IGNORECASE)
RE_ACAO = re.compile(r"\ba[cç][aã]o\b", re.IGNORECASE)


def tipo_acao_de_magia(tempo: str | None) -> str:
    if not tempo:
        return "nenhuma"
    if RE_BONUS.search(tempo):
        return "acao_bonus"
    if RE_REACAO.search(tempo):
        return "reacao"
    if RE_ACAO.search(tempo):
        return "acao"
    return "nenhuma"


def tipo_acao_de_habilidade(tipo: str) -> str:
    return {"acao": "acao", "reacao": "reacao", "traco": "nenhuma"}.get(tipo, "nenhuma")


def tipo_acao_de_equipamento(dano_formula: str | None) -> str:
    return "acao" if dano_formula else "nenhuma"


def main() -> None:
    engine = banco.criar_engine(RAIZ)
    Sessao = banco.fabrica_sessao(engine)
    s = Sessao()

    alteradas = {"magias": 0, "habilidades": 0, "equipamentos": 0}

    for magia in s.query(banco.Magia).filter(banco.Magia.tipo_acao.is_(None)).all():
        magia.tipo_acao = tipo_acao_de_magia(magia.tempo)
        alteradas["magias"] += 1

    for habilidade in s.query(banco.Habilidade).filter(banco.Habilidade.tipo_acao.is_(None)).all():
        habilidade.tipo_acao = tipo_acao_de_habilidade(habilidade.tipo)
        alteradas["habilidades"] += 1

    for equipamento in s.query(banco.Equipamento).filter(banco.Equipamento.tipo_acao.is_(None)).all():
        equipamento.tipo_acao = tipo_acao_de_equipamento(equipamento.dano_formula)
        alteradas["equipamentos"] += 1

    s.commit()
    print(
        f"tipo_acao preenchido: {alteradas['magias']} magia(s), "
        f"{alteradas['habilidades']} habilidade(s), {alteradas['equipamentos']} equipamento(s)."
    )


if __name__ == "__main__":
    main()
