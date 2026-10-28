"""Hooks do MkDocs para a wiki de Gallancourt.

Registrado em `mkdocs.yml` (chave `hooks:`). Roda durante a geração do site e:

- monta o cabeçalho de cada página de NPC (retrato + dados rápidos) a partir do bloco `npc:`
  do front matter;
- transforma as seções `##` das páginas de NPC em abas;
- gera a tabela de NPCs em `personagens/index.md` (marcador `<!-- npcs:tabela -->`);
- gera a lista de sessões em `mestre/sessoes/index.md` (marcador `<!-- sessoes:lista -->`);
- gera a lista de lugares em `lugares/index.md` (marcador `<!-- lugares:lista -->`) e a de
  jogadores em `mestre/jogadores/index.md` (marcador `<!-- jogadores:lista -->`);
- gera as tabelas de magias: por nível em `magias/index.md` (marcador `<!-- magias:niveis -->`)
  e por classe em `magias/por-classe/*.md` (marcador `<!-- magias:classe -->`), lendo o bloco
  `magia:` do front matter de cada página em `magias/*.md`; e, na página de cada magia, acrescenta
  a seção "Dano e teste de resistência" quando o front matter tiver os campos `resistencia`/`dano`;
- gera as listas de dotes (`docs/dotes/index.md`, marcador `<!-- dotes:lista -->`) e perícias
  (`docs/pericias/index.md`, marcador `<!-- pericias:lista -->`);
- mostra a linha do tempo da campanha (`dados/linha-do-tempo.yml`, ver `linha_tempo.py`) em cada
  página envolvida e aplica as mudanças de estado (situação, localização…) aos NPCs;
- gera a página geral da linha do tempo (marcador `<!-- linha-do-tempo:geral -->`).

A tabela e a lista são lidas direto dos arquivos a cada geração: uma página nova de NPC ou de
sessão aparece sozinha, sem editar nenhuma lista à mão.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linha_tempo  # noqa: E402

# Linha do tempo carregada uma vez por geração do site (on_pre_build)
_EVENTOS: list[dict] = []

# Magias carregadas uma vez por geração do site (on_pre_build) — sem este cache, cada chamada a
# _tabela_magias_por_nivel/_tabela_magias_classe (1 + uma por classe) releria e reparsearia todos
# os arquivos de docs/magias/ do zero, multiplicando a leitura de disco por ~10.
_MAGIAS: list[dict] = []

RETRATO_PADRAO = "../assets/placeholders/personagem.svg"
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
    partes = _criar_entidade_div("npc", "../mestre/painel.md")
    partes += [
        '<div class="npc-ferramentas" markdown>',
        "",
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
    ]
    return "\n".join(partes)


# --------------------------------------------------------------------------
# Magias (2014): tabela por nível (magias/index.md) e por classe (magias/por-classe/*.md)
# --------------------------------------------------------------------------

NIVEIS_MAGIA = [
    (0, "Truque"), (1, "1º Nível"), (2, "2º Nível"), (3, "3º Nível"), (4, "4º Nível"),
    (5, "5º Nível"), (6, "6º Nível"), (7, "7º Nível"), (8, "8º Nível"), (9, "9º Nível"),
]

CLASSES_CONJURADORAS = {
    "artifice": "Artífice", "bardo": "Bardo", "bruxo": "Bruxo", "clerigo": "Clérigo",
    "druida": "Druida", "feiticeiro": "Feiticeiro", "mago": "Mago",
    "paladino": "Paladino", "patrulheiro": "Patrulheiro",
}

ESCOLAS_MAGIA = [
    "Abjuração", "Adivinhação", "Conjuração", "Encantamento", "Evocação",
    "Ilusão", "Necromancia", "Transmutação",
]
CATEGORIAS_MAGIA = ["Dano", "Suporte", "Utilidade", "Controle"]
TIPOS_DANO_MAGIA = [
    "Ácido", "Concussão", "Cortante", "Elétrico", "Fogo", "Frio", "Força",
    "Necrótico", "Perfurante", "Psíquico", "Radiante", "Trovejante", "Veneno", "Nenhum",
]
TIPOS_ALCANCE_MAGIA = ["Pessoal", "Toque", "Distância"]
# Mesmos valores exibidos na coluna "Área" da tabela (ver _rotulo_area) — "Nenhuma" no front
# matter aparece como "Alvo único" tanto na célula quanto nas opções do filtro.
AREAS_EFEITO_MAGIA = ["Alvo único", "Cone", "Cubo", "Cilindro", "Esfera", "Linha"]

# Colunas das tabelas de Dotes/Perícias: (rótulo, chave no bloco dote:/pericia:)
COLUNAS_DOTE = [("Pré-requisito", "pre_requisito"), ("Fonte", "fonte")]
COLUNAS_PERICIA = [("Atributo", "atributo"), ("Fonte", "fonte")]


def _ler_magias(docs: Path) -> list[dict]:
    magias = []
    for arquivo in sorted((docs / "magias").glob("*.md")):
        if arquivo.name == "index.md":
            continue
        meta, corpo = _front_matter(arquivo.read_text(encoding="utf-8"))
        dados = meta.get("magia")
        if not isinstance(dados, dict):
            continue
        nome = _titulo_h1(corpo, arquivo.stem)
        magias.append({**dados, "nome": nome, "arquivo": arquivo.name})
    return magias


def _select_magia(rotulo: str, coluna: str, modo: str, opcoes: list[str], todas: str) -> str:
    itens = "".join(f'<option value="{html.escape(o)}">{html.escape(o)}</option>' for o in opcoes)
    return (
        f'<select class="magia-filtro" data-coluna="{coluna}" data-modo="{modo}" '
        f'aria-label="Filtrar por {rotulo}"><option value="">{html.escape(todas)}</option>{itens}</select>'
    )


def _filtros_magia(incluir_classe: bool) -> list[str]:
    controles = ['<input type="search" class="magia-busca" placeholder="Filtrar por nome…" '
                 'aria-label="Filtrar magias">']
    if incluir_classe:
        controles.append(_select_magia(
            "classe", "Classes", "contem", sorted(CLASSES_CONJURADORAS.values()), "Todas as classes",
        ))
    controles += [
        _select_magia("escola", "Escola", "igual", ESCOLAS_MAGIA, "Todas as escolas"),
        _select_magia("categoria", "Categoria", "igual", CATEGORIAS_MAGIA, "Todas as categorias"),
        _select_magia("tipo de dano", "Tipo de Dano", "igual", TIPOS_DANO_MAGIA, "Qualquer dano"),
        _select_magia("tipo de alcance", "Tipo de Alcance", "igual", TIPOS_ALCANCE_MAGIA, "Qualquer alcance"),
        _select_magia("área", "Área", "igual", AREAS_EFEITO_MAGIA, "Qualquer área"),
        _select_magia("ritual", "Ritual", "igual", ["Sim", "Não"], "Ritual: todas"),
        _select_magia("concentração", "Concentração", "igual", ["Sim", "Não"], "Concentração: todas"),
        '<span class="magia-contagem" aria-live="polite"></span>',
    ]
    return ['<div class="magia-ferramentas" markdown>', "", *controles, "", "</div>"]


def _rotulo_area(area: str | None) -> str:
    """"Nenhuma" no front matter (sem área de efeito, alvo único) aparece como "Alvo único"."""
    return "Alvo único" if not area or area == "Nenhuma" else area


_RE_DURACAO_MAXIMA = re.compile(r"(\d+)\s+(rodadas?|minutos?|horas?|dias?)\b", re.I)


def _duracao_maxima(duracao: str | None) -> str:
    """Tempo máximo de uma duração (ex.: "Concentração, até 1 minuto" -> "1 minuto"), sem o
    "até"/"ou até" — vazio para durações sem número (Instantânea, Especial, Até ser dissipada)."""
    m = _RE_DURACAO_MAXIMA.search(duracao or "")
    return f"{m.group(1)} {m.group(2)}" if m else ""


def _icone_tempo(tempo: str | None) -> str:
    """Marcador visual do tipo de ação gasto para conjurar — só para Ação/Ação Bônus/Reação
    (os demais tempos, como "1 minuto" ou tempos de ritual, não ganham ícone)."""
    t = (tempo or "").strip().lower()
    if t.startswith("1 ação bônus"):
        return '<span class="magia-icone-tempo magia-icone-tempo--bonus" title="Ação Bônus"></span>'
    if t.startswith("1 reação"):
        return '<span class="magia-icone-tempo magia-icone-tempo--reacao" title="Reação"></span>'
    if t.startswith("1 ação"):
        return '<span class="magia-icone-tempo magia-icone-tempo--acao" title="Ação"></span>'
    return ""


def _linha_magia(m: dict, com_classes: bool, com_nivel: bool, prefixo: str = "") -> str:
    celulas = []
    if com_nivel:
        nivel = m.get("nivel", 0)
        celulas.append(_celula("Truque" if nivel == 0 else f"{nivel}º"))
    nome_en = m.get("nome_ingles")
    sufixo_nome = f'<br><span class="magia-nome-en">{html.escape(nome_en)}</span>' if nome_en else ""
    celulas.append(f"[{_celula(m['nome'])}]({prefixo}{m['arquivo']}){sufixo_nome}")
    celulas.append(_celula(m.get("escola")))
    celulas.append(f"{_icone_tempo(m.get('tempo'))}{_celula(m.get('tempo'))}")
    celulas.append(_celula(m.get("alcance")))
    celulas.append(_rotulo_area(m.get("area")))
    duracao_max = _duracao_maxima(m.get("duracao"))
    sufixo_duracao = f'<br><span class="magia-duracao-max">{duracao_max}</span>' if duracao_max else ""
    celulas.append(f"{_celula(m.get('duracao'))}{sufixo_duracao}")
    celulas.append(_celula(m.get("componentes")))
    if com_classes:
        celulas.append(_celula(", ".join(sorted(m.get("classes") or []))))
    celulas += [
        _celula("Sim" if m.get("ritual") else "Não"),
        _celula("Sim" if m.get("concentracao") else "Não"),
        _celula(m.get("categoria")), _celula(m.get("dano_tipo") or "Nenhum"),
        _celula(m.get("alcance_tipo")),
    ]
    return "| " + " | ".join(celulas) + " |"


def _tabela_magia_bloco(magias: list[dict], com_classes: bool, com_nivel: bool, prefixo: str = "") -> list[str]:
    cabecalhos = (["Nível"] if com_nivel else []) + ["Nome", "Escola", "Tempo", "Alcance", "Área", "Duração", "Componentes"]
    if com_classes:
        cabecalhos.append("Classes")
    cabecalhos += ["Ritual", "Concentração", "Categoria", "Tipo de Dano", "Tipo de Alcance"]
    cabecalho = "| " + " | ".join(cabecalhos) + " |"
    separador = "|" + "---|" * len(cabecalhos)
    chave = (lambda m: (m.get("nivel", 0), m["nome"].casefold())) if com_nivel else (lambda m: m["nome"].casefold())
    corpo = [_linha_magia(m, com_classes, com_nivel, prefixo) for m in sorted(magias, key=chave)]
    return ['<div class="magia-tabela" markdown>', "", cabecalho, separador, *corpo, "", "</div>"]


def _secao_dano_magia(m: dict) -> str:
    """Bloco "## Dano e teste de resistência" acrescentado ao final da página de uma magia,
    a partir dos campos opcionais `resistencia`/`resistencia_efeito`/`dano` do front matter
    (ver hooks/gallancourt.py, docstring do módulo, e o plano que introduziu estes campos)."""
    partes = ["## Dano e teste de resistência", ""]
    resistencia = m.get("resistencia")
    if resistencia:
        efeito = m.get("resistencia_efeito")
        linha = f"- **Teste de resistência:** {resistencia}"
        if efeito:
            linha += f" — {efeito} em caso de sucesso"
        partes += [linha, ""]
    dano = m.get("dano")
    if dano:
        rotulo_coluna = "Nível de personagem" if m.get("nivel", 0) == 0 else "Nível do espaço"
        partes += [f"| {rotulo_coluna} | Dano |", "|---|---|"]
        partes += [f"| {rotulo} | {dado} |" for rotulo, dado in dano]
        partes.append("")
    return "\n".join(partes)


def _tabela_magias_por_nivel(docs: Path, config) -> str:
    por_nivel: dict[int, list[dict]] = {n: [] for n, _ in NIVEIS_MAGIA}
    for m in _MAGIAS:
        por_nivel.setdefault(m.get("nivel", 0), []).append(m)
    blocos = _filtros_magia(incluir_classe=True)
    blocos.append("")
    blocos.append('=== "Todas"')
    blocos.append("")
    if _MAGIAS:
        tabela = _tabela_magia_bloco(_MAGIAS, com_classes=True, com_nivel=True)
    else:
        tabela = ["*Nenhuma magia cadastrada ainda.*"]
    blocos += ["    " + linha if linha else "" for linha in tabela]
    blocos.append("")
    for nivel, rotulo in NIVEIS_MAGIA:
        blocos.append(f'=== "{rotulo}"')
        blocos.append("")
        magias_nivel = por_nivel.get(nivel, [])
        if magias_nivel:
            tabela = _tabela_magia_bloco(magias_nivel, com_classes=True, com_nivel=False)
        else:
            tabela = ["*Nenhuma magia cadastrada neste nível ainda.*"]
        blocos += ["    " + linha if linha else "" for linha in tabela]
        blocos.append("")
    return "\n".join(blocos)


def _tabela_magias_classe(docs: Path, classe: str) -> str:
    magias = [m for m in _MAGIAS if classe in (m.get("classes") or [])]
    blocos = _filtros_magia(incluir_classe=False)
    blocos.append("")
    if magias:
        blocos += _tabela_magia_bloco(magias, com_classes=False, com_nivel=True, prefixo="../")
    else:
        blocos.append("*Nenhuma magia cadastrada para esta classe ainda.*")
    return "\n".join(blocos)


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

    partes = [
        '<div class="criar-sessao" markdown>',
        "",
        "*(o formulário aparece aqui quando a página carrega — precisa do "
        "[Painel do Mestre](../painel.md) rodando no seu computador)*",
        "",
        "</div>",
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
# Lista de lugares e de jogadores — mesmo padrão simples da lista de sessões:
# um botão "Adicionar" e um .bar-list lido direto da pasta a cada geração.
# --------------------------------------------------------------------------

# Colunas das tabelas de Lugares/Jogadores: (rótulo, chave no bloco lugar:/jogador:)
COLUNAS_LUGAR = [("Situado", "situado"), ("Região", "regiao"), ("Reino", "reino")]
COLUNAS_JOGADOR = [
    ("Jogador", "jogador"), ("Classe", "classe"), ("Nível", "nivel"), ("CA", "ca"), ("PV", "pv"),
]

_RE_STATBLOCK_DADOS = re.compile(r"<!-- dados:statblock (.*?) -->", re.DOTALL)


def _resumo_statblock(texto: str) -> dict:
    """Primeira ficha de combate (ver admin/wiki_data.py) anexada à página, só para ler alguns
    valores de resumo (classe/nível/CA/PV) — não precisa renderizar nada."""
    m = _RE_STATBLOCK_DADOS.search(texto)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


def _criar_entidade_div(tipo: str, caminho_painel_doc: str) -> list[str]:
    """Div-mount do formulário embutido "Adicionar NPC/Lugar/Jogador" (ver
    docs/javascripts/gallancourt.js::montarFormularioEntidade e painel-fetch.js). Site e Painel
    são a mesma origem/porta, então o formulário fala com a API por caminho relativo (ver
    painel-fetch.js) — não precisa saber nenhum endereço."""
    return [
        f'<div class="criar-entidade" data-tipo="{tipo}" markdown>',
        "",
        f"*(o formulário aparece aqui quando a página carrega — precisa do "
        f"[Painel do Mestre]({caminho_painel_doc}) rodando no seu computador)*",
        "",
        "</div>",
        "",
    ]


def _ler_lugares_da_pasta(docs: Path, subpasta: str, prefixo_link: str) -> list[tuple[str, str, dict]]:
    linhas = []
    pasta = docs / subpasta
    if not pasta.is_dir():
        return linhas
    for arquivo in sorted(pasta.glob("*.md")):
        if arquivo.stem == "index":
            continue
        meta, corpo = _front_matter(arquivo.read_text(encoding="utf-8"))
        lugar = meta.get("lugar")
        if not isinstance(lugar, dict):
            continue
        linhas.append((_titulo_h1(corpo, arquivo.stem), f"{prefixo_link}{arquivo.name}", lugar))
    return linhas


def _lista_lugares(docs: Path, config) -> str:
    # Mesma tabela recebe tanto lugares cadastrados pelo Painel (docs/lugares/) quanto cidades
    # (docs/cidades/) — ambas as pastas usam o mesmo bloco `lugar:` no front matter.
    linhas = _ler_lugares_da_pasta(docs, "lugares", "") + _ler_lugares_da_pasta(docs, "cidades", "../cidades/")
    linhas.sort(key=lambda l: l[0].casefold())

    partes = _criar_entidade_div("lugar", "../mestre/painel.md")
    if not linhas:
        return "\n".join(partes + ["*Nenhum lugar criado ainda.*"])

    cabecalho = "| Nome | " + " | ".join(r for r, _ in COLUNAS_LUGAR) + " | Descrição |"
    separador = "|" + "---|" * (len(COLUNAS_LUGAR) + 2)
    corpo_tabela = [
        f"| [{_celula(nome)}]({arq}) | "
        + " | ".join(_celula(lugar.get(chave)) for _, chave in COLUNAS_LUGAR)
        + f" | {_celula(lugar.get('resumo'))} |"
        for nome, arq, lugar in linhas
    ]
    partes += [
        '<div class="lugar-ferramentas" markdown>',
        "",
        '<input type="search" class="lugar-busca" placeholder="Filtrar por nome, região, reino…" '
        'aria-label="Filtrar lugares">',
        '<span class="lugar-contagem" aria-live="polite"></span>',
        "",
        "</div>",
        "",
        '<div class="lugar-tabela" markdown>',
        "",
        cabecalho,
        separador,
        *corpo_tabela,
        "",
        "</div>",
    ]
    return "\n".join(partes)


def _ler_entidades_da_pasta(docs: Path, subpasta: str, campo: str) -> list[tuple[str, str, dict]]:
    """Mesmo molde de _ler_lugares_da_pasta, para listas simples sem formulário do Painel
    (Dotes/Perícias — conteúdo fixo escrito à mão, não cadastrado em tempo de jogo)."""
    linhas = []
    pasta = docs / subpasta
    if not pasta.is_dir():
        return linhas
    for arquivo in sorted(pasta.glob("*.md")):
        if arquivo.stem == "index":
            continue
        meta, corpo = _front_matter(arquivo.read_text(encoding="utf-8"))
        dados = meta.get(campo)
        if not isinstance(dados, dict):
            continue
        linhas.append((_titulo_h1(corpo, arquivo.stem), arquivo.name, dados))
    linhas.sort(key=lambda l: l[0].casefold())
    return linhas


def _tabela_entidade_simples(
    linhas: list[tuple[str, str, dict]], colunas: list[tuple[str, str]],
    classe_css: str, placeholder_busca: str, vazio: str,
) -> str:
    if not linhas:
        return f"*{vazio}*"
    cabecalho = "| Nome | " + " | ".join(r for r, _ in colunas) + " |"
    separador = "|" + "---|" * (len(colunas) + 1)
    corpo_tabela = [
        f"| [{_celula(nome)}]({arq}) | " + " | ".join(_celula(dados.get(chave)) for _, chave in colunas) + " |"
        for nome, arq, dados in linhas
    ]
    partes = [
        f'<div class="{classe_css}-ferramentas" markdown>',
        "",
        f'<input type="search" class="{classe_css}-busca" placeholder="{placeholder_busca}" '
        f'aria-label="Filtrar">',
        f'<span class="{classe_css}-contagem" aria-live="polite"></span>',
        "",
        "</div>",
        "",
        f'<div class="{classe_css}-tabela" markdown>',
        "",
        cabecalho,
        separador,
        *corpo_tabela,
        "",
        "</div>",
    ]
    return "\n".join(partes)


def _lista_dotes(docs: Path, config) -> str:
    linhas = _ler_entidades_da_pasta(docs, "dotes", "dote")
    return _tabela_entidade_simples(
        linhas, COLUNAS_DOTE, "dote", "Filtrar por nome…", "Nenhum dote cadastrado ainda.",
    )


def _lista_pericias(docs: Path, config) -> str:
    linhas = _ler_entidades_da_pasta(docs, "pericias", "pericia")
    return _tabela_entidade_simples(
        linhas, COLUNAS_PERICIA, "pericia", "Filtrar por nome…", "Nenhuma perícia cadastrada ainda.",
    )


def _lista_jogadores(docs: Path, config) -> str:
    linhas = []
    pasta = docs / "mestre" / "jogadores"
    if pasta.is_dir():
        for arquivo in sorted(pasta.glob("*.md")):
            if arquivo.stem == "index":
                continue
            texto = arquivo.read_text(encoding="utf-8")
            meta, corpo = _front_matter(texto)
            jogador = meta.get("jogador")
            if not isinstance(jogador, dict):
                continue
            ficha = _resumo_statblock(texto)
            jogador = dict(jogador)
            jogador["classe"] = ficha.get("classe") or jogador.get("raca_classe") or "—"
            jogador["nivel"] = ficha.get("nivel") or "—"
            jogador["ca"] = ficha.get("ca") or "—"
            pv, pv_atual = ficha.get("pv"), ficha.get("pv_atual")
            jogador["pv"] = (f"{pv_atual}/{pv}" if pv_atual else pv) or "—"
            linhas.append((_titulo_h1(corpo, arquivo.stem), arquivo.name, jogador))
    linhas.sort(key=lambda l: l[0].casefold())

    partes = _criar_entidade_div("jogador", "../painel.md")
    if not linhas:
        return "\n".join(partes + ["*Nenhum jogador cadastrado ainda.*"])

    cabecalho = "| Nome | " + " | ".join(r for r, _ in COLUNAS_JOGADOR) + " | Resumo |"
    separador = "|" + "---|" * (len(COLUNAS_JOGADOR) + 2)
    corpo_tabela = [
        f"| [{_celula(nome)}]({arq}) | "
        + " | ".join(_celula(jogador.get(chave)) for _, chave in COLUNAS_JOGADOR)
        + f" | {_celula(jogador.get('resumo'))} |"
        for nome, arq, jogador in linhas
    ]
    partes += [
        '<div class="jogador-ferramentas" markdown>',
        "",
        '<input type="search" class="jogador-busca" placeholder="Filtrar por nome ou jogador…" '
        'aria-label="Filtrar jogadores">',
        '<span class="jogador-contagem" aria-live="polite"></span>',
        "",
        "</div>",
        "",
        '<div class="jogador-tabela" markdown>',
        "",
        cabecalho,
        separador,
        *corpo_tabela,
        "",
        "</div>",
    ]
    return "\n".join(partes)


# --------------------------------------------------------------------------
# Página de NPC: cabeçalho e abas
# --------------------------------------------------------------------------

def _retrato_padrao(pagina: str) -> str:
    """RETRATO_PADRAO é relativo a docs/personagens/ — para páginas mais profundas (ex.:
    personagens/genericos/<slug>.md) precisa de um "../" extra por nível."""
    profundidade_extra = pagina.count("/") - 1
    return ("../" * max(profundidade_extra, 0)) + RETRATO_PADRAO


def _cabecalho_npc(npc: dict, pagina: str, docs: Path) -> str:
    retrato = npc.get("retrato") or _retrato_padrao(pagina)
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


def _cabecalho_jogador(jogador: dict) -> str:
    """Card de identidade no topo da página de um jogador — mesmo padrão visual de
    _cabecalho_npc (reaproveita .npc-cabecalho/.npc-dados), só sem retrato."""
    resumo = jogador.get("resumo")
    linhas = ["| | |", "|---|---|"]
    quem_joga = (jogador.get("jogador") or "").strip()
    if quem_joga:
        linhas.append(f"| **Jogador** | {_celula(quem_joga)} |")
    raca_classe = (jogador.get("raca_classe") or "").strip()
    if raca_classe:
        linhas.append(f"| **Raça e classe** | {_celula(raca_classe)} |")
    return "\n".join([
        '<div class="npc-cabecalho" markdown>',
        "",
        '<div class="npc-dados" markdown>',
        "",
        *([f"*{resumo}*", ""] if resumo else []),
        *(linhas if len(linhas) > 2 else []),
        "",
        "</div>",
        "",
        "</div>",
        "",
        "<!-- npc-corpo -->",
        "",
    ])


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


_RE_STATBLOCK = re.compile(
    r"<!-- inicio:statblock:[a-z0-9-]+ -->.*?<!-- fim:statblock:[a-z0-9-]+ -->", re.DOTALL,
)


def _extrair_statblocks(texto: str) -> tuple[str, list[str]]:
    """Tira do texto qualquer ficha de combate (cartão `.stat-block`, ver
    admin/wiki_data.py::salvar_statblock) anexada à página, para reinserir dentro da aba
    "Ficha" em vez de deixá-la solta onde o Painel a inseriu (normalmente no fim do arquivo)."""
    fichas = _RE_STATBLOCK.findall(texto)
    return _RE_STATBLOCK.sub("", texto), fichas


def _paginar_npc(conteudo: str) -> str:
    if "<!-- npc-corpo -->" not in conteudo:
        return conteudo
    cabeca, corpo = conteudo.split("<!-- npc-corpo -->", 1)
    corpo, fichas_combate = _extrair_statblocks(corpo)
    corpo, em_aberto = _separar_em_aberto(corpo)

    partes = re.split(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', corpo, flags=re.S)
    abas = []
    if partes[0].strip():
        abas.append(("Visão geral", partes[0]))
    for i in range(1, len(partes), 3):
        ancora, titulo_html, secao = partes[i], partes[i + 1], partes[i + 2]
        titulo = html.unescape(re.sub(r"<[^>]+>", "", titulo_html)).replace("¶", "").strip()
        abas.append((titulo, f'<span id="{ancora}" class="npc-ancora"></span>{secao}'))
    indice_ficha = next((i for i, (titulo, _) in enumerate(abas) if titulo == "Ficha"), None)
    if indice_ficha is not None:
        if fichas_combate:
            titulo, conteudo_ficha = abas[indice_ficha]
            abas[indice_ficha] = (titulo, conteudo_ficha + "".join(fichas_combate))
    else:
        # Sem ficha de combate anexada ainda, reserva o espaço com um aviso — o Painel do
        # Mestre preenche isso pela aba "Ficha de combate" (atributos, perícias, CA, PV,
        # equipamento), escolhendo esta página; o cartão então aparece aqui automaticamente.
        conteudo_ficha = "".join(fichas_combate) if fichas_combate else (
            "<p><em>Ficha ainda não preenchida — crie uma pela aba \"Ficha de combate\" do "
            "Painel do Mestre, escolhendo esta página.</em></p>"
        )
        abas.append(("Ficha", conteudo_ficha))
    if em_aberto:
        abas.append(("Em aberto", "".join(em_aberto)))
    if not abas:
        return cabeca
    # Ordem: Visão geral, Linha do tempo, demais seções, Ficha, Em aberto.
    prioridade = {"Visão geral": 0, "Linha do tempo": 1, "Ficha": 90, "Em aberto": 99}
    abas = [a for _, a in sorted(enumerate(abas), key=lambda x: (prioridade.get(x[1][0], 50), x[0]))]
    return cabeca + _abas(abas)


# --------------------------------------------------------------------------
# Eventos do MkDocs
# --------------------------------------------------------------------------

def on_pre_build(config):
    global _EVENTOS, _MAGIAS
    _EVENTOS = linha_tempo.carregar(Path(config["config_file_path"]).parent)
    _MAGIAS = _ler_magias(Path(config["docs_dir"]))


def _depois_do_h1(markdown: str, bloco: str) -> str:
    return re.sub(r"^(# .+\n)", lambda m: m.group(1) + "\n" + bloco + "\n", markdown, count=1, flags=re.M)


# Páginas de Classes/Raças/Antecedentes empilham tabelas densas (características por nível,
# traços, abas 2014/2024) — envolvê-las numa div própria deixa a fonte das tabelas menor só ali
# (ver `.pagina-regra table` em extra.css), sem afetar o resto do site.
def _envolver_pagina_regra(markdown: str) -> str:
    m = re.match(r"^(# .+\n)", markdown, re.M)
    if not m:
        return markdown
    cabeca, resto = markdown[: m.end()], markdown[m.end() :]
    return f'{cabeca}\n<div class="pagina-regra" markdown>\n\n{resto.rstrip()}\n\n</div>\n'


def on_page_markdown(markdown: str, page, config, files):
    docs = Path(config["docs_dir"])
    src = page.file.src_uri
    if "<!-- linha-do-tempo:geral -->" in markdown:
        markdown = markdown.replace("<!-- linha-do-tempo:geral -->", linha_tempo.pagina_geral(docs, _EVENTOS, src))
    if src == "personagens/index.md" and "<!-- npcs:tabela -->" in markdown:
        markdown = markdown.replace("<!-- npcs:tabela -->", _tabela_npcs(docs, config))
    if src == "mestre/sessoes/index.md" and "<!-- sessoes:lista -->" in markdown:
        markdown = markdown.replace("<!-- sessoes:lista -->", _lista_sessoes(docs, config))
    if src == "lugares/index.md" and "<!-- lugares:lista -->" in markdown:
        markdown = markdown.replace("<!-- lugares:lista -->", _lista_lugares(docs, config))
    if src == "mestre/jogadores/index.md" and "<!-- jogadores:lista -->" in markdown:
        markdown = markdown.replace("<!-- jogadores:lista -->", _lista_jogadores(docs, config))
    if src == "magias/index.md" and "<!-- magias:niveis -->" in markdown:
        markdown = markdown.replace("<!-- magias:niveis -->", _tabela_magias_por_nivel(docs, config))
    if src.startswith("magias/por-classe/") and "<!-- magias:classe -->" in markdown:
        slug = Path(src).stem
        classe = CLASSES_CONJURADORAS.get(slug, slug.capitalize())
        markdown = markdown.replace("<!-- magias:classe -->", _tabela_magias_classe(docs, classe))
    if src.startswith("magias/") and not src.endswith("index.md") and "/por-classe/" not in src:
        dados_magia = page.meta.get("magia")
        if isinstance(dados_magia, dict) and (dados_magia.get("resistencia") or dados_magia.get("dano")):
            markdown = markdown.rstrip("\n") + "\n\n" + _secao_dano_magia(dados_magia)
    if src == "dotes/index.md" and "<!-- dotes:lista -->" in markdown:
        markdown = markdown.replace("<!-- dotes:lista -->", _lista_dotes(docs, config))
    if src == "pericias/index.md" and "<!-- pericias:lista -->" in markdown:
        markdown = markdown.replace("<!-- pericias:lista -->", _lista_pericias(docs, config))
    if src.startswith(("classes/", "racas/", "antecedentes/")) and not src.endswith("index.md"):
        markdown = _envolver_pagina_regra(markdown)
    if src.startswith("mestre/sessoes/sessao-") and "<!-- participantes:botao -->" in markdown:
        botao = (
            f"[:material-account-group: Participantes desta sessão]"
            f"(/sessoes/participantes?pagina={src}){{ .md-button .botao-painel target=_blank "
            f'title="{DICA_PAINEL}" }}'
        )
        markdown = markdown.replace("<!-- participantes:botao -->", botao)
    npc = page.meta.get("npc")
    jogador = page.meta.get("jogador")
    secao_tempo = linha_tempo.secao_da_pagina(docs, _EVENTOS, src)
    if isinstance(npc, dict):
        markdown = _depois_do_h1(markdown, _cabecalho_npc(npc, src, docs))
        if secao_tempo:
            markdown = markdown.rstrip("\n") + "\n\n" + secao_tempo
    elif isinstance(jogador, dict):
        markdown = _depois_do_h1(markdown, _cabecalho_jogador(jogador))
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
    if isinstance(page.meta.get("npc"), dict) or isinstance(page.meta.get("jogador"), dict):
        return _paginar_npc(conteudo)
    return conteudo
