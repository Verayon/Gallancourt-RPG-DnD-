#!/usr/bin/env python3
"""Popula `banco.Classe` (as 12 classes base do Livro do Jogador 2014) a partir do markdown
convertido — só o Dado de Vida é extraído do livro (linha "Dado de Vida: 1dN", formato estável em
todas as 12 classes); atributo/progressão de conjuração vêm de uma tabela fixa (regra pública do
SRD, não ambígua, sem necessidade de parsear prosa pra isso).

**Escopo reduzido nesta rodada**: NÃO importa `ClasseFeature`/`Subclasse`. A tabela de progressão
por nível que daria "em qual nível vem cada característica" saiu do Docling com cabeçalhos
badalados de forma diferente por classe (ex.: conjuradores têm colunas extras de espaços de
magia, cada uma mangled de um jeito) — não é seguro extrair nível→característica sem risco de
atribuir a característica errada ao nível errado numa referência de regras. `ClasseFeature`
continua crescendo sob demanda, como já era antes (ver personagens_api.subir_de_nivel) — só a
ficha de Classe em si (dado de vida, atributo de conjuração) é que passa a vir pré-semeada.

One-off, idempotente: casa por `nome` antes de criar.

Uso:
    python scripts/importar_classes_livro.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "admin"))

import banco  # noqa: E402

ARQUIVO_LIVRO = RAIZ / "referencias" / "pdfs" / "md" / (
    "D&D 5E - Livro do Jogador (Fundo Branco) - Biblioteca Élfica.md"
)

# (nome exibido, título "##" no livro, slug em docs/classes/, atributo_conjuracao, progressao)
# Atributo/progressão são regra pública do SRD (não extraídos do texto — ver docstring do módulo).
CLASSES = [
    ("Bárbaro", "BÁRBARO", "barbaro", None, None),
    ("Bardo", "BARDO", "bardo", "carisma", "completo"),
    ("Bruxo", "BRUXO", "bruxo", "carisma", "pacto"),
    ("Clérigo", "CLÉRIGO", "clerigo", "sabedoria", "completo"),
    ("Druida", "DRUIDA", "druida", "sabedoria", "completo"),
    ("Feiticeiro", "FEITICEIRO", "feiticeiro", "carisma", "completo"),
    ("Guerreiro", "GUERREIRO", "guerreiro", None, None),
    ("Ladino", "LADINO", "ladino", None, None),
    ("Mago", "MAGO", "mago", "inteligencia", "completo"),
    ("Monge", "MONGE", "monge", None, None),
    ("Paladino", "PALADINO", "paladino", "carisma", "meio"),
    ("Patrulheiro", "PATRULHEIRO", "patrulheiro", "sabedoria", "meio"),
]

RE_DADO_VIDA = re.compile(r"Dado de Vida:\s*1d(\d+)", re.IGNORECASE)


def _secoes(texto: str) -> dict[str, tuple[int, int]]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", texto, re.MULTILINE))
    secoes = {}
    for i, m in enumerate(matches):
        inicio = m.end()
        fim = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        titulo = m.group(1).strip()
        if titulo not in secoes:  # primeira ocorrência (o capítulo da classe, não uma referência)
            secoes[titulo] = (inicio, fim)
    return secoes


def main() -> None:
    texto = ARQUIVO_LIVRO.read_text(encoding="utf-8")
    secoes = _secoes(texto)

    engine = banco.criar_engine(RAIZ)
    Sessao = banco.fabrica_sessao(engine)
    s = Sessao()

    fonte_phb = s.query(banco.Fonte).filter(banco.Fonte.abreviacao == "PHB").first()
    existentes = {c.nome.casefold(): c for c in s.query(banco.Classe).all()}

    criadas = atualizadas = puladas = 0
    for nome, titulo, slug, atributo, progressao in CLASSES:
        if titulo not in secoes:
            puladas += 1
            continue
        inicio, fim = secoes[titulo]
        # Olha bem além do fim da seção "## <CLASSE>" raiz, já que "Dado de Vida" mora dentro de
        # uma sub-seção ("## PONTOS DE VIDA") depois de toda a prosa introdutória + tabela de
        # progressão da classe (classes com texto introdutório mais longo passam de 14000
        # caracteres até lá — medido nas 12 classes antes de fixar este valor).
        m = RE_DADO_VIDA.search(texto[inicio:inicio + 20000])
        dado_vida = int(m.group(1)) if m else None
        if dado_vida is None:
            puladas += 1
            continue

        existente = existentes.get(nome.casefold())
        if existente is None:
            s.add(banco.Classe(
                nome=nome, dado_vida=dado_vida, atributo_conjuracao=atributo,
                progressao_conjuracao=progressao, fonte_id=fonte_phb.id if fonte_phb else None,
                pagina_rel_docs=f"classes/{slug}.md",
            ))
            criadas += 1
        else:
            if not existente.pagina_rel_docs:
                existente.pagina_rel_docs = f"classes/{slug}.md"
            if not existente.fonte_id and fonte_phb:
                existente.fonte_id = fonte_phb.id
            if not existente.atributo_conjuracao and atributo:
                existente.atributo_conjuracao = atributo
            if not existente.progressao_conjuracao and progressao:
                existente.progressao_conjuracao = progressao
            atualizadas += 1

    s.commit()
    if fonte_phb:
        banco.marcar_fonte_importada(
            s, "PHB", "referencias/pdfs/md/D&D 5E - Livro do Jogador (Fundo Branco) - Biblioteca Élfica.md",
        )
    print(f"classes: {criadas} criada(s), {atualizadas} atualizada(s), {puladas} pulada(s) (seção não encontrada).")


if __name__ == "__main__":
    main()
