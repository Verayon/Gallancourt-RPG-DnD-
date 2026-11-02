"""Migração de uso único: tira os monstros do Markdown estático e coloca no banco (ver
admin/banco.py, admin/monstros_api.py e ARQUITETURA.md).

O que faz, nesta ordem:
1. Lê docs/itens/*.md e docs/magias/*.md e espelha cada um como uma linha em `equipamentos`/
   `magias` (catálogos compartilhados) — essas páginas NÃO são tocadas nem apagadas.
2. Lê cada docs/monstros/*.md (ficha de combate embutida, já existente) e cria `Monstro` +
   `FichaMonstro` (is_base=True) com os atributos convertidos para inteiro.
3. Tenta casar o campo livre "equipamento" de cada monstro com o catálogo de equipamentos
   (por nome, melhor-esforço); o que não casar vira uma entrada nova de equipamento, marcada
   com a origem (aquele monstro). Em qualquer caso, vincula à ficha Base.
4. Separa traços/ações/reações em habilidades individuais (via wd.linhas_para_trechos), tentando
   extrair bônus de acerto e dano por regex — o que não casar vira habilidade só com descrição.
5. Reescreve cada docs/monstros/<slug>.md para o formato reduzido (front matter + H1 + marcador
   `<!-- monstro:ficha-dinamica -->`), mantendo o `monstro:` do front matter como está.

Rode com `--root <pasta>` para testar numa cópia antes de rodar no projeto real (nunca roda em
cima do real sem confirmar — ver `--confirmar`).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROJETO / "admin"))
sys.path.insert(0, str(RAIZ_PROJETO / "hooks"))

import banco  # noqa: E402
import monstros_api as ma  # noqa: E402
import wiki_data as wd  # noqa: E402

_RE_ACERTO = re.compile(r"\+(\d+)\s+para acertar")
_RE_DANO = re.compile(r"Acerto:\s*\d+\s*\(([\dd+\-\s]+)\)\s*de dano (\w+)", re.IGNORECASE)
_RE_DANO_ITEM = re.compile(r"^([\dd]+(?:\s*[+\-]\s*\d+)?)\s*(.*)$")
_RE_CA_FIXA = re.compile(r"^\+?(\d+)$")


def _para_int(valor, padrao=10) -> int:
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return padrao


def migrar_itens(sessao, docs: Path) -> dict[str, int]:
    """docs/itens/*.md -> tabela `equipamentos`. Devolve {nome em minúsculas: id} para o
    casamento de equipamento dos monstros."""
    indice: dict[str, int] = {}
    pasta = docs / "itens"
    for arquivo in sorted(pasta.glob("*.md")):
        if arquivo.name == "index.md":
            continue
        texto = arquivo.read_text(encoding="utf-8")
        meta, corpo = wd._front_matter(texto)
        item = meta.get("item") or {}
        nome = wd._titulo_do_arquivo(arquivo)
        descricao = re.sub(r"^#.+\n+", "", corpo, count=1).strip()

        dano_formula = dano_tipo = None
        dano_txt = (item.get("dano") or "").strip()
        if dano_txt:
            m = _RE_DANO_ITEM.match(dano_txt)
            if m:
                dano_formula, dano_tipo = m.group(1).strip(), m.group(2).strip() or None

        ca_txt = str(item.get("ca") or "").strip()
        ca_bonus = None
        ca_formula = ca_txt or None
        m_ca = _RE_CA_FIXA.match(ca_txt)
        if m_ca:
            ca_bonus = int(m_ca.group(1))
            ca_formula = None

        obj = banco.Equipamento(
            nome=nome, categoria=item.get("categoria"), custo=item.get("custo"),
            peso=item.get("peso"), dano_formula=dano_formula, dano_tipo=dano_tipo,
            propriedades=item.get("propriedades"), ca_bonus=ca_bonus, ca_formula=ca_formula,
            raridade=item.get("raridade"), fonte=item.get("fonte"), descricao=descricao or None,
            slug_origem=f"itens/{arquivo.name}",
        )
        sessao.add(obj)
        sessao.flush()
        indice[nome.lower()] = obj.id
    sessao.commit()
    return indice


def migrar_magias(sessao, docs: Path) -> None:
    pasta = docs / "magias"
    for arquivo in sorted(pasta.rglob("*.md")):
        if arquivo.name == "index.md" or arquivo.parent.name == "por-classe":
            continue
        texto = arquivo.read_text(encoding="utf-8")
        meta, corpo = wd._front_matter(texto)
        magia = meta.get("magia")
        if not isinstance(magia, dict):
            continue
        nome = wd._titulo_do_arquivo(arquivo)
        descricao = re.sub(r"^#.+\n+", "", corpo, count=1).strip()
        classes = magia.get("classes")
        classes_txt = ", ".join(classes) if isinstance(classes, list) else (classes or None)
        # `dano` no front matter é sempre uma tabela de escala por nível ([[rótulo, dado], ...]),
        # nunca uma fórmula única — resume numa string legível ("1d6 (1º); 2d6 (2º); …").
        dano_lista = magia.get("dano")
        dano_formula = None
        if isinstance(dano_lista, list):
            dano_formula = "; ".join(f"{dado} ({rotulo})" for rotulo, dado in dano_lista)
        sessao.add(banco.Magia(
            nome=nome, nivel=magia.get("nivel"), escola=magia.get("escola"),
            tempo=magia.get("tempo"), alcance=magia.get("alcance"),
            componentes=magia.get("componentes"), duracao=magia.get("duracao"),
            classes=classes_txt, dano_formula=dano_formula,
            dano_tipo=(magia.get("dano_tipo") or None) if magia.get("dano_tipo") != "Nenhum" else None,
            resistencia=magia.get("resistencia"),
            fonte=magia.get("fonte"), descricao=descricao or None,
            slug_origem=f"magias/{arquivo.relative_to(pasta).as_posix()}",
        ))
    sessao.commit()


def _casar_equipamento(indice_itens: dict[str, int], fragmento: str) -> int | None:
    alvo = fragmento.strip().lower()
    if not alvo:
        return None
    if alvo in indice_itens:
        return indice_itens[alvo]
    for nome, item_id in indice_itens.items():
        if nome in alvo or alvo in nome:
            return item_id
    return None


def migrar_monstro(sessao, caminho: Path, indice_itens: dict[str, int]) -> str | None:
    texto = caminho.read_text(encoding="utf-8")
    meta, _corpo = wd._front_matter(texto)
    monstro_meta = meta.get("monstro")
    if not isinstance(monstro_meta, dict):
        return None
    slug = caminho.stem
    blocos = wd.ler_statblocks_da_pagina(caminho)
    if not blocos:
        return None
    # A primeira ficha do arquivo (em ordem de aparição no texto) vira a Base; demais (variantes
    # já criadas antes desta migração) viram fichas adicionais, pelo rótulo salvo em cada uma.
    ordem = [m.group(1) for m in wd._MARCADOR_DADOS.finditer(texto)]
    nome_arquivo = wd._titulo_do_arquivo(caminho)

    monstro = ma.criar_monstro(
        sessao, slug, nome_arquivo, monstro_meta.get("tamanho"), monstro_meta.get("tipo"),
        monstro_meta.get("alinhamento"),
    )

    for i, slug_ficha in enumerate(ordem):
        v = blocos.get(slug_ficha)
        if v is None:
            continue
        rotulo = (v.get("rotulo_variante") or "").strip() or ("Base" if i == 0 else f"Variante {i + 1}")

        ca_texto = str(v.get("ca") or "")
        m_ca = re.match(r"\d+", ca_texto)
        ca_total = _para_int(m_ca.group() if m_ca else None, 10)

        pv_texto = str(v.get("pv") or "")
        m_pv = re.match(r"\d+", pv_texto)
        pv_maximo = _para_int(m_pv.group() if m_pv else None, 1)
        m_formula = re.search(r"\(([^)]+)\)", pv_texto)
        pv_formula = m_formula.group(1) if m_formula else None
        pv_atual = _para_int(v.get("pv_atual"), pv_maximo)

        ficha = banco.FichaMonstro(
            monstro_id=monstro.id, rotulo=rotulo, is_base=(i == 0),
            cr=v.get("cr") or None, bonus_proficiencia=_para_int(v.get("bonus_proficiencia"), 2),
            forca=_para_int(v.get("for")), destreza=_para_int(v.get("des")),
            constituicao=_para_int(v.get("con")), inteligencia=_para_int(v.get("int")),
            sabedoria=_para_int(v.get("sab")), carisma=_para_int(v.get("car")),
            ca_total=ca_total, pv_formula=pv_formula, pv_maximo=pv_maximo, pv_atual=pv_atual,
            deslocamento=v.get("deslocamento") or None, sentidos=v.get("sentidos") or None,
            idiomas=v.get("idiomas") or None, pericias=v.get("pericias") or None,
        )
        sessao.add(ficha)
        sessao.flush()

        # Fontes de equipamento: o campo "equipamento" (texto livre) e o que estiver entre
        # parênteses na CA (ex.: "15 (armadura de couro, escudo)") — é de lá que normalmente vem
        # a armadura/escudo de um monstro, já que poucos preenchiam o campo "equipamento" à parte.
        m_ca_motivo = re.search(r"\(([^)]+)\)", ca_texto)
        fragmentos_equip = (v.get("equipamento") or "").split(",")
        if m_ca_motivo:
            fragmentos_equip += m_ca_motivo.group(1).split(",")
        vistos_equip: set[str] = set()
        for fragmento in fragmentos_equip:
            fragmento = fragmento.strip()
            chave = fragmento.lower()
            if not fragmento or chave in vistos_equip:
                continue
            vistos_equip.add(chave)
            item_id = _casar_equipamento(indice_itens, fragmento)
            if item_id is None:
                novo = banco.Equipamento(
                    nome=fragmento, categoria=None, origem_tipo=monstro_meta.get("tipo"),
                    origem_monstro_slug=slug,
                )
                sessao.add(novo)
                sessao.flush()
                item_id = novo.id
            sessao.add(banco.FichaEquipamento(ficha_id=ficha.id, equipamento_id=item_id))

        for campo, tipo in (("tracos", "traco"), ("acoes", "acao"), ("reacoes", "reacao")):
            for nome_h, desc_h in wd.linhas_para_trechos(v.get(campo) or ""):
                if not nome_h and not desc_h:
                    continue
                bonus_acerto = None
                m_acerto = _RE_ACERTO.search(desc_h)
                if m_acerto:
                    bonus_acerto = int(m_acerto.group(1))
                dano_formula = dano_tipo = None
                m_dano = _RE_DANO.search(desc_h)
                if m_dano:
                    dano_formula, dano_tipo = m_dano.group(1).strip(), m_dano.group(2)
                habilidade = banco.Habilidade(
                    nome=nome_h or (desc_h[:60] or "Sem nome"), tipo=tipo,
                    bonus_acerto=bonus_acerto, dano_formula=dano_formula, dano_tipo=dano_tipo,
                    descricao=desc_h or None, origem_tipo=monstro_meta.get("tipo"),
                    origem_monstro_slug=slug,
                )
                sessao.add(habilidade)
                sessao.flush()
                sessao.add(banco.FichaHabilidade(ficha_id=ficha.id, habilidade_id=habilidade.id))

    sessao.commit()
    return slug


_MARCADOR_PAGINA_MONSTRO = """---
tags:
  - Monstros
monstro:
  tamanho: {tamanho}
  tipo: {tipo}
  alinhamento: {alinhamento}
---

# {titulo}

<!-- monstro:ficha-dinamica -->
"""


def reduzir_pagina_monstro(caminho: Path) -> None:
    texto = caminho.read_text(encoding="utf-8")
    meta, corpo = wd._front_matter(texto)
    monstro_meta = meta.get("monstro") or {}
    titulo = wd._titulo_do_arquivo(caminho)
    novo_texto = _MARCADOR_PAGINA_MONSTRO.format(
        tamanho=monstro_meta.get("tamanho") or "", tipo=monstro_meta.get("tipo") or "",
        alinhamento=monstro_meta.get("alinhamento") or "", titulo=titulo,
    )
    caminho.write_text(novo_texto, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(RAIZ_PROJETO), help="Raiz do projeto (ou de uma cópia de teste)")
    parser.add_argument("--confirmar", action="store_true", help="Sem isso, só simula e mostra o que faria")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    docs = root / "docs"
    engine = banco.criar_engine(root)
    Sessao = banco.fabrica_sessao(engine)

    pasta_monstros = docs / "monstros"
    arquivos = sorted(p for p in pasta_monstros.glob("*.md") if p.name != "index.md")

    if not args.confirmar:
        print(f"[simulação] migraria {len(arquivos)} monstros + itens/magias de {docs}.")
        print("Rode de novo com --confirmar para aplicar.")
        return

    with Sessao() as sessao:
        print("Migrando itens...")
        indice_itens = migrar_itens(sessao, docs)
        print(f"  {len(indice_itens)} itens migrados para 'equipamentos'.")

        print("Migrando magias...")
        migrar_magias(sessao, docs)
        total_magias = sessao.query(banco.Magia).count()
        print(f"  {total_magias} magias migradas.")

        print("Migrando monstros...")
        migrados = []
        for caminho in arquivos:
            slug = migrar_monstro(sessao, caminho, indice_itens)
            if slug:
                migrados.append(slug)
        print(f"  {len(migrados)} monstros migrados.")

    print("Reduzindo páginas docs/monstros/*.md...")
    for caminho in arquivos:
        reduzir_pagina_monstro(caminho)
    print("Concluído.")


if __name__ == "__main__":
    main()
