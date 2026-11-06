#!/usr/bin/env python3
"""Popula `Personagem`(tipo="monstro")/`Ficha` a partir dos stat blocks do Manual dos Monstros
convertido — só os que casam com um padrão limpo e reconhecível (ver módulo). Nunca toca um
monstro cujo slug já exista (98 já foram importados manualmente antes desta rodada) — só
adiciona os que faltam. Gera a página mínima em docs/monstros/<slug>.md (mesmo formato das 98 já
existentes: tags + bloco `monstro:` + marcador) só quando ela ainda não existe.

Stat blocks que não casam com o padrão esperado (~25% do livro, corrompidos por um artefato do
Docling que duplica cabeçalho/CA/PV numa tabela de 6 colunas) são listados em
`referencias/pdfs/md/monstros-nao-importados.md` em vez de entrar com dado errado.

One-off, idempotente (roda de novo sem duplicar — os já criados ficam de fora por já terem slug).

Uso:
    python scripts/importar_monstros_livro.py
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
    "D&D 5E - Manual dos Monstros (D&D Beyond 2.1) - Biblioteca Élfica.md"
)
RELATORIO = RAIZ / "referencias" / "pdfs" / "md" / "monstros-nao-importados.md"

TAMANHOS = ("Minúsculo", "Pequeno", "Médio", "Grande", "Enorme", "Imenso")
# O livro usa "Besta"/"mau"/"imparcial" — a wiki (98 monstros já importados antes) usa
# "Fera"/"maligno"/"Sem alinhamento". Mantém consistência com o que já existe, em vez de
# introduzir uma segunda nomenclatura.
TIPO_LIVRO_PARA_WIKI = {"Besta": "Fera"}
RE_MAU = re.compile(r"\bmau\b", re.IGNORECASE)

RE_CABECALHO = re.compile(
    r"^([A-Za-zÀ-ÿ()\-\s]+?)\s+(" + "|".join(TAMANHOS) + r"),\s*(.+?)\s*$", re.MULTILINE,
)
RE_CA = re.compile(r"Classe de Armadura\s+(\d+)")
RE_PV = re.compile(r"Pontos de Vida\s+(\d+)\s*(?:\(([^)]+)\))?")
RE_DESLOCAMENTO = re.compile(r"Deslocamento\s+(\d+(?:[.,]\d+)?)\s*m([^\n|]*)")
RE_ATRIBUTOS = re.compile(
    r"\|\s*(\d+)\s*\([^)]*\)\s*\|\s*(\d+)\s*\([^)]*\)\s*\|\s*(\d+)\s*\([^)]*\)\s*\|"
    r"\s*(\d+)\s*\([^)]*\)\s*\|\s*(\d+)\s*\([^)]*\)\s*\|\s*(\d+)\s*\([^)]*\)\s*\|"
)
RE_PERCEPCAO_PASSIVA = re.compile(r"Percepção passiva\s+(\d+)")
RE_CR = re.compile(r"Nível de Desafio\s+([\d/]+)")
RE_DANO_MODO = re.compile(
    r"(Resistência|Imunidade|Vulnerabilidade) a Dano\s+(.+?)"
    r"(?=;|\s+Imunidade a Condição|\s+Sentidos\b|\s+Idiomas\b|\s+Nível de Desafio\b|\n\n|$)",
    re.IGNORECASE,
)
MODO_POR_PALAVRA = {"resistência": "resistente", "imunidade": "imune", "vulnerabilidade": "vulneravel"}
RE_TRACO_PARAGRAFO = re.compile(r"^([^.\n,]{1,50})\.\s+(.+)$", re.DOTALL)


def _slug(nome: str) -> str:
    base = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base or "monstro"


def _nome_limpo(titulo: str) -> str:
    """Desduplica o artefato "GRELL GRELL"/"HARPIA HARPIA" (nome repetido 2x na mesma linha de
    cabeçalho) e devolve em Title Case."""
    palavras = titulo.split()
    meio = len(palavras) // 2
    if len(palavras) % 2 == 0 and palavras[:meio] == palavras[meio:]:
        palavras = palavras[:meio]
    return " ".join(palavras).title()


def _secoes_subcapitulo(texto: str) -> list[tuple[str, int, int]]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", texto, re.MULTILINE))
    return [
        (m.group(1).strip(), m.end(), matches[i + 1].start() if i + 1 < len(matches) else len(texto))
        for i, m in enumerate(matches)
    ]


def _extrair_tracos(corpo: str) -> list[tuple[str, str]]:
    tracos = []
    for paragrafo in re.split(r"\n\s*\n", corpo):
        paragrafo = paragrafo.strip()
        m = RE_TRACO_PARAGRAFO.match(paragrafo) if paragrafo else None
        if m:
            tracos.append((m.group(1).strip(), m.group(2).strip().replace("\n", " ")))
    return tracos


def _resistencias_dano(bloco: str) -> list[tuple[str, str]]:
    resultado = []
    for m in RE_DANO_MODO.finditer(bloco):
        modo = MODO_POR_PALAVRA[m.group(1).casefold()]
        for fragmento in re.split(r",| e ", m.group(2)):
            fragmento = fragmento.strip().rstrip(".;")
            if not fragmento:
                continue
            tipo = next((t for t in banco.TIPOS_DANO if fragmento.casefold().startswith(t.casefold())), None)
            if tipo:
                resultado.append((tipo, modo))
    return resultado


def main() -> None:
    texto = ARQUIVO_LIVRO.read_text(encoding="utf-8")
    secoes = _secoes_subcapitulo(texto)

    # Um cabeçalho é início de stat block quando a 1ª linha não-vazia do corpo bate o padrão
    # "<tipo> <tamanho>, <alinhamento>" — isso já separa automaticamente cabeçalhos de família
    # (ex. "## GOBLINS", só prosa) e de sub-seção ("## AÇÕES") dos de monstro de verdade.
    blocos_monstro = []
    for titulo, inicio, fim in secoes:
        primeira_linha = texto[inicio:fim].strip().split("\n", 1)[0]
        m = RE_CABECALHO.match(primeira_linha)
        if m:
            blocos_monstro.append((titulo, inicio, fim, m))

    engine = banco.criar_engine(RAIZ)
    Sessao = banco.fabrica_sessao(engine)
    s = Sessao()

    slugs_existentes = {p.slug for p in s.query(banco.Personagem).filter(banco.Personagem.tipo == "monstro").all()}
    fonte_mm = s.query(banco.Fonte).filter(banco.Fonte.abreviacao == "MM").first()

    criados = pulados_existentes = falhas = 0
    nomes_falha = []
    for titulo, inicio, fim, m_cabecalho in blocos_monstro:
        nome = _nome_limpo(titulo)
        slug = _slug(nome)
        if slug in slugs_existentes:
            pulados_existentes += 1
            continue

        bloco = texto[inicio:fim]
        ca = RE_CA.search(bloco)
        pv = RE_PV.search(bloco)
        atributos = RE_ATRIBUTOS.search(bloco)
        cr = RE_CR.search(bloco)
        if not (ca and pv and atributos and cr):
            falhas += 1
            nomes_falha.append(nome)
            continue

        tipo_criatura = m_cabecalho.group(1).strip()
        tipo_criatura = TIPO_LIVRO_PARA_WIKI.get(tipo_criatura, tipo_criatura)
        tamanho = m_cabecalho.group(2).strip()
        alinhamento = m_cabecalho.group(3).strip()
        alinhamento = "Sem alinhamento" if alinhamento.casefold() == "imparcial" else RE_MAU.sub("maligno", alinhamento)

        deslocamento_m = deslocamento_extra = None
        m_desl = RE_DESLOCAMENTO.search(bloco)
        if m_desl:
            deslocamento_m = float(m_desl.group(1).replace(",", "."))
            extra = m_desl.group(2).strip().lstrip(",").strip()
            deslocamento_extra = extra or None

        m_perc = RE_PERCEPCAO_PASSIVA.search(bloco)

        personagem = banco.Personagem(
            tipo="monstro", slug=slug, nome=nome, tamanho=tamanho, tipo_criatura=tipo_criatura,
            alinhamento=alinhamento,
        )
        s.add(personagem)
        s.flush()

        ficha = banco.Ficha(
            personagem_id=personagem.id, rotulo="Base", is_base=True, cr=cr.group(1),
            ca_total=int(ca.group(1)), pv_maximo=int(pv.group(1)), pv_atual=int(pv.group(1)),
            dados_vida_total=pv.group(2),
            forca=int(atributos.group(1)), destreza=int(atributos.group(2)),
            constituicao=int(atributos.group(3)), inteligencia=int(atributos.group(4)),
            sabedoria=int(atributos.group(5)), carisma=int(atributos.group(6)),
            deslocamento_m=deslocamento_m if deslocamento_m is not None else 9.0,
            deslocamento_extra=deslocamento_extra,
            percepcao_passiva=int(m_perc.group(1)) if m_perc else 10,
        )
        s.add(ficha)
        s.flush()

        for tipo_dano, modo in _resistencias_dano(bloco):
            s.add(banco.FichaResistenciaDano(ficha_id=ficha.id, nome=tipo_dano, modo=modo))

        # Traços/ações: tudo até "## AÇÕES" (se houver, dentro deste mesmo bloco de texto) é
        # traço passivo; dali em diante é ação. "## AÇÕES" já está fora de `secoes_subcapitulo`
        # porque não bate o padrão de monstro — mas ainda está dentro do texto de `bloco`.
        pos_acoes = bloco.find("## AÇÕES")
        texto_tracos = bloco[:pos_acoes] if pos_acoes != -1 else bloco
        texto_acoes = bloco[pos_acoes + len("## AÇÕES"):] if pos_acoes != -1 else ""
        for nome_h, descricao, tipo_h in (
            [(n, d, "traco") for n, d in _extrair_tracos(texto_tracos)]
            + [(n, d, "acao") for n, d in _extrair_tracos(texto_acoes)]
        ):
            habilidade = banco.Habilidade(
                nome=nome_h, tipo=tipo_h, descricao=descricao,
                origem_tipo="monstro", origem_personagem_slug=slug,
                fonte_id=fonte_mm.id if fonte_mm else None,
            )
            s.add(habilidade)
            s.flush()
            s.add(banco.FichaHabilidade(ficha_id=ficha.id, habilidade_id=habilidade.id))

        pagina = RAIZ / "docs" / "monstros" / f"{slug}.md"
        if not pagina.exists():
            pagina.write_text(
                "---\n"
                "tags:\n"
                "  - Monstros\n"
                "monstro:\n"
                f"  tamanho: {tamanho}\n"
                f"  tipo: {tipo_criatura}\n"
                f"  alinhamento: {alinhamento}\n"
                "---\n\n"
                f"# {nome}\n\n"
                "<!-- personagem:ficha-dinamica -->\n",
                encoding="utf-8",
            )
        slugs_existentes.add(slug)
        criados += 1

    s.commit()
    if fonte_mm:
        banco.marcar_fonte_importada(
            s, "MM", "referencias/pdfs/md/D&D 5E - Manual dos Monstros (D&D Beyond 2.1) - Biblioteca Élfica.md",
        )
    if nomes_falha:
        RELATORIO.write_text(
            "# Monstros não importados automaticamente\n\n"
            "Stat block não casou com o padrão esperado (provável artefato de conversão do "
            "Docling — tabela de atributos ou CA/PV duplicados/corrompidos). Revisar manualmente "
            "contra o PDF original antes de cadastrar.\n\n"
            + "\n".join(f"- {n}" for n in nomes_falha) + "\n",
            encoding="utf-8",
        )
    print(
        f"monstros: {criados} criado(s), {pulados_existentes} já existente(s) (slug já em uso), "
        f"{falhas} com stat block não reconhecido (ver {RELATORIO.relative_to(RAIZ)})."
    )


if __name__ == "__main__":
    main()
