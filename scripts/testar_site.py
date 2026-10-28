#!/usr/bin/env python3
"""Teste fixo do site de Gallancourt — valida sempre as mesmas coisas, na mesma ordem.

Uso (a partir da raiz do projeto):

    python scripts/testar_site.py                  # tudo
    python scripts/testar_site.py --sem-navegador  # pula os testes que abrem um navegador
    python scripts/testar_site.py --sem-painel     # pula os testes do Painel do Mestre
    python scripts/testar_site.py --manter         # não apaga a cópia de teste (para investigar)

O teste NUNCA altera o projeto: tudo roda numa cópia temporária. Termina com código 0 se tudo
passou e 1 se algo falhou (é o que o botão do GitHub usa para mostrar ✅ ou ❌).

Grupos de verificação:
  1. Cálculos     — ordem da linha do tempo
  2. Menu         — as 6 categorias de topo e as subcategorias da Wiki, na ordem combinada
  3. Relações     — o gerador de relações não muda nada se rodado de novo
  4. Build        — `mkdocs build --strict` sem erros nem links quebrados
  5. Páginas      — tabela de NPCs, caixa e abas dos NPCs, sessões, linha do tempo, botões
  6. Navegador    — filtro, ordenação e abas funcionando de verdade (precisa do Playwright)
  7. Painel       — criar NPC, criar sessão, registrar acontecimento, e o efeito no site

Para os testes de navegador: `pip install playwright` e `playwright install chromium`. Sem isso,
o grupo 6 aparece como PULADO (não conta como falha).
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IGNORAR_NA_COPIA = shutil.ignore_patterns("site", "fontes", ".venv", "venv", "__pycache__", "*.pyc", ".cache")

# Ordem do menu combinada com o autor
MENU_TOPO = ["Início", "Lore", "Wiki", "Compêndio", "Mestre", "Configurações"]
MENU_WIKI = [
    "Mundo", "Geografia", "Cidades", "Lugares", "Facções", "NPCs", "Eventos",
    "Classes", "Raças", "Antecedentes", "Magias", "Dotes", "Perícias",
]
COLUNAS_NPC = ["Retrato", "Nome", "Título", "Raça", "Cidade", "Afiliação", "Situação", "Resumo"]

resultados: list[tuple[str, str, str, str]] = []  # (grupo, verificação, situação, detalhe)


class Pulado(Exception):
    """Verificação que não pôde rodar neste ambiente (não conta como falha)."""


def verificacao(grupo: str, nome: str):
    def decorar(fn):
        @functools.wraps(fn)
        def executar(*args, **kwargs):
            try:
                detalhe = fn(*args, **kwargs) or ""
                resultados.append((grupo, nome, "PASSOU", str(detalhe)))
            except Pulado as exc:
                resultados.append((grupo, nome, "PULADO", str(exc)))
            except AssertionError as exc:
                resultados.append((grupo, nome, "FALHOU", str(exc) or "condição não atendida"))
            except Exception as exc:  # noqa: BLE001 — qualquer erro vira falha legível
                resultados.append((grupo, nome, "FALHOU", f"{type(exc).__name__}: {exc}"))
                if os.environ.get("TESTE_DETALHADO"):
                    traceback.print_exc()
        return executar
    return decorar


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def rodar(cmd: list[str], cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


def construir(copia: Path) -> subprocess.CompletedProcess:
    return rodar([sys.executable, "-m", "mkdocs", "build", "--strict", "-q", "-d", str(copia / "site")], copia)


def ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


def front_matter(texto: str) -> dict:
    import yaml
    m = re.match(r"---\n(.*?)\n---", texto, re.S)
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def paginas_npc(copia: Path) -> list[Path]:
    return [p for p in sorted((copia / "docs" / "personagens").glob("*.md"))
            if p.name != "index.md" and isinstance(front_matter(ler(p)).get("npc"), dict)]


def linhas_tabela_npc(html: str) -> list[str]:
    tabela = re.search(r'<div class="npc-tabela">.*?<tbody>(.*?)</tbody>', html, re.S)
    assert tabela, "tabela de NPCs não encontrada em personagens/index.html"
    return re.findall(r"<tr>(.*?)</tr>", tabela.group(1), re.S)


def importar_hooks(copia: Path):
    sys.path.insert(0, str(copia / "hooks"))
    import linha_tempo  # noqa: PLC0415
    return linha_tempo


def hash_pasta(pasta: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(pasta.rglob("*.md")):
        h.update(p.relative_to(pasta).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()


# --------------------------------------------------------------------------
# 1. Cálculos
# --------------------------------------------------------------------------

@verificacao("1. Cálculos", "Linha do tempo: datas, ordem cronológica e estado atual")
def teste_linha_tempo(copia: Path):
    lt = importar_hooks(copia)
    assert lt.chave_data("24 de outubro de 1453") == (1453, 10, 24)
    assert lt.chave_data("3 de Março de 1453") == (1453, 3, 3), "mês com acento/maiúscula não reconhecido"
    assert lt.chave_data("algum dia") is None
    eventos = [
        {"id": 1, "data": "10 de março de 1453", "titulo": "B",
         "mudancas": [{"pagina": "personagens/x.md", "campo": "cidade", "valor": "Valynesse"}]},
        {"id": 2, "data": "2 de março de 1453", "titulo": "A",
         "mudancas": [{"pagina": "personagens/x.md", "campo": "cidade", "valor": "Dodixie"}]},
        {"id": 3, "sessao": 1, "titulo": "Sem data"},
    ]
    assert [e["titulo"] for e in lt.ordenar(eventos)] == ["A", "B", "Sem data"], "ordem cronológica errada"
    assert lt.estado_atual(eventos, "personagens/x.md")["cidade"][0] == "Valynesse", \
        "o estado atual deve ser a mudança mais recente na cronologia"


# --------------------------------------------------------------------------
# 2. Menu
# --------------------------------------------------------------------------

def _nav(copia: Path) -> list:
    import yaml

    class Carregador(yaml.SafeLoader):
        pass
    Carregador.add_multi_constructor("tag:yaml.org,2002:python/", lambda carregador, sufixo, no: None)
    return yaml.load(ler(copia / "mkdocs.yml"), Loader=Carregador)["nav"]


def _titulos(itens: list) -> list[str]:
    return [next(iter(i)) for i in itens if isinstance(i, dict)]


@verificacao("2. Menu", "Seis categorias de topo, na ordem combinada")
def teste_menu_topo(copia: Path):
    topo = _titulos(_nav(copia))
    assert topo == MENU_TOPO, f"esperado {MENU_TOPO}, obtido {topo}"


@verificacao("2. Menu", "Subcategorias da Wiki, na ordem combinada")
def teste_menu_wiki(copia: Path):
    wiki = next(i["Wiki"] for i in _nav(copia) if isinstance(i, dict) and "Wiki" in i)
    sub = _titulos(wiki)
    assert sub == MENU_WIKI, f"esperado {MENU_WIKI}, obtido {sub}"


@verificacao("2. Menu", "Todo NPC está no menu (Wiki → NPCs)")
def teste_menu_npcs(copia: Path):
    texto = ler(copia / "mkdocs.yml")
    faltando = [p.name for p in paginas_npc(copia) if f"personagens/{p.name}" not in texto]
    assert not faltando, "fora do menu: " + ", ".join(faltando)


# --------------------------------------------------------------------------
# 3. Relações
# --------------------------------------------------------------------------

@verificacao("3. Relações", "gerar_relacoes.py não muda nada se rodado de novo")
def teste_relacoes(copia: Path):
    antes = hash_pasta(copia / "docs")
    r = rodar([sys.executable, "scripts/gerar_relacoes.py"], copia)
    assert r.returncode == 0, r.stderr[-500:]
    assert hash_pasta(copia / "docs") == antes, \
        "o gerador mudou páginas: alguém editou à mão um trecho gerado ou mudou o script sem regenerar"


# --------------------------------------------------------------------------
# 4. Build
# --------------------------------------------------------------------------

@verificacao("4. Build", "mkdocs build --strict sem erros nem links quebrados")
def teste_build(copia: Path):
    r = construir(copia)
    saida = (r.stdout + r.stderr).strip()
    problemas = [l for l in saida.splitlines() if ("WARNING" in l or "ERROR" in l) and "git logs" not in l]
    assert r.returncode == 0, "build falhou:\n" + "\n".join(problemas[-15:] or saida.splitlines()[-15:])
    return f"{sum(1 for _ in (copia / 'site').rglob('index.html'))} páginas geradas"


# --------------------------------------------------------------------------
# 5. Páginas geradas
# --------------------------------------------------------------------------

def _site(copia: Path, rota: str) -> str:
    arq = copia / "site" / rota / "index.html"
    if not arq.exists():
        raise Pulado(f"site/{rota} não existe (o build falhou?)")
    return ler(arq)


@verificacao("5. Páginas", "Tabela de NPCs: uma linha por NPC e as colunas combinadas")
def teste_tabela_npcs(copia: Path):
    html = _site(copia, "personagens")
    linhas = linhas_tabela_npc(html)
    esperados = len(paginas_npc(copia))
    assert len(linhas) == esperados, f"{len(linhas)} linhas na tabela, {esperados} páginas de NPC"
    cabecalho = re.search(r'<div class="npc-tabela">.*?<thead>(.*?)</thead>', html, re.S).group(1)
    colunas = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<th[^>]*>(.*?)</th>", cabecalho, re.S)]
    assert colunas == COLUNAS_NPC, f"colunas {colunas}"
    assert 'class="npc-busca"' in html, "caixa de busca ausente"
    return f"{len(linhas)} NPCs"


@verificacao("5. Páginas", "Cada NPC tem caixa de retrato/dados e abas começando em Visão geral")
def teste_paginas_npc(copia: Path):
    problemas = []
    for p in paginas_npc(copia):
        html = _site(copia, f"personagens/{p.stem}")
        if 'class="npc-cabecalho"' not in html:
            problemas.append(f"{p.stem}: sem caixa")
        rotulos = re.findall(r'<label for="npc-aba-\d+">([^<]*)</label>', html)
        if not rotulos or rotulos[0] != "Visão geral":
            problemas.append(f"{p.stem}: abas {rotulos[:3]}")
    assert not problemas, "; ".join(problemas[:8])


@verificacao("5. Páginas", "Lista de sessões mostra todas as sessões")
def teste_sessoes(copia: Path):
    html = _site(copia, "mestre/sessoes")
    arquivos = sorted((copia / "docs" / "mestre" / "sessoes").glob("sessao-*.md"))
    faltando = [a.stem for a in arquivos if f'href="../sessoes/{a.stem}/"' not in html and f'href="{a.stem}/"' not in html]
    assert not faltando, "fora da lista: " + ", ".join(faltando)
    return f"{len(arquivos)} sessões"


@verificacao("5. Páginas", "Formulários embutidos de Adicionar NPC e Nova sessão aparecem nas páginas")
def teste_botoes(copia: Path):
    html_npc = _site(copia, "personagens")
    assert 'class="criar-entidade"' in html_npc and 'data-tipo="npc"' in html_npc, "formulário de NPC ausente"
    html_sessoes = _site(copia, "mestre/sessoes")
    assert 'class="criar-sessao"' in html_sessoes, "formulário de Nova sessão ausente"


@verificacao("5. Páginas", "Página geral da linha do tempo existe")
def teste_pagina_linha_tempo(copia: Path):
    html = _site(copia, "mestre/linha-do-tempo")
    assert "linha-tempo" in html or "Nenhum acontecimento" in html, "conteúdo da linha do tempo ausente"


# --------------------------------------------------------------------------
# 7. Painel do Mestre (Flask), na cópia
# --------------------------------------------------------------------------

NPC_TESTE = "Teste Automático"
SLUG_TESTE = "teste-automatico"


def _painel(copia: Path):
    try:
        import flask  # noqa: F401, PLC0415
    except ImportError as exc:
        raise Pulado("Flask não instalado (pip install -r requirements.txt)") from exc
    os.environ["GALLANCOURT_ADMIN_ROOT"] = str(copia)
    sys.path.insert(0, str(copia / "admin"))
    import app as painel  # noqa: PLC0415
    return painel.app.test_client()


def _ok(resposta) -> None:
    texto = resposta.get_data(as_text=True)
    assert resposta.status_code < 400, f"HTTP {resposta.status_code}"
    if "aviso--erro" in texto:
        erro = re.findall(r'<pre class="saida-build">(.*?)</pre>', texto, re.S) or \
               re.findall(r'aviso--erro">(.*?)</p>', texto, re.S)
        raise AssertionError(re.sub(r"\s+", " ", erro[0])[-300:] if erro else "o Painel mostrou um erro")


@verificacao("7. Painel", "Adicionar NPC")
def teste_painel_npc(copia: Path):
    c = _painel(copia)
    _ok(c.post("/npc/novo", data={
        "nome": NPC_TESTE, "titulo": "Capitã", "cidade": "Dodixie", "afiliacao": "Casa Duvant",
        "resumo": "NPC criado pelo teste.",
    }))
    pagina = copia / "docs" / "personagens" / f"{SLUG_TESTE}.md"
    assert pagina.exists(), "página do NPC não foi criada"
    assert front_matter(ler(pagina)).get("npc", {}).get("titulo") == "Capitã", "dados do NPC não gravados"
    assert f"personagens/{SLUG_TESTE}.md" in ler(copia / "mkdocs.yml"), "NPC não entrou no menu"


@verificacao("7. Painel", "Adicionar NPC genérico")
def teste_painel_npc_generico(copia: Path):
    c = _painel(copia)
    _ok(c.post("/npc/novo", data={"nome": "Guarda de teste", "generico": "on"}))
    pagina = copia / "docs" / "personagens" / "genericos" / "guarda-de-teste.md"
    assert pagina.exists(), "página do NPC genérico não foi criada (deveria ir para personagens/genericos/)"
    assert "personagens/genericos/guarda-de-teste.md" in ler(copia / "mkdocs.yml"), "NPC genérico não entrou no menu"


@verificacao("7. Painel", "Começar ficha de combate a partir de um NPC genérico")
def teste_painel_copiar_ficha_generica(copia: Path):
    pagina_generico = copia / "docs" / "personagens" / "genericos" / "guarda-de-teste.md"
    if not pagina_generico.exists():
        raise Pulado("depende do teste 'Adicionar NPC genérico'")
    c = _painel(copia)
    _ok(c.post("/ficha-combate", data={
        "pagina": "personagens/genericos/guarda-de-teste.md", "slug_antigo": "",
        "campo_nome": "Guarda de teste", "campo_ca": "16", "campo_pv": "11 (2d8+2)",
        "campo_deslocamento": "9 m",
    }))
    r = c.get(
        "/ficha-combate?pagina=mestre/index.md"
        "&copiar_de=personagens/genericos/guarda-de-teste.md::guarda-de-teste"
    )
    html = r.get_data(as_text=True)
    assert 'value="16"' in html, "CA do NPC genérico não foi copiada para o formulário"
    assert 'value="Guarda de teste"' in html, "nome do NPC genérico não foi copiado para o formulário"


@verificacao("7. Painel", "Adicionar lugar")
def teste_painel_lugar(copia: Path):
    c = _painel(copia)
    _ok(c.post("/lugar/novo", data={
        "nome": "Taberna de teste", "situado": "Dodixie", "regiao": "Costa norte",
        "reino": "Gallancourt (Aliança dos Lordes)",
    }))
    pagina = copia / "docs" / "lugares" / "taberna-de-teste.md"
    assert pagina.exists(), "página do lugar não foi criada"
    assert front_matter(ler(pagina)).get("lugar", {}).get("situado") == "Dodixie", "dados do lugar não gravados"
    assert "lugares/taberna-de-teste.md" in ler(copia / "mkdocs.yml"), "lugar não entrou no menu"


@verificacao("7. Painel", "Adicionar jogador")
def teste_painel_jogador(copia: Path):
    c = _painel(copia)
    _ok(c.post("/jogador/novo", data={"nome": "Personagem de teste", "jogador": "Jogador de teste"}))
    pagina = copia / "docs" / "mestre" / "jogadores" / "personagem-de-teste.md"
    assert pagina.exists(), "página do jogador não foi criada"
    assert "mestre/jogadores/personagem-de-teste.md" in ler(copia / "mkdocs.yml"), "jogador não entrou no menu"


@verificacao("7. Painel", "Criar sessão nova")
def teste_painel_sessao(copia: Path):
    c = _painel(copia)
    _ok(c.post("/sessoes/nova", data={"numero": "99", "titulo": "Sessão de teste", "local": "Dodixie"}))
    assert list((copia / "docs" / "mestre" / "sessoes").glob("sessao-99-*.md")), "página da sessão não criada"


@verificacao("7. Painel", "Salvar participantes da sessão")
def teste_painel_participantes(copia: Path):
    pastas_sessao = list((copia / "docs" / "mestre" / "sessoes").glob("sessao-99-*.md"))
    pagina_jogador = copia / "docs" / "mestre" / "jogadores" / "personagem-de-teste.md"
    if not pastas_sessao or not pagina_jogador.exists():
        raise Pulado("depende dos testes 'Criar sessão nova' e 'Adicionar jogador'")
    c = _painel(copia)
    pagina_sessao = pastas_sessao[0].relative_to(copia / "docs").as_posix()
    _ok(c.post("/sessoes/participantes", data={
        "pagina": pagina_sessao, "jogadores": ["mestre/jogadores/personagem-de-teste.md"],
    }))
    assert front_matter(ler(pastas_sessao[0])).get("participantes", {}).get("jogadores") == [
        "mestre/jogadores/personagem-de-teste.md",
    ], "participantes não gravados no front-matter da sessão"


@verificacao("7. Painel", "API JSON: listar e criar NPC/lugar/jogador")
def teste_painel_api_entidades(copia: Path):
    c = _painel(copia)

    r = c.get("/api/npcs")
    assert r.status_code == 200 and isinstance(r.get_json()["itens"], list), "GET /api/npcs falhou"

    _ok(c.post("/api/npcs", data={"nome": "NPC via API", "cidade": "Dodixie"}))
    assert (copia / "docs" / "personagens" / "npc-via-api.md").exists(), "POST /api/npcs não criou a página"
    nomes = [i["nome"] for i in c.get("/api/npcs").get_json()["itens"]]
    assert "NPC via API" in nomes, "NPC criado via API não aparece em GET /api/npcs"

    _ok(c.post("/api/lugares", data={"nome": "Lugar via API", "tipo": "taberna"}))
    assert (copia / "docs" / "lugares" / "lugar-via-api.md").exists(), "POST /api/lugares não criou a página"

    _ok(c.post("/api/jogadores", data={"nome": "Jogador via API"}))
    assert (copia / "docs" / "mestre" / "jogadores" / "jogador-via-api.md").exists(), "POST /api/jogadores não criou a página"

    resposta_erro = c.post("/api/lugares", data={"tipo": "sem nome"})
    assert resposta_erro.status_code == 400, "POST /api/lugares sem nome deveria devolver 400"


@verificacao("7. Painel", "API JSON: criar sessão com NPCs/Jogadores/Lugares e anotação de prompt")
def teste_painel_api_criar_sessao(copia: Path):
    pagina_npc = copia / "docs" / "personagens" / "npc-via-api.md"
    pagina_lugar = copia / "docs" / "lugares" / "lugar-via-api.md"
    pagina_jogador = copia / "docs" / "mestre" / "jogadores" / "jogador-via-api.md"
    if not (pagina_npc.exists() and pagina_lugar.exists() and pagina_jogador.exists()):
        raise Pulado("depende do teste 'API JSON: listar e criar NPC/lugar/jogador'")
    c = _painel(copia)
    r = c.post("/api/sessoes/nova", json={
        "numero": 98, "titulo": "Sessão via API", "campos": {"data": "2026-11-01"},
        "npcs": ["personagens/npc-via-api.md"], "jogadores": ["mestre/jogadores/jogador-via-api.md"],
        "lugares": ["lugares/lugar-via-api.md"], "prompt": "Quero uma sessão de teste.",
    })
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.get_json()}"
    paginas = list((copia / "docs" / "mestre" / "sessoes").glob("sessao-98-*.md"))
    assert paginas, "página da sessão via API não foi criada"
    texto = ler(paginas[0])
    assert "[NPC via API]" in texto, "link do NPC selecionado não apareceu na sessão"
    assert "[Lugar via API]" in texto, "link do lugar selecionado não apareceu na sessão"
    assert "Quero uma sessão de teste." in texto, "anotação do prompt não apareceu na sessão"
    assert front_matter(texto).get("participantes", {}).get("npcs") == ["personagens/npc-via-api.md"], \
        "participantes (npcs) não gravados a partir da criação via API"


@verificacao("7. Painel", "API JSON do Painel de Iniciativa embutido")
def teste_painel_api_iniciativa(copia: Path):
    c = _painel(copia)
    pagina = "mestre/sessoes/sessao-0-os-grilhoes-da-estrada.md"
    base = f"/api/sessao-ao-vivo/{pagina}"

    r = c.get(base)
    assert r.status_code == 200, f"HTTP {r.status_code}"
    dados = r.get_json()
    assert dados["pagina"] == pagina, "resposta não trouxe a página certa"
    # A Sessão 0 tem 6 fichas de combate na própria página e nenhum participante cadastrado —
    # a lista tem que vir só dessas 6, nunca de todo stat-block do site (item 2.6.1 do pedido).
    assert len(dados["fichas_disponiveis"]) == 6, (
        f"esperava 6 fichas (só as da própria página), veio {len(dados['fichas_disponiveis'])}"
    )
    assert all(f["pagina_rel_docs"] == pagina for f in dados["fichas_disponiveis"]), (
        "uma ficha de fora da página vazou para a lista — deveria estar restrita à sessão"
    )

    r2 = c.post(f"{base}/combatente", json={"nome": "Teste API", "tipo": "jogador", "iniciativa": 7})
    assert r2.status_code == 200, f"HTTP {r2.status_code}"
    dados2 = r2.get_json()
    combatente = next((x for x in dados2["combatentes"] if x["nome"] == "Teste API"), None)
    assert combatente is not None, "combatente criado pela API não apareceu no estado devolvido"

    r3 = c.post(f"{base}/combatente/{combatente['id']}/remover")
    assert r3.status_code == 200 and not r3.get_json()["combatentes"], "remoção pela API não funcionou"

    r4 = c.get("/api/sessao-ao-vivo/personagens/pagina-que-nao-existe.md")
    assert r4.status_code == 404 and r4.get_json().get("erro"), "página inexistente devia devolver 404 em JSON"


@verificacao("7. Painel", "Criar item de Loot & Pistas dentro de uma aba de sessão")
def teste_painel_item(copia: Path):
    pastas_sessao = list((copia / "docs" / "mestre" / "sessoes").glob("sessao-99-*.md"))
    if not pastas_sessao:
        raise Pulado("depende do teste 'Criar sessão nova'")
    pagina_sessao = pastas_sessao[0]
    pagina_rel = pagina_sessao.relative_to(copia / "docs").as_posix()
    c = _painel(copia)
    _ok(c.post("/ficha-item", data={
        "pagina": pagina_rel, "slug_antigo": "", "campo_nome": "Moeda de teste",
        "campo_descricao": "Uma moeda qualquer.", "campo_local": "Dodixie",
        "ancora": "## Itens encontrados",
    }))
    texto = ler(pagina_sessao)
    assert "<!-- inicio:item:moeda-de-teste -->" in texto, "item não foi criado na página"
    # A âncora "## Itens encontrados" é o último cabeçalho da aba "Loot & Pistas" — sem cuidado,
    # a busca por "onde inserir" passa reto pelo fim da aba (indentada 4 espaços) e cai dentro da
    # aba seguinte, "Segredos do Mestre" (sem indentação nenhuma). As duas verificações abaixo
    # cobrem esse caso.
    linha_cartao = next(l for l in texto.splitlines() if "inicio:item:moeda-de-teste" in l)
    assert linha_cartao.startswith("    "), "o cartão do item perdeu a indentação da aba"
    assert texto.index("inicio:item:moeda-de-teste") < texto.index('=== "Segredos do Mestre"'), (
        "o item vazou para dentro da aba seguinte (Segredos do Mestre)"
    )
    r = construir(copia)
    assert r.returncode == 0, "build falhou depois de criar o item de Loot & Pistas"


@verificacao("7. Painel", "Registrar acontecimento com mudança de estado")
def teste_painel_acontecimento(copia: Path):
    c = _painel(copia)
    pagina = f"personagens/{SLUG_TESTE}.md"
    if not (copia / "docs" / pagina).exists():
        raise Pulado("depende do teste 'Adicionar NPC'")
    _ok(c.post("/linha-do-tempo", data={
        "data": "2 de março de 1453", "sessao": "99", "titulo": "Morte de teste", "envolvido": [pagina],
        "mudanca_pagina_0": pagina, "mudanca_campo_0": "situacao", "mudanca_valor_0": "Morta",
    }))
    assert "Morte de teste" in ler(copia / "dados" / "linha-do-tempo.yml"), "acontecimento não gravado"


@verificacao("7. Painel", "Efeito no site: NPC na tabela e situação atual")
def teste_painel_efeito(copia: Path):
    if not (copia / "docs" / "personagens" / f"{SLUG_TESTE}.md").exists():
        raise Pulado("depende dos testes anteriores do Painel")
    r = construir(copia)
    assert r.returncode == 0, "build falhou depois das ações do Painel"
    html = _site(copia, f"personagens/{SLUG_TESTE}")
    assert "Situação atual" in html and "Morta" in html, "situação atual não aparece na caixa do NPC"
    assert "Linha do tempo" in re.findall(r'<label for="npc-aba-\d+">([^<]*)</label>', html), "aba Linha do tempo ausente"
    tabela = _site(copia, "personagens")
    assert len(linhas_tabela_npc(tabela)) == len(paginas_npc(copia)), "o NPC novo não entrou na tabela"
    assert "Sessão de teste" in _site(copia, "mestre/sessoes"), "a sessão nova não entrou na lista"


@verificacao("7. Painel", "Servidor único: / serve o site, /painel serve o Painel, 404 funciona")
def teste_painel_servir_site(copia: Path):
    if not (copia / "docs" / "personagens" / f"{SLUG_TESTE}.md").exists():
        raise Pulado("depende dos testes anteriores do Painel")
    c = _painel(copia)

    home = c.get("/")
    assert home.status_code == 200, f"GET / -> {home.status_code}"
    assert "<html" in home.get_data(as_text=True).lower(), "GET / não devolveu uma página HTML"

    painel = c.get("/painel")
    assert painel.status_code == 200, f"GET /painel -> {painel.status_code}"
    assert "sess" in painel.get_data(as_text=True).lower(), "GET /painel não parece ser o formulário de sessão"

    pagina_npc = c.get(f"/personagens/{SLUG_TESTE}/")
    assert pagina_npc.status_code == 200, "a página do NPC criado pelo Painel não é servida em /"
    assert NPC_TESTE in pagina_npc.get_data(as_text=True), "conteúdo do NPC ausente na página servida"

    ausente = c.get("/esta-pagina-nao-existe/")
    assert ausente.status_code == 404, f"GET de página inexistente -> {ausente.status_code}, esperava 404"


# --------------------------------------------------------------------------
# 6. Navegador (Playwright)
# --------------------------------------------------------------------------

class _Servidor:
    def __init__(self, pasta: Path):
        class Silencioso(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):  # sem uma linha de log por acesso
                pass
        manipulador = functools.partial(Silencioso, directory=str(pasta))
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), manipulador)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def parar(self):
        self.httpd.shutdown()


_navegador = {}


def _pagina(copia: Path, largura: int = 1300):
    if "erro" in _navegador:
        raise Pulado(_navegador["erro"])
    if "browser" not in _navegador:
        try:
            from playwright.sync_api import sync_playwright  # noqa: PLC0415
        except ImportError:
            _navegador["erro"] = "Playwright não instalado (pip install playwright && playwright install chromium)"
            raise Pulado(_navegador["erro"]) from None
        pw = sync_playwright().start()
        tentativas = [{}]
        for caminho in (os.environ.get("GALLANCOURT_CHROMIUM"), "/opt/pw-browsers/chromium"):
            if caminho and Path(caminho).exists():
                tentativas.append({"executable_path": caminho})
        for opcoes in tentativas:
            try:
                _navegador["browser"] = pw.chromium.launch(**opcoes)
                break
            except Exception:  # noqa: BLE001
                continue
        else:
            pw.stop()
            _navegador["erro"] = "Chromium não encontrado (rode: playwright install chromium)"
            raise Pulado(_navegador["erro"])
        _navegador["pw"] = pw
        _navegador["servidor"] = _Servidor(copia / "site")
    pagina = _navegador["browser"].new_page(viewport={"width": largura, "height": 900})
    return pagina, _navegador["servidor"].url


def _visiveis(pagina) -> int:
    return pagina.eval_on_selector_all(".npc-tabela tbody tr", "linhas => linhas.filter(l => !l.hidden).length")


@verificacao("6. Navegador", "Busca por texto filtra a tabela de NPCs")
def teste_nav_busca(copia: Path):
    pagina, url = _pagina(copia)
    pagina.goto(f"{url}/personagens/")
    total = _visiveis(pagina)
    pagina.fill(".npc-busca", "dodixie")
    filtrados = _visiveis(pagina)
    assert 0 < filtrados < total, f"{filtrados} de {total} visíveis após filtrar por 'dodixie'"
    pagina.close()


@verificacao("6. Navegador", "Clique no cabeçalho ordena e inverte a ordem")
def teste_nav_ordem(copia: Path):
    pagina, url = _pagina(copia)
    pagina.goto(f"{url}/personagens/")
    pagina.click("th >> text=Nome")
    primeiro = pagina.inner_text(".npc-tabela tbody tr:first-child td:nth-child(2)")
    pagina.click("th >> text=Nome")
    invertido = pagina.inner_text(".npc-tabela tbody tr:first-child td:nth-child(2)")
    assert primeiro != invertido, "a segunda ordenação não inverteu a ordem"
    pagina.close()


@verificacao("6. Navegador", "Filtro do cabeçalho (Cidade) filtra a tabela")
def teste_nav_filtro(copia: Path):
    pagina, url = _pagina(copia)
    pagina.goto(f"{url}/personagens/")
    total = _visiveis(pagina)
    pagina.select_option("th:has-text('Cidade') select", "Valynesse")
    filtrados = _visiveis(pagina)
    cidades = pagina.eval_on_selector_all(
        ".npc-tabela tbody tr:not([hidden]) td:nth-child(6)", "cs => [...new Set(cs.map(c => c.textContent.trim()))]")
    assert 0 < filtrados < total and cidades == ["Valynesse"], f"{filtrados} visíveis, cidades {cidades}"
    pagina.close()


@verificacao("6. Navegador", "Abas da página do NPC trocam de conteúdo")
def teste_nav_abas(copia: Path):
    pagina, url = _pagina(copia)
    pagina.goto(f"{url}/personagens/scyras-corbeau/")
    rotulos = pagina.locator(".npc-abas .tabbed-labels label")
    assert rotulos.count() >= 2, "menos de duas abas"
    rotulos.nth(1).click()
    visivel = pagina.locator(".npc-abas .tabbed-block").nth(1).is_visible()
    assert visivel, "a segunda aba não ficou visível depois do clique"
    pagina.close()


@verificacao("6. Navegador", "Menu abre no celular")
def teste_nav_celular(copia: Path):
    pagina, url = _pagina(copia, largura=390)
    pagina.goto(f"{url}/")
    pagina.click(".md-header label[for='__drawer']")
    pagina.wait_for_timeout(400)
    assert pagina.locator(".md-nav--primary").first.is_visible(), "menu não abriu"
    pagina.close()


# --------------------------------------------------------------------------
# Execução
# --------------------------------------------------------------------------

def relatorio() -> tuple[str, int]:
    simbolo = {"PASSOU": "✅", "FALHOU": "❌", "PULADO": "⏭️"}
    linhas = ["| | Grupo | Verificação | Detalhe |", "|---|---|---|---|"]
    for grupo, nome, situacao, detalhe in resultados:
        detalhe = detalhe.replace("|", "\\|").replace("\n", " ")
        linhas.append(f"| {simbolo[situacao]} | {grupo} | {nome} | {detalhe} |")
    falhas = sum(1 for r in resultados if r[2] == "FALHOU")
    passou = sum(1 for r in resultados if r[2] == "PASSOU")
    pulados = sum(1 for r in resultados if r[2] == "PULADO")
    resumo = f"**{passou} passaram · {falhas} falharam · {pulados} pulados**"
    return resumo + "\n\n" + "\n".join(linhas) + "\n", falhas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--sem-navegador", action="store_true", help="pula os testes de navegador")
    parser.add_argument("--sem-painel", action="store_true", help="pula os testes do Painel do Mestre")
    parser.add_argument("--manter", action="store_true", help="não apaga a cópia temporária")
    args = parser.parse_args()

    temporaria = Path(tempfile.mkdtemp(prefix="gallancourt-teste-"))
    copia = temporaria / "projeto"
    shutil.copytree(RAIZ, copia, ignore=IGNORAR_NA_COPIA)
    print(f"Testando numa cópia em {copia} …", flush=True)

    try:
        teste_linha_tempo(copia)
        teste_menu_topo(copia)
        teste_menu_wiki(copia)
        teste_menu_npcs(copia)
        teste_relacoes(copia)
        teste_build(copia)
        teste_tabela_npcs(copia)
        teste_paginas_npc(copia)
        teste_sessoes(copia)
        teste_botoes(copia)
        teste_pagina_linha_tempo(copia)
        if not args.sem_navegador:
            for t in (teste_nav_busca, teste_nav_ordem, teste_nav_filtro, teste_nav_abas, teste_nav_celular):
                t(copia)
        if not args.sem_painel:
            for t in (
                teste_painel_npc, teste_painel_npc_generico, teste_painel_copiar_ficha_generica,
                teste_painel_lugar, teste_painel_jogador, teste_painel_sessao, teste_painel_participantes,
                teste_painel_api_entidades, teste_painel_api_criar_sessao,
                teste_painel_api_iniciativa, teste_painel_item, teste_painel_acontecimento, teste_painel_efeito,
                teste_painel_servir_site,
            ):
                t(copia)
    finally:
        if "browser" in _navegador:
            _navegador["browser"].close()
            _navegador["servidor"].parar()
            _navegador["pw"].stop()
        if not args.manter:
            shutil.rmtree(temporaria, ignore_errors=True)

    texto, falhas = relatorio()
    print("\n" + texto)
    resumo_github = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo_github:
        with open(resumo_github, "a", encoding="utf-8") as f:
            f.write("## Teste do site\n\n" + texto)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
