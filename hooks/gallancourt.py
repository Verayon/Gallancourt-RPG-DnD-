"""Hooks do MkDocs para a wiki de Gallancourt.

Registrado em `mkdocs.yml` (chave `hooks:`). Roda durante a geração do site e:

- monta o cabeçalho de cada página de NPC (retrato + dados rápidos) a partir do bloco `npc:`
  do front matter;
- transforma as seções `##` das páginas de NPC em abas;
- gera a tabela de NPCs em `personagens/index.md` (marcador `<!-- npcs:tabela -->`);
- gera a lista de sessões em `mestre/sessoes/index.md` (marcador `<!-- sessoes:lista -->`);
- mostra a linha do tempo da campanha (`dados/linha-do-tempo.yml`, ver `linha_tempo.py`) em cada
  página envolvida e aplica as mudanças de estado (situação, localização…) aos NPCs;
- gera a página geral da linha do tempo (marcador `<!-- linha-do-tempo:geral -->`).

A tabela e a lista são lidas direto dos arquivos a cada geração: uma página nova de NPC ou de
sessão aparece sozinha, sem editar nenhuma lista à mão.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linha_tempo  # noqa: E402

# Linha do tempo carregada uma vez por geração do site (on_pre_build)
_EVENTOS: list[dict] = []

RETRATO_PADRAO = "../assets/placeholders/personagem.svg"
PAINEL_PADRAO = "http://127.0.0.1:5001"
DICA_PAINEL = "Abre o Painel do Mestre — ele precisa estar rodando no seu computador"

# Colunas da tabela de NPCs: (rótulo, chave no bloco npc:)
COLUNAS_NPC = [
    ("Título", "titulo"), ("Raça", "raca"), ("Cidade", "cidade"),
    ("Afiliação", "afiliacao"), ("Situação", "situacao"),
]


def _npc_atual(npc: dict, pagina: str) -> dict:
    """Dados do NPC com as mudanças da linha do tempo aplicadas."""
    atual = dict(npc)
    for campo, (valor, _) in linha_tempo.estado_atual(_EVENTOS, pagina).items():
        atual[campo] = valor
    atual.setdefault("situacao", "—")
    return atual


# --------------------------------------------------------------------------
# Leitura de arquivos
# --------------------------------------------------------------------------

def _front_matter(texto: str) -> tuple[dict, str]:
    m = re.match(r"---\n(.*?)\n---\n?(.*)", texto, re.S)
    if not m:
        return {}, texto
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def _titulo_h1(corpo: str, padrao: str) -> str:
    m = re.search(r"^# (.+)$", corpo, re.M)
    return m.group(1).strip() if m else padrao


def _celula(valor) -> str:
    """Texto seguro para uma célula de tabela Markdown."""
    return str(valor if valor not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def _painel(config) -> str:
    return (config.get("extra") or {}).get("painel_url", PAINEL_PADRAO).rstrip("/")


# --------------------------------------------------------------------------
# Tabela de NPCs
# --------------------------------------------------------------------------

def _tabela_npcs(docs: Path, config) -> str:
    linhas = []
    for arquivo in sorted((docs / "personagens").glob("*.md")):
        if arquivo.name == "index.md":
            continue
        meta, corpo = _front_matter(arquivo.read_text(encoding="utf-8"))
        npc = meta.get("npc")
        if not isinstance(npc, dict):
            continue
        nome = _titulo_h1(corpo, arquivo.stem)
        retrato = npc.get("retrato") or RETRATO_PADRAO
        npc = _npc_atual(npc, f"personagens/{arquivo.name}")
        linhas.append((nome, arquivo.name, retrato, npc))
    linhas.sort(key=lambda l: l[0].casefold())

    cabecalho = "| Retrato | Nome | " + " | ".join(r for r, _ in COLUNAS_NPC) + " | Resumo |"
    separador = "|" + "---|" * (len(COLUNAS_NPC) + 3)
    corpo = [
        f"| ![{_celula(nome)}]({retrato}){{ .npc-mini loading=lazy }} | [{_celula(nome)}]({arq}) | "
        + " | ".join(_celula(npc.get(chave)) for _, chave in COLUNAS_NPC)
        + f" | {_celula(npc.get('resumo'))} |"
        for nome, arq, retrato, npc in linhas
    ]
    painel = _painel(config)
    return "\n".join([
        '<div class="npc-ferramentas" markdown>',
        "",
        f'[:material-account-plus: Adicionar NPC]({painel}/npc/novo){{ .md-button .md-button--primary '
        f'.botao-painel target=_blank title="{DICA_PAINEL}" }}',
        '<input type="search" class="npc-busca" placeholder="Filtrar por nome, cidade, afiliação…" '
        'aria-label="Filtrar NPCs">',
        '<span class="npc-contagem" aria-live="polite"></span>',
        "",
        "</div>",
        "",
        '<div class="npc-tabela" markdown>',
        "",
        cabecalho,
        separador,
        *corpo,
        "",
        "</div>",
    ])


# --------------------------------------------------------------------------
# Lista de sessões
# --------------------------------------------------------------------------

def _ficha_markdown(corpo: str) -> dict[str, str]:
    m = re.search(r'<div class="ficha" markdown>(.*?)</div>', corpo, re.S)
    if not m:
        return {}
    # A ficha pode estar indentada (ex.: dentro da aba "Resumo" de uma sessão) ou não (ex.: NPC,
    # cidade) — aceita espaços à esquerda de cada linha "| **Rótulo** | valor |".
    return dict(re.findall(r"^[ \t]*\| \*\*(.+?)\*\* \| (.*?) \|$", m.group(1), re.M))


def _lista_sessoes(docs: Path, config) -> str:
    sessoes = []
    for arquivo in (docs / "mestre" / "sessoes").glob("sessao-*.md"):
        meta, corpo = _front_matter(arquivo.read_text(encoding="utf-8"))
        info = meta.get("sessao") or {}
        numero = info.get("numero")
        if numero is None:
            m = re.match(r"sessao-(\d+)", arquivo.stem)
            numero = int(m.group(1)) if m else 0
        ficha = _ficha_markdown(corpo)
        sessoes.append((int(numero), _titulo_h1(corpo, arquivo.stem), arquivo.name, ficha))
    sessoes.sort()

    painel = _painel(config)
    partes = [
        f"[:material-plus: Nova sessão]({painel}/sessoes/nova){{ .md-button .md-button--primary "
        f'.botao-painel target=_blank title="{DICA_PAINEL}" }}',
        "",
    ]
    if not sessoes:
        return "\n".join(partes + ["*Nenhuma sessão criada ainda.*"])
    partes += ['<div class="sessao-lista" markdown>', ""]
    for _, titulo, arq, ficha in sessoes:
        data = ficha.get("Data", "—")
        if data == "—":
            data = ""
        resumo_breve = ficha.get("Resumo breve", "—")
        if resumo_breve == "—":
            resumo_breve = " · ".join(
                f"{rotulo}: {ficha[rotulo]}"
                for rotulo in ("Local", "Jogadores", "Nível sugerido")
                if ficha.get(rotulo, "—") != "—"
            )
        partes += [
            '<div class="sessao-card" markdown>', "",
            '<div class="sessao-card__cabecalho" markdown>', "",
            f"**[{titulo}]({arq})**", "",
        ]
        if data:
            partes += [f"{data}", ""]
        partes += ["</div>", ""]
        if resumo_breve:
            partes += ["---", "", f"{resumo_breve}", ""]
        partes += ["</div>", ""]
    partes += ["</div>"]
    return "\n".join(partes)


# --------------------------------------------------------------------------
# Página de NPC: cabeçalho e abas
# --------------------------------------------------------------------------

def _cabecalho_npc(npc: dict, pagina: str, docs: Path) -> str:
    retrato = npc.get("retrato") or RETRATO_PADRAO
    ficha = npc.get("ficha") or {}
    atuais = []
    for campo, (valor, evento) in linha_tempo.estado_atual(_EVENTOS, pagina).items():
        quando = evento.get("data") or ""
        sessao = linha_tempo.link_sessao(docs, evento.get("sessao"), pagina)
        origem = ", ".join(x for x in (quando, sessao) if x)
        rotulo = linha_tempo.ROTULO_MUDANCA.get(campo, campo)
        atuais.append(f"| **{rotulo} atual** | **{_celula(valor)}**" + (f" *({origem})*" if origem else "") + " |")
    linhas = ["| | |", "|---|---|"] + atuais + [
        f"| **{rotulo}** | {_celula(valor)} |" for rotulo, valor in ficha.items()
    ]
    resumo = npc.get("resumo")
    return "\n".join([
        '<div class="npc-cabecalho" markdown>',
        "",
        '<div class="npc-retrato" markdown>',
        "",
        f"![Retrato]({retrato}){{ loading=lazy }}",
        "",
        "</div>",
        "",
        '<div class="npc-dados" markdown>',
        "",
        *( [f"*{resumo}*", ""] if resumo else [] ),
        *linhas,
        "",
        "</div>",
        "",
        "</div>",
        "",
        "<!-- npc-corpo -->",
        "",
    ])


def _extrair_div(html_texto: str, inicio: int) -> int:
    """Devolve o índice logo após o </div> que fecha a <div> aberta em `inicio`."""
    profundidade = 0
    for m in re.finditer(r"<div\b|</div>", html_texto[inicio:]):
        profundidade += 1 if m.group(0) == "<div" else -1
        if profundidade == 0:
            return inicio + m.end()
    return len(html_texto)


def _separar_em_aberto(corpo: str) -> tuple[str, list[str]]:
    blocos = []
    padrao = re.compile(r'<div class="admonition question">\s*<p class="admonition-title">Em aberto</p>')
    while (m := padrao.search(corpo)):
        fim = _extrair_div(corpo, m.start())
        blocos.append(corpo[m.start():fim])
        corpo = corpo[:m.start()] + corpo[fim:]
    return corpo, blocos


def _abas(abas: list[tuple[str, str]]) -> str:
    marcado = 'checked="checked" '
    entradas = "".join(
        f'<input {marcado if i == 0 else ""}id="npc-aba-{i + 1}" name="npc-abas" type="radio" />'
        for i in range(len(abas))
    )
    rotulos = "".join(f'<label for="npc-aba-{i + 1}">{html.escape(r)}</label>' for i, (r, _) in enumerate(abas))
    blocos = "".join(f'<div class="tabbed-block">\n{c}\n</div>' for _, c in abas)
    return (
        f'<div class="tabbed-set tabbed-alternate npc-abas" data-tabs="1:{len(abas)}">'
        f'{entradas}<div class="tabbed-labels">{rotulos}</div>'
        f'<div class="tabbed-content">{blocos}</div></div>'
    )


def _paginar_npc(conteudo: str) -> str:
    if "<!-- npc-corpo -->" not in conteudo:
        return conteudo
    cabeca, corpo = conteudo.split("<!-- npc-corpo -->", 1)
    corpo, em_aberto = _separar_em_aberto(corpo)

    partes = re.split(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', corpo, flags=re.S)
    abas = []
    if partes[0].strip():
        abas.append(("Visão geral", partes[0]))
    for i in range(1, len(partes), 3):
        ancora, titulo_html, secao = partes[i], partes[i + 1], partes[i + 2]
        titulo = html.unescape(re.sub(r"<[^>]+>", "", titulo_html)).replace("¶", "").strip()
        abas.append((titulo, f'<span id="{ancora}" class="npc-ancora"></span>{secao}'))
    if em_aberto:
        abas.append(("Em aberto", "".join(em_aberto)))
    if not abas:
        return cabeca
    # Ordem: Visão geral, Linha do tempo, demais seções, Em aberto.
    prioridade = {"Visão geral": 0, "Linha do tempo": 1, "Em aberto": 99}
    abas = [a for _, a in sorted(enumerate(abas), key=lambda x: (prioridade.get(x[1][0], 50), x[0]))]
    return cabeca + _abas(abas)


# --------------------------------------------------------------------------
# Eventos do MkDocs
# --------------------------------------------------------------------------

def on_pre_build(config):
    global _EVENTOS
    _EVENTOS = linha_tempo.carregar(Path(config["config_file_path"]).parent)


def _depois_do_h1(markdown: str, bloco: str) -> str:
    return re.sub(r"^(# .+\n)", lambda m: m.group(1) + "\n" + bloco + "\n", markdown, count=1, flags=re.M)


def on_page_markdown(markdown: str, page, config, files):
    docs = Path(config["docs_dir"])
    src = page.file.src_uri
    if "<!-- linha-do-tempo:geral -->" in markdown:
        markdown = markdown.replace("<!-- linha-do-tempo:geral -->", linha_tempo.pagina_geral(docs, _EVENTOS, src))
    if src == "personagens/index.md" and "<!-- npcs:tabela -->" in markdown:
        markdown = markdown.replace("<!-- npcs:tabela -->", _tabela_npcs(docs, config))
    if src == "mestre/sessoes/index.md" and "<!-- sessoes:lista -->" in markdown:
        markdown = markdown.replace("<!-- sessoes:lista -->", _lista_sessoes(docs, config))
    npc = page.meta.get("npc")
    secao_tempo = linha_tempo.secao_da_pagina(docs, _EVENTOS, src)
    if isinstance(npc, dict):
        markdown = _depois_do_h1(markdown, _cabecalho_npc(npc, src, docs))
        if secao_tempo:
            markdown = markdown.rstrip("\n") + "\n\n" + secao_tempo
    elif secao_tempo:
        estado = linha_tempo.estado_atual(_EVENTOS, src)
        if "situacao" in estado:
            valor, evento = estado["situacao"]
            sessao = linha_tempo.link_sessao(docs, evento.get("sessao"), src)
            origem = ", ".join(x for x in (evento.get("data") or "", sessao) if x)
            aviso = ['!!! info "Situação atual"', f"    **{valor}**" + (f" — desde {origem}." if origem else "")]
            markdown = _depois_do_h1(markdown, "\n".join(aviso) + "\n")
        markdown = markdown.rstrip("\n") + "\n\n" + secao_tempo
    return markdown


def on_page_content(conteudo: str, page, config, files):
    if isinstance(page.meta.get("npc"), dict):
        return _paginar_npc(conteudo)
    return conteudo
