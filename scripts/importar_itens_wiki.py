#!/usr/bin/env python3
"""Popula o catálogo `banco.Equipamento` a partir do bloco `item:` já estruturado de cada
`docs/itens/*.md` (fonte de verdade da wiki) — mesmo princípio de importar_magias_wiki.py. One-off,
idempotente: casa por `nome` antes de criar, só completa campos vazios numa linha que já existe.

Uso:
    python scripts/importar_itens_wiki.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "admin"))
sys.path.insert(0, str(RAIZ / "scripts"))

import banco  # noqa: E402
import wiki_data as wd  # noqa: E402
import preencher_tipo_acao as pta  # noqa: E402

PASTA_ITENS = RAIZ / "docs" / "itens"

RE_DANO = re.compile(r"^(\d+d\d+(?:\s*[+-]\s*\d+)?)\s*(.*)$")
RE_CA_BONUS = re.compile(r"^[+-]?\d+$")
RE_PESO = re.compile(r"([\d,.]+)")


def _peso_kg(peso: object) -> float | None:
    if not isinstance(peso, str):
        return None
    m = RE_PESO.search(peso)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def _dano(dano: object) -> tuple[str | None, str | None]:
    if not isinstance(dano, str) or not dano.strip():
        return None, None
    m = RE_DANO.match(dano.strip())
    if m:
        return m.group(1).strip(), (m.group(2).strip() or None)
    return dano.strip(), None


def _ca(ca: object) -> tuple[int | None, str | None]:
    if not isinstance(ca, str) or not ca.strip():
        return None, None
    valor = ca.strip()
    if RE_CA_BONUS.match(valor):
        return int(valor), None
    return None, valor


def _campos_de(bloco: dict, corpo: str, slug: str) -> dict:
    dano_formula, dano_tipo = _dano(bloco.get("dano"))
    ca_bonus, ca_formula = _ca(bloco.get("ca"))
    return {
        "categoria": bloco.get("categoria"),
        "custo": bloco.get("custo"),
        "peso_kg": _peso_kg(bloco.get("peso")),
        "dano_formula": dano_formula,
        "dano_tipo": dano_tipo,
        "propriedades": bloco.get("propriedades"),
        "ca_bonus": ca_bonus,
        "ca_formula": ca_formula,
        "raridade": bloco.get("raridade"),
        "fonte": bloco.get("fonte"),
        "descricao": corpo.strip() or None,
        "slug_origem": slug,
        "tipo_acao": pta.tipo_acao_de_equipamento(dano_formula),
    }


def main() -> None:
    engine = banco.criar_engine(RAIZ)
    Sessao = banco.fabrica_sessao(engine)
    s = Sessao()

    fontes_por_chave = {}
    for f in banco.listar_fontes(s):
        fontes_por_chave[f.abreviacao] = f
        fontes_por_chave[f.nome] = f
    existentes = {e.nome.casefold(): e for e in s.query(banco.Equipamento).all()}

    criadas = atualizadas = ja_completas = puladas = 0
    fontes_vistas: set[str] = set()
    for pagina in sorted(PASTA_ITENS.glob("*.md")):
        if pagina.stem == "index":
            continue
        meta, corpo = wd._front_matter(wd._ler(pagina))
        bloco = meta.get("item")
        if not isinstance(bloco, dict):
            puladas += 1
            continue
        nome = wd._titulo_do_arquivo(pagina)
        campos = _campos_de(bloco, corpo, pagina.stem)
        fonte_id = None
        if campos["fonte"]:
            fonte = fontes_por_chave.get(campos["fonte"])
            if fonte:
                fontes_vistas.add(fonte.abreviacao)
                fonte_id = fonte.id

        existente = existentes.get(nome.casefold())
        if existente is None:
            item = banco.Equipamento(nome=nome, fonte_id=fonte_id, **campos)
            s.add(item)
            existentes[nome.casefold()] = item
            criadas += 1
            continue

        mudou = False
        for chave, valor in campos.items():
            if valor is not None and not getattr(existente, chave):
                setattr(existente, chave, valor)
                mudou = True
        if existente.fonte_id is None and fonte_id is not None:
            existente.fonte_id = fonte_id
            mudou = True
        if mudou:
            atualizadas += 1
        else:
            ja_completas += 1

    s.commit()
    for abreviacao in sorted(fontes_vistas):
        banco.marcar_fonte_importada(s, abreviacao, "docs/itens/*.md")
    print(
        f"itens: {criadas} criado(s), {atualizadas} atualizado(s), "
        f"{ja_completas} já completo(s), {puladas} página(s) sem bloco item:."
    )


if __name__ == "__main__":
    main()
