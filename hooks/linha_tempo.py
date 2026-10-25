"""Linha do tempo da campanha: acontecimentos e mudanças de estado de NPCs, cidades e facções.

Fonte única: `dados/linha-do-tempo.yml` (fora de `docs/`, não é publicado como arquivo). Cada
acontecimento tem data na campanha, sessão (opcional), título, descrição, as páginas envolvidas
e, se houver, mudanças de estado ("Odette morreu", "Thalin foi para Valynesse").

Usado em dois lugares:

- `hooks/gallancourt.py` (geração do site) mostra a linha do tempo em cada página envolvida, em
  ordem cronológica, aplica as mudanças à caixa do NPC e à tabela de NPCs, e monta a página
  Mestre → Linha do tempo;
- `admin/wiki_data.py` (Painel do Mestre) acrescenta, edita e apaga acontecimentos.
"""
from __future__ import annotations

import posixpath
import re
import unicodedata
from pathlib import Path

import yaml

ARQUIVO = Path("dados") / "linha-do-tempo.yml"

CABECALHO_ARQUIVO = """\
# Linha do tempo da campanha de Gallancourt.
#
# Edite pelo Painel do Mestre (aba "Linha do tempo"). Cada acontecimento aparece, em ordem
# cronológica, na página de cada NPC, cidade ou facção envolvida; as mudanças de estado
# (situação, localização, afiliação, título) atualizam a caixa do NPC e a tabela de NPCs.
#
# Campos de cada acontecimento:
#   id         número único (o Painel preenche)
#   data       data na campanha, no formato "DD de <mês> de <ano>" (ver docs/mundo/calendario.md)
#   sessao     número da sessão (opcional)
#   titulo     resumo curto
#   descricao  texto (aceita Markdown)
#   envolvidos páginas envolvidas, relativas a docs/ (ex.: personagens/thalin.md)
#   notas      (opcional) nota específica de cada página: {pagina: texto}
#   mudancas   lista de {pagina, campo, valor}; campos: situacao, cidade, afiliacao, titulo
"""

# Campos de estado que um acontecimento pode mudar: (chave, rótulo, vale para)
CAMPOS_MUDANCA = [
    ("situacao", "Situação", "todos"),       # Morto, Desaparecido, Preso… / cidade sitiada…
    ("cidade", "Localização", "npc"),         # onde o NPC está agora
    ("afiliacao", "Afiliação", "npc"),
    ("titulo", "Título", "npc"),
]
ROTULO_MUDANCA = {c: r for c, r, _ in CAMPOS_MUDANCA}

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}


# --------------------------------------------------------------------------
# Leitura e escrita
# --------------------------------------------------------------------------

def caminho(raiz: Path) -> Path:
    return Path(raiz) / ARQUIVO


def carregar(raiz: Path) -> list[dict]:
    arq = caminho(raiz)
    if not arq.exists():
        return []
    dados = yaml.safe_load(arq.read_text(encoding="utf-8")) or {}
    eventos = dados.get("eventos") or []
    return [e for e in eventos if isinstance(e, dict)]


def salvar(raiz: Path, eventos: list[dict]) -> None:
    arq = caminho(raiz)
    arq.parent.mkdir(parents=True, exist_ok=True)
    corpo = yaml.dump({"eventos": eventos}, allow_unicode=True, sort_keys=False, width=100)
    arq.write_text(CABECALHO_ARQUIVO + "\n" + corpo, encoding="utf-8")


# --------------------------------------------------------------------------
# Ordem cronológica
# --------------------------------------------------------------------------

def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()


def chave_data(data: str) -> tuple[int, int, int] | None:
    """'24 de outubro de 1453' -> (1453, 10, 24). None se não reconhecer o formato."""
    m = re.match(r"\s*(\d{1,2})\s+de\s+([a-zçã]+)\s+de\s+(-?\d+)", _sem_acento(data or ""))
    if not m or m.group(2) not in MESES:
        return None
    return int(m.group(3)), MESES[m.group(2)], int(m.group(1))


def ordenar(eventos: list[dict]) -> list[dict]:
    """Ordem cronológica: data na campanha; sem data reconhecida, pela sessão; empate, pelo id."""
    def chave(e):
        d = chave_data(str(e.get("data") or ""))
        sessao = e.get("sessao")
        sessao = int(sessao) if str(sessao).lstrip("-").isdigit() else 10**6
        return (d is None, d or (0, 0, 0), sessao, int(e.get("id") or 0))
    return sorted(eventos, key=chave)


def paginas_do_evento(evento: dict) -> set[str]:
    paginas = set(evento.get("envolvidos") or []) | set((evento.get("notas") or {}).keys())
    paginas |= {m.get("pagina") for m in evento.get("mudancas") or [] if m.get("pagina")}
    return paginas


def eventos_da_pagina(eventos: list[dict], pagina: str) -> list[dict]:
    return [e for e in ordenar(eventos) if pagina in paginas_do_evento(e)]


def estado_atual(eventos: list[dict], pagina: str) -> dict[str, tuple[str, dict]]:
    """Último valor de cada campo mudado: {campo: (valor, evento)}."""
    estado = {}
    for e in ordenar(eventos):
        for m in e.get("mudancas") or []:
            if m.get("pagina") == pagina and m.get("campo"):
                estado[m["campo"]] = (str(m.get("valor") or ""), e)
    return estado


# --------------------------------------------------------------------------
# Exibição
# --------------------------------------------------------------------------

def _rel(destino: str, origem: str) -> str:
    return posixpath.relpath(destino, posixpath.dirname(origem) or ".")


def link_sessao(docs: Path, numero, origem: str) -> str:
    """Link para a sessão: o registro no Diário, se existir; senão, a página de preparação."""
    if numero in (None, ""):
        return ""
    try:
        n = int(numero)
    except (TypeError, ValueError):
        return f"Sessão {numero}"
    diario = f"diario/sessao-{n:02d}.md"
    if (docs / diario).exists():
        return f"[Sessão {n}]({_rel(diario, origem)})"
    preparo = sorted((docs / "mestre" / "sessoes").glob(f"sessao-{n}-*.md")) + sorted(
        (docs / "mestre" / "sessoes").glob(f"sessao-{n}.md"))
    if preparo:
        return f"[Sessão {n}]({_rel(preparo[0].relative_to(docs).as_posix(), origem)})"
    return f"Sessão {n}"


def titulo_da_pagina(docs: Path, pagina: str) -> str:
    arq = docs / pagina
    if arq.exists():
        m = re.search(r"^# (.+)$", arq.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1).strip()
    return Path(pagina).stem.replace("-", " ").title()


def _linha_evento(docs: Path, e: dict, origem: str, pagina_foco: str | None) -> list[str]:
    data = e.get("data") or "Data não definida"
    sessao = link_sessao(docs, e.get("sessao"), origem)
    cabeca = f"**{data}**" + (f" · {sessao}" if sessao else "") + f" — **{e.get('titulo') or 'Acontecimento'}**"
    linhas = [f"-   {cabeca}"]
    notas = e.get("notas") or {}
    texto = notas.get(pagina_foco) if pagina_foco and notas.get(pagina_foco) else e.get("descricao")
    if texto:
        linhas += ["", *("    " + l if l.strip() else "" for l in str(texto).strip().splitlines())]
    if not pagina_foco and notas:
        linhas += [""] + [
            f"    - [{titulo_da_pagina(docs, p)}]({_rel(p, origem)}): {n}" for p, n in notas.items() if (docs / p).exists()
        ]
    mudancas = [m for m in e.get("mudancas") or [] if pagina_foco is None or m.get("pagina") == pagina_foco]
    if mudancas:
        textos = []
        for m in mudancas:
            rotulo = ROTULO_MUDANCA.get(m.get("campo"), m.get("campo"))
            alvo = "" if pagina_foco else f"[{titulo_da_pagina(docs, m['pagina'])}]({_rel(m['pagina'], origem)}) — "
            textos.append(f"{alvo}{rotulo}: **{m.get('valor')}**")
        linhas += ["", "    :material-swap-horizontal: " + " · ".join(textos)]
    outros = sorted(p for p in paginas_do_evento(e) if p != pagina_foco and (docs / p).exists())
    if outros and pagina_foco:
        linhas += ["", "    Envolvidos: " + ", ".join(f"[{titulo_da_pagina(docs, p)}]({_rel(p, origem)})" for p in outros)]
    linhas.append("")
    return linhas


def secao_da_pagina(docs: Path, eventos: list[dict], pagina: str) -> str:
    """Seção `## Linha do tempo` para a página de um NPC, cidade ou facção (vazia se não houver)."""
    lista = eventos_da_pagina(eventos, pagina)
    if not lista:
        return ""
    partes = ["## Linha do tempo", "", '<div class="linha-tempo" markdown>', ""]
    for e in lista:
        partes += _linha_evento(docs, e, pagina, pagina)
    partes += ["</div>", ""]
    return "\n".join(partes)


def pagina_geral(docs: Path, eventos: list[dict], origem: str) -> str:
    if not eventos:
        return "*Nenhum acontecimento registrado ainda.*"
    partes = ['<div class="linha-tempo" markdown>', ""]
    for e in ordenar(eventos):
        partes += _linha_evento(docs, e, origem, None)
        ja_citados = set((e.get("notas") or {}).keys())
        envolvidos = sorted(p for p in paginas_do_evento(e) if (docs / p).exists() and p not in ja_citados)
        if envolvidos:
            partes[-1:] = ["", "    Envolvidos: " + ", ".join(
                f"[{titulo_da_pagina(docs, p)}]({_rel(p, origem)})" for p in envolvidos), ""]
    partes.append("</div>")
    return "\n".join(partes)
