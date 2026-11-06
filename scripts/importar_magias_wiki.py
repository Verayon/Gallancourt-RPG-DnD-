#!/usr/bin/env python3
"""Popula o catálogo `banco.Magia` a partir do bloco `magia:` já estruturado de cada
`docs/magias/*.md` (417 páginas, fonte de verdade da wiki) — não lê o livro em PDF/Markdown
convertido, que é texto solto e menos confiável pra isso. One-off, idempotente: casa por `nome`
(sem diferenciar maiúsculas) antes de criar, e só completa campos vazios numa magia que já existe
(nunca duplica, nunca sobrescreve um ajuste manual feito pelo Painel).

Uso:
    python scripts/importar_magias_wiki.py
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

PASTA_MAGIAS = RAIZ / "docs" / "magias"


def _dano_formula_base(dano: object) -> str | None:
    """`dano:` é uma lista de [rótulo_de_nível, fórmula] (ex.: Bola de Fogo escala por nível) —
    usa a primeira linha (nível mínimo/base) como `Magia.dano_formula`."""
    if isinstance(dano, list) and dano and isinstance(dano[0], list) and len(dano[0]) == 2:
        return str(dano[0][1])
    if isinstance(dano, str):
        return dano
    return None


def _campos_de(bloco: dict, corpo: str, slug: str) -> dict:
    classes = bloco.get("classes")
    return {
        "nivel": bloco.get("nivel"),
        "escola": bloco.get("escola"),
        "tempo": bloco.get("tempo"),
        "alcance": bloco.get("alcance"),
        "componentes": bloco.get("componentes"),
        "duracao": bloco.get("duracao"),
        "classes": ", ".join(classes) if isinstance(classes, list) else classes,
        "dano_formula": _dano_formula_base(bloco.get("dano")),
        "dano_tipo": bloco.get("dano_tipo") if bloco.get("dano_tipo") not in (None, "Nenhum") else None,
        "resistencia": bloco.get("resistencia"),
        "fonte": bloco.get("fonte"),
        "descricao": corpo.strip() or None,
        "slug_origem": slug,
        "tipo_acao": pta.tipo_acao_de_magia(bloco.get("tempo")),
    }


def main() -> None:
    engine = banco.criar_engine(RAIZ)
    Sessao = banco.fabrica_sessao(engine)
    s = Sessao()

    # O `fonte:` do front matter às vezes vem como abreviação ("PHB") e às vezes como nome
    # completo ("Xanathar's Guide to Everything") — inconsistência já existente na wiki, não
    # introduzida aqui. Casa pelos dois pra não perder o vínculo.
    fontes_por_chave = {}
    for f in banco.listar_fontes(s):
        fontes_por_chave[f.abreviacao] = f
        fontes_por_chave[f.nome] = f
    existentes = {m.nome.casefold(): m for m in s.query(banco.Magia).all()}

    criadas = atualizadas = ja_completas = puladas = 0
    fontes_vistas: set[str] = set()
    for pagina in sorted(PASTA_MAGIAS.glob("*.md")):
        if pagina.stem == "index":
            continue
        meta, corpo = wd._front_matter(wd._ler(pagina))
        bloco = meta.get("magia")
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
            magia = banco.Magia(nome=nome, fonte_id=fonte_id, **campos)
            s.add(magia)
            existentes[nome.casefold()] = magia
            criadas += 1
        else:
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
        banco.marcar_fonte_importada(s, abreviacao, "docs/magias/*.md")
    print(
        f"magias: {criadas} criada(s), {atualizadas} atualizada(s), "
        f"{ja_completas} já completa(s), {puladas} página(s) sem bloco magia:."
    )


if __name__ == "__main__":
    main()
