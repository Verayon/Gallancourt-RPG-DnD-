#!/usr/bin/env python3
"""Popula `banco.Raca`/`banco.RacaTraco` a partir do capítulo de raças do Livro do Jogador
convertido (`referencias/pdfs/md/`). Esse markdown não é estruturado (é prosa, ao contrário de
docs/magias|itens, que já têm front matter) — por isso o parsing aqui é por heurística: cada raça
base vira `## <NOME>` seguido, em algum ponto, de `## TRAÇOS RACIAIS DOS <NOME>S`; sub-raças
(Alto Elfo, Anão da Montanha...) são `##` próprios, com os traços direto no corpo (sem sub-seção
"TRAÇOS RACIAIS"). Dentro de cada seção, um parágrafo "Nome do Traço. Descrição..." (nome curto,
sem vírgula, antes do primeiro ponto) é tratado como um traço; o resto é só prosa/lore, ignorado.

One-off, idempotente: casa por `nome` antes de criar.

Uso:
    python scripts/importar_racas_livro.py
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "admin"))

import banco  # noqa: E402

ARQUIVO_LIVRO = RAIZ / "referencias" / "pdfs" / "md" / (
    "D&D 5E - Livro do Jogador (Fundo Branco) - Biblioteca Élfica.md"
)

# (nome exibido, título "##" no livro, título da seção "TRAÇOS RACIAIS DOS ..." (plural
# irregular — "anões", não "anãos" — por isso é explícito, não gerado por regra), slug da página
# em docs/racas/, [sub-raças (título no livro, nome exibido)])
RACAS_BASE = [
    ("Anão", "ANÃO", "TRAÇOS RACIAIS DOS ANÕES", "anao",
     [("ANÃO DA COLINA", "Anão da Colina"), ("ANÃO DA MONTANHA", "Anão da Montanha")]),
    ("Elfo", "ELFO", "TRAÇOS RACIAIS DOS ELFOS", "elfo", [
        ("ALTO ELFO", "Alto Elfo"), ("ELFO DA FLORESTA", "Elfo da Floresta"),
        ("ELFO NEGRO (DROW)", "Elfo Negro (Drow)"),
    ]),
    ("Halfling", "HALFLING", "TRAÇOS RACIAIS DOS HALFLINGS", "halfling",
     [("PÉS LEVES", "Halfling Pés Leves"), ("ROBUSTO", "Halfling Robusto")]),
    ("Humano", "HUMANO", "TRAÇOS RACIAIS DOS HUMANOS", "humano", []),
    ("Draconato", "DRACONATO", "TRAÇOS RACIAIS DOS DRACONATOS", "draconato", []),
    ("Gnomo", "GNOMO", "TRAÇOS RACIAIS DOS GNOMOS", "gnomo",
     [("GNOMO DA FLORESTA", "Gnomo da Floresta"), ("GNOMO DAS ROCHAS", "Gnomo das Rochas")]),
    ("Meio-Elfo", "MEIO-ELFO", "TRAÇOS RACIAIS DOS MEIO-ELFOS", "meio-elfo", []),
    ("Meio-Orc", "MEIO-ORC", "TRAÇOS RACIAIS DOS MEIO-ORCS", "meio-orc", []),
    ("Tiefling", "TIEFLING", "TRAÇOS RACIAIS DOS TIEFLINGS", "tiflin", []),
]

RE_SECAO = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
RE_TRACO = re.compile(r"^([^.\n,]{1,45})\.\s+(.+)$", re.DOTALL)
RE_TAMANHO = re.compile(r"tamanho é (\w+)", re.IGNORECASE)
RE_DESLOCAMENTO = re.compile(r"(\d+(?:[.,]\d+)?)\s*metros?", re.IGNORECASE)


def _secoes(texto: str) -> list[tuple[str, int, int]]:
    """Lista (título, início_do_corpo, fim_do_corpo) de cada seção `##`, nessa ordem."""
    matches = list(RE_SECAO.finditer(texto))
    secoes = []
    for i, m in enumerate(matches):
        inicio = m.end()
        fim = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        secoes.append((m.group(1).strip(), inicio, fim))
    return secoes


def _extrair_tracos(corpo: str) -> list[tuple[str, str]]:
    tracos = []
    for paragrafo in re.split(r"\n\s*\n", corpo):
        paragrafo = paragrafo.strip()
        if not paragrafo:
            continue
        m = RE_TRACO.match(paragrafo)
        if m:
            tracos.append((m.group(1).strip(), m.group(2).strip()))
    return tracos


def _maiusculas_demais(paragrafo: str) -> bool:
    """Parágrafos de abertura às vezes vêm com a primeira frase inteira em caixa alta (artefato
    do versalete do livro original) — não é bom descricao, prefere o próximo parágrafo normal."""
    letras = [c for c in paragrafo if c.isalpha()]
    if not letras:
        return False
    return sum(1 for c in letras if c.isupper()) / len(letras) > 0.5


def _primeiro_paragrafo(corpo: str) -> str | None:
    candidato = None
    for paragrafo in re.split(r"\n\s*\n", corpo):
        paragrafo = paragrafo.strip()
        if not paragrafo or paragrafo.startswith("<!--") or paragrafo.startswith("-"):
            continue
        if candidato is None:
            candidato = paragrafo
        if not _maiusculas_demais(paragrafo):
            return paragrafo
    return candidato


def _upsert_traco(sessao: banco.Session, raca: banco.Raca, nome: str, descricao: str) -> bool:
    existente = next((t for t in raca.tracos_vinculo if t.nome.casefold() == nome.casefold()), None)
    if existente is not None:
        return False
    sessao.add(banco.RacaTraco(raca_id=raca.id, nome=nome, descricao=descricao))
    return True


def _upsert_raca(
    sessao: banco.Session, existentes: dict, nome: str, fonte_id: int | None, pagina_rel_docs: str | None,
    raca_pai_id: int | None, descricao: str | None, tracos: list[tuple[str, str]],
) -> tuple[banco.Raca, bool, int]:
    criada = False
    raca = existentes.get(nome.casefold())
    if raca is None:
        raca = banco.Raca(
            nome=nome, fonte_id=fonte_id, pagina_rel_docs=pagina_rel_docs, raca_pai_id=raca_pai_id,
            descricao=descricao,
        )
        sessao.add(raca)
        sessao.flush()
        existentes[nome.casefold()] = raca
        criada = True
    else:
        if not raca.descricao and descricao:
            raca.descricao = descricao
        if not raca.pagina_rel_docs and pagina_rel_docs:
            raca.pagina_rel_docs = pagina_rel_docs
        if not raca.fonte_id and fonte_id:
            raca.fonte_id = fonte_id

    for nome_traco, nome_exibido in [("Tamanho", "tamanho"), ("Deslocamento", "deslocamento")]:
        descricao_traco = next((d for n, d in tracos if n.casefold() == nome_traco.casefold()), None)
        if not descricao_traco:
            continue
        if nome_exibido == "tamanho" and not raca.tamanho:
            m = RE_TAMANHO.search(descricao_traco)
            if m:
                raca.tamanho = m.group(1)
        elif nome_exibido == "deslocamento" and not raca.deslocamento:
            m = RE_DESLOCAMENTO.search(descricao_traco)
            if m:
                raca.deslocamento = round(float(m.group(1).replace(",", ".")))

    novos_tracos = sum(1 for nome_t, desc_t in tracos if _upsert_traco(sessao, raca, nome_t, desc_t))
    return raca, criada, novos_tracos


def main() -> None:
    texto = ARQUIVO_LIVRO.read_text(encoding="utf-8")
    secoes = {titulo: (inicio, fim) for titulo, inicio, fim in _secoes(texto)}

    engine = banco.criar_engine(RAIZ)
    Sessao = banco.fabrica_sessao(engine)
    s = Sessao()

    fonte_phb = s.query(banco.Fonte).filter(banco.Fonte.abreviacao == "PHB").first()
    existentes = {r.nome.casefold(): r for r in s.query(banco.Raca).all()}

    racas_criadas = subracas_criadas = tracos_criados = 0
    for nome_raca, titulo_base, titulo_tracos, slug_pagina, subracas in RACAS_BASE:
        pagina = f"racas/{slug_pagina}.md"

        descricao = None
        if titulo_base in secoes:
            inicio, fim = secoes[titulo_base]
            descricao = _primeiro_paragrafo(texto[inicio:fim])

        tracos = []
        if titulo_tracos in secoes:
            inicio, fim = secoes[titulo_tracos]
            tracos = _extrair_tracos(texto[inicio:fim])

        raca, criada, novos_tracos = _upsert_raca(
            s, existentes, nome_raca, fonte_phb.id if fonte_phb else None, pagina, None, descricao, tracos,
        )
        racas_criadas += 1 if criada else 0
        tracos_criados += novos_tracos

        for titulo_sub, nome_sub in subracas:
            if titulo_sub not in secoes:
                continue
            inicio, fim = secoes[titulo_sub]
            corpo_sub = texto[inicio:fim]
            tracos_sub = _extrair_tracos(corpo_sub)
            descricao_sub = _primeiro_paragrafo(corpo_sub)
            _, sub_criada, sub_novos_tracos = _upsert_raca(
                s, existentes, nome_sub, fonte_phb.id if fonte_phb else None, pagina, raca.id,
                descricao_sub, tracos_sub,
            )
            subracas_criadas += 1 if sub_criada else 0
            tracos_criados += sub_novos_tracos

    s.commit()
    if fonte_phb:
        banco.marcar_fonte_importada(
            s, "PHB", "referencias/pdfs/md/D&D 5E - Livro do Jogador (Fundo Branco) - Biblioteca Élfica.md",
        )
    total_racas = s.query(banco.Raca).count()
    total_tracos = s.query(banco.RacaTraco).count()
    print(
        f"raças: {racas_criadas} base(s) criada(s), {subracas_criadas} sub-raça(s) criada(s), "
        f"{tracos_criados} traço(s) novo(s) — {total_racas} raça(s)/{total_tracos} traço(s) no total."
    )


if __name__ == "__main__":
    main()
