"""Servidor único de Gallancourt — serve o site (pasta site/, já construído pelo MkDocs) e o
Painel do Mestre, na mesma origem/porta. Nada de editar arquivos à mão nem de abrir dois
endereços diferentes.

Uso:
    .venv\\Scripts\\python admin\\app.py
    (ou dê duplo clique em admin\\iniciar-painel.bat)

Depois abra http://127.0.0.1:5001/ — é o site inteiro (wiki + ferramentas do Painel). Roda só em
127.0.0.1 por padrão (não aparece na rede). Veja docs/mestre/painel.md para o guia de uso.
"""
from __future__ import annotations

import datetime
import hmac
import os
import secrets
import time
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, session, url_for

import wiki_data as wd
import roadmap
import bugs
import gerador_npc as gn
import banco
import personagens_api as ma
import combate_api as ca

ROOT = Path(os.environ.get("GALLANCOURT_ADMIN_ROOT", wd.DEFAULT_ROOT)).resolve()
SITE_DIR = ROOT / "site"
ENGINE_BANCO = banco.criar_engine(ROOT)
SessaoBanco = banco.fabrica_sessao(ENGINE_BANCO)


def _carregar_env_local(root: Path) -> None:
    """Lê admin/painel_local.env (ignorado pelo git, nunca commitado) e preenche variáveis de
    ambiente que ainda não estejam definidas — assim PAINEL_SENHA não precisa ser digitada nem
    aparecer em nenhum arquivo versionado. Formato simples, uma linha `CHAVE=valor` por vez."""
    caminho = root / "admin" / "painel_local.env"
    if not caminho.is_file():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip())


_carregar_env_local(ROOT)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB por envio
app.secret_key = os.environ.get("PAINEL_SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("PAINEL_HTTPS", "") == "1"
app.permanent_session_lifetime = datetime.timedelta(days=30)

SENHA_PAINEL = os.environ.get("PAINEL_SENHA", "").strip()
_ROTAS_LIVRES = {"tela_login", "fazer_login", "static", "api_bugs_opcoes", "api_criar_bug"}
_tentativas_falhas: dict[str, list[float]] = {}
_JANELA_BLOQUEIO_SEGUNDOS = 300
_MAX_TENTATIVAS = 5


def _ip_cliente() -> str:
    return (request.remote_addr or "desconhecido").strip()


def _bloqueado(ip: str) -> bool:
    agora = time.time()
    tentativas = [t for t in _tentativas_falhas.get(ip, []) if agora - t < _JANELA_BLOQUEIO_SEGUNDOS]
    _tentativas_falhas[ip] = tentativas
    return len(tentativas) >= _MAX_TENTATIVAS


def _registrar_falha(ip: str) -> None:
    _tentativas_falhas.setdefault(ip, []).append(time.time())


@app.get("/login")
def tela_login():
    if not SENHA_PAINEL or session.get("autenticado"):
        return redirect(request.args.get("next") or url_for("servir_site", caminho=""))
    return render_template("login.html", proximo=request.args.get("next", ""), erro=None)


@app.post("/login")
def fazer_login():
    ip = _ip_cliente()
    proximo = request.form.get("proximo") or url_for("servir_site", caminho="")
    if _bloqueado(ip):
        return render_template(
            "login.html", proximo=proximo,
            erro="Muitas tentativas erradas. Espere alguns minutos antes de tentar de novo.",
        ), 429
    senha = request.form.get("senha", "")
    if SENHA_PAINEL and hmac.compare_digest(senha, SENHA_PAINEL):
        session.clear()
        session["autenticado"] = True
        session.permanent = True
        return redirect(proximo)
    _registrar_falha(ip)
    return render_template("login.html", proximo=proximo, erro="Senha incorreta."), 401


@app.get("/logout")
def fazer_logout():
    session.clear()
    return redirect(url_for("tela_login"))


@app.get("/api/auth/estado")
def api_auth_estado():
    """Usado por docs/javascripts/modo-mestre.js em toda página do site, pra saber se mostra o
    botão 'Entrar' ou o indicador de Modo Mestre ativo — e por monstro-ficha.js, pra decidir se
    desenha os controles de edição."""
    return jsonify(autenticado=bool(session.get("autenticado")))


@app.post("/api/auth/entrar")
def api_auth_entrar():
    """Versão em JSON do /login (mesma senha, mesma sessão) — usada pelo popup de Modo Mestre
    (docs/javascripts/modo-mestre.js), que não navega pra outra página."""
    ip = _ip_cliente()
    if _bloqueado(ip):
        return jsonify(autenticado=False, erro="Muitas tentativas erradas. Espere alguns minutos."), 429
    dados = request.get_json(silent=True) or {}
    senha = dados.get("senha", "")
    if SENHA_PAINEL and hmac.compare_digest(senha, SENHA_PAINEL):
        session.clear()
        session["autenticado"] = True
        session.permanent = True
        return jsonify(autenticado=True)
    _registrar_falha(ip)
    return jsonify(autenticado=False, erro="Senha incorreta."), 401


@app.post("/api/auth/sair")
def api_auth_sair():
    session.clear()
    return jsonify(autenticado=False)


# Prefixos de API que ficam de leitura livre mesmo com PAINEL_SENHA definida (ver
# "Mudança de acesso" — o site passou a ser consulta pública; só criar/editar/excluir exige
# login). Checado só em GET: POST/PUT/DELETE nesses mesmos prefixos continuam exigindo login.
_PREFIXOS_API_LEITURA_LIVRE = (
    "/api/personagens", "/api/catalogo", "/api/auth/", "/api/roadmap", "/api/combate",
)


@app.before_request
def _exigir_login():
    if not SENHA_PAINEL:
        return None  # sem PAINEL_SENHA configurada: autenticação desligada (uso só local)
    if request.endpoint in _ROTAS_LIVRES or request.endpoint == "api_auth_entrar":
        return None
    if request.method == "GET" and (
        request.endpoint == "servir_site" or request.path.startswith(_PREFIXOS_API_LEITURA_LIVRE)
    ):
        return None  # o site e as APIs de leitura são públicos — só a edição exige senha
    if session.get("autenticado"):
        return None
    if request.path.startswith("/api/"):
        return jsonify(erro="Faça login (Modo Mestre) para isso."), 401
    destino = request.full_path if request.query_string else request.path
    return redirect(url_for("tela_login", next=destino))


def _campanha_atual():
    """Lê a campanha do banco (ver admin/banco.py) pra mostrar no cabeçalho do Painel. Se o banco
    ainda não foi migrado (`alembic upgrade head` nunca rodou), devolve None em vez de quebrar o
    Painel inteiro — é uma fundação nova, opcional, não uma dependência obrigatória ainda."""
    try:
        with SessaoBanco() as sessao:
            return sessao.query(banco.Campanha).first()
    except Exception:
        return None


@app.context_processor
def _globais_template():
    return {
        "pastas_imagens": wd.PASTAS_IMAGENS, "autenticacao_ativa": bool(SENHA_PAINEL),
        "campanha": _campanha_atual(),
    }


def _entidade_por_slug(lista: list[wd.Entidade], slug: str) -> wd.Entidade | None:
    for e in lista:
        if e.slug == slug:
            return e
    return None


@app.get("/painel")
def formulario_sessao():
    npcs = wd.listar_npcs(ROOT)
    cidades = wd.listar_cidades(ROOT)
    faccoes = wd.listar_faccoes(ROOT)
    proxima = wd.proxima_sessao(ROOT)
    hoje = datetime.date.today().isoformat()
    return render_template(
        "sessao.html",
        npcs=npcs,
        cidades=cidades,
        faccoes=faccoes,
        proxima=proxima,
        hoje=hoje,
        resumo_inicial=request.args.get("resumo", ""),
    )


@app.post("/sessao")
def aplicar_sessao():
    npcs_disponiveis = wd.listar_npcs(ROOT)
    cidades_disponiveis = wd.listar_cidades(ROOT)
    faccoes_disponiveis = wd.listar_faccoes(ROOT)

    titulo = request.form.get("titulo", "").strip() or "Sessão sem título"
    data_real = request.form.get("data_real", "").strip() or datetime.date.today().isoformat()
    data_campanha = request.form.get("data_campanha", "").strip() or "(data não informada)"
    resumo = request.form.get("resumo", "").strip() or "(sem resumo)"

    numero_futuro = wd.proxima_sessao(ROOT)
    selecionados_npc = request.form.getlist("npc")

    npcs_sel: list[tuple[wd.Entidade, str]] = []
    for slug in selecionados_npc:
        e = _entidade_por_slug(npcs_disponiveis, slug)
        if e is None:
            continue
        nota = request.form.get(f"nota_npc_{slug}", "").strip() or f"Participou da sessão {numero_futuro}."
        npcs_sel.append((e, nota))

    locais_sel: list[tuple[wd.Entidade, str]] = []
    for slug in request.form.getlist("local"):
        e = _entidade_por_slug(cidades_disponiveis, slug)
        if e is None:
            continue
        nota = request.form.get(f"nota_local_{slug}", "").strip() or "Foi palco de acontecimentos da sessão."
        locais_sel.append((e, nota))
    for slug in request.form.getlist("faccao"):
        e = _entidade_por_slug(faccoes_disponiveis, slug)
        if e is None:
            continue
        nota = request.form.get(f"nota_faccao_{slug}", "").strip() or "Foi envolvida em acontecimentos da sessão."
        locais_sel.append((e, nota))

    resultado = wd.aplicar_sessao(
        ROOT,
        titulo=titulo,
        data_real=data_real,
        data_campanha=data_campanha,
        resumo=resumo,
        npcs_selecionados=npcs_sel,
        locais_selecionados=locais_sel,
    )
    return render_template("sucesso.html", r=resultado)


@app.get("/ficha")
def escolher_ficha():
    tipo = request.args.get("tipo", "cidade")
    item_slug = request.args.get("item", "")
    if tipo not in wd.TIPOS_FICHA:
        tipo = "cidade"
    listar_fn, campos, titulo_secao = wd.TIPOS_FICHA[tipo]
    itens = listar_fn(ROOT)

    entidade = _entidade_por_slug(itens, item_slug) if item_slug else None
    valores = wd.ler_campos_ficha(wd.docs_dir(ROOT) / entidade.rel_docs, campos) if entidade else {}

    return render_template(
        "ficha.html",
        tipo=tipo,
        itens=itens,
        item_slug=item_slug,
        entidade=entidade,
        campos=campos,
        titulo_secao=titulo_secao,
        valores=valores,
        salvo=False,
    )


@app.post("/ficha")
def salvar_ficha():
    tipo = request.form.get("tipo", "cidade")
    item_slug = request.form.get("item", "")
    if tipo not in wd.TIPOS_FICHA:
        abort(400)
    listar_fn, campos, titulo_secao = wd.TIPOS_FICHA[tipo]
    itens = listar_fn(ROOT)
    entidade = _entidade_por_slug(itens, item_slug)
    if entidade is None:
        abort(404)

    valores = {chave: request.form.get(f"campo_{chave}", "").strip() for chave, _, _ in campos}
    caminho = wd.docs_dir(ROOT) / entidade.rel_docs
    wd.escrever_ficha(caminho, titulo_secao, campos, valores)
    build_ok, build_saida = wd.publicar_build(ROOT)

    valores_atuais = wd.ler_campos_ficha(caminho, campos)
    return render_template(
        "ficha.html",
        tipo=tipo,
        itens=itens,
        item_slug=item_slug,
        entidade=entidade,
        campos=campos,
        titulo_secao=titulo_secao,
        valores=valores_atuais,
        salvo=True,
        build_ok=build_ok,
        build_saida=build_saida,
    )


@app.get("/editar")
def escolher_pagina():
    paginas = wd.listar_todas_paginas(ROOT)
    pagina_escolhida = request.args.get("pagina", "")
    conteudo = ""
    if pagina_escolhida:
        caminho = _resolver_pagina(pagina_escolhida)
        if caminho is None:
            abort(404)
        conteudo = caminho.read_text(encoding="utf-8")
    return render_template(
        "editar.html", paginas=paginas, pagina_escolhida=pagina_escolhida, conteudo=conteudo,
        salvo=False,
    )


@app.post("/editar")
def salvar_pagina():
    pagina_escolhida = request.form.get("pagina", "")
    conteudo = request.form.get("conteudo", "")
    caminho = _resolver_pagina(pagina_escolhida)
    if caminho is None:
        abort(404)
    caminho.write_text(conteudo, encoding="utf-8")
    paginas = wd.listar_todas_paginas(ROOT)
    return render_template(
        "editar.html", paginas=paginas, pagina_escolhida=pagina_escolhida, conteudo=conteudo,
        salvo=True,
    )


@app.post("/editar/imagem")
def enviar_imagem():
    pagina_escolhida = request.form.get("pagina", "")
    caminho = _resolver_pagina(pagina_escolhida)
    if caminho is None:
        abort(404)

    arquivo = request.files.get("imagem")
    paginas = wd.listar_todas_paginas(ROOT)
    conteudo_atual = caminho.read_text(encoding="utf-8")

    if arquivo is None or not arquivo.filename:
        return render_template(
            "editar.html", paginas=paginas, pagina_escolhida=pagina_escolhida,
            conteudo=conteudo_atual, salvo=False, erro_imagem="Escolha um arquivo de imagem primeiro.",
        )

    pasta = request.form.get("pasta", "mundo")
    try:
        destino, snippet = wd.salvar_imagem(ROOT, pagina_escolhida, pasta, arquivo.filename, arquivo.read())
    except ValueError as exc:
        return render_template(
            "editar.html", paginas=paginas, pagina_escolhida=pagina_escolhida,
            conteudo=conteudo_atual, salvo=False, erro_imagem=str(exc),
        )

    conteudo_novo = conteudo_atual.rstrip("\n") + "\n" + snippet
    caminho.write_text(conteudo_novo, encoding="utf-8")

    return render_template(
        "editar.html", paginas=paginas, pagina_escolhida=pagina_escolhida, conteudo=conteudo_novo,
        salvo=True, imagem_salva=str(destino.relative_to(wd.docs_dir(ROOT))),
    )


def _paginas_ficha_combate():
    return [p for p in wd.listar_todas_paginas(ROOT) if p.rel_docs.startswith("mestre/sessoes/")]


@app.get("/ficha-combate")
def escolher_ficha_combate():
    # Desde 2026-10-31, monstro/NPC nomeado/jogador têm ficha de combate de verdade no banco
    # (editável ao vivo na própria página, em Modo Mestre — ver docs/javascripts/ficha.js). Este
    # formulário (texto em Markdown/JSON embutido) continua existindo só para o uso que sobrou:
    # figurantes de sessão sem página própria (ver docs/mestre/manutencao-do-canone.md) — por
    # isso o seletor de página só oferece páginas de sessão.
    paginas = _paginas_ficha_combate()
    fichas = wd.listar_statblocks(ROOT)
    pagina_escolhida = request.args.get("pagina", "")
    slug_escolhido = request.args.get("ficha", "")

    valores: dict = {}
    if pagina_escolhida and slug_escolhido:
        caminho = _resolver_pagina(pagina_escolhida)
        if caminho is None:
            abort(404)
        valores = wd.ler_statblocks_da_pagina(caminho).get(slug_escolhido, {})
    elif pagina_escolhida and request.args.get("copiar_de", ""):
        # Nova ficha, começando a partir de um NPC genérico (guarda, camponês…) — copia os
        # valores, nunca a foto (não faz sentido reaproveitar o retrato do modelo).
        pagina_origem, slug_origem = _parse_combo_ficha(request.args.get("copiar_de", ""))
        caminho_origem = _resolver_pagina(pagina_origem)
        if caminho_origem is not None:
            valores = dict(wd.ler_statblocks_da_pagina(caminho_origem).get(slug_origem, {}))
            valores.pop("foto", None)

    return render_template(
        "ficha_combate.html",
        paginas=paginas,
        fichas=fichas,
        pagina_escolhida=pagina_escolhida,
        slug_escolhido=slug_escolhido,
        valores=valores,
        campos_texto=wd.CAMPOS_STATBLOCK_TEXTO,
        campos_atributos=wd.CAMPOS_STATBLOCK_ATRIBUTOS,
        rotulos_atributos=wd.ROTULOS_ATRIBUTOS,
        campos_listas=wd.CAMPOS_STATBLOCK_LISTAS,
        pericias_d20=wd.PERICIAS_D20,
        salvaguardas_d20=wd.SALVAGUARDAS_D20,
        campos_inventario_item=wd.CAMPOS_INVENTARIO_ITEM,
        equipado_opcoes=wd.EQUIPADO_OPCOES,
        campos_magia_item=wd.CAMPOS_MAGIA_ITEM,
        campos_caracteristica_item=wd.CAMPOS_CARACTERISTICA_ITEM,
        categorias_caracteristica=wd.CATEGORIAS_CARACTERISTICA,
        campos_efeito_item=wd.CAMPOS_EFEITO_ITEM,
        tipos_efeito=wd.TIPOS_EFEITO,
        copiar_de=request.args.get("copiar_de", ""),
        salvo=False,
    )


def _ler_grupo_do_form(form, prefixo: str, campos: list[tuple]) -> list[dict]:
    """Lê um grupo de linhas repetíveis do formulário (inventário/grimório/características/
    efeitos da ficha completa, ver admin/templates/ficha_combate.html) — cada campo chega como
    uma lista paralela `{prefixo}_{chave}[]`; zipa as listas numa linha por índice e descarta
    linhas sem `nome` preenchido."""
    listas = {chave: form.getlist(f"{prefixo}_{chave}[]") for chave, _, _ in campos}
    tamanho = max((len(v) for v in listas.values()), default=0)
    linhas = []
    for i in range(tamanho):
        linha = {}
        for chave, _, _ in campos:
            valores_campo = listas[chave]
            linha[chave] = (valores_campo[i] if i < len(valores_campo) else "").strip()
        if linha.get("nome"):
            linhas.append(linha)
    return linhas


@app.post("/ficha-combate")
def salvar_ficha_combate():
    paginas = _paginas_ficha_combate()
    pagina_escolhida = request.form.get("pagina", "")
    slug_antigo = request.form.get("slug_antigo", "")
    ancora = request.form.get("ancora", "").strip()

    caminho = _resolver_pagina(pagina_escolhida)
    if caminho is None:
        abort(400)

    valores = {chave: request.form.get(f"campo_{chave}", "").strip() for chave, _, _ in wd.CAMPOS_STATBLOCK_TEXTO}
    for a in wd.CAMPOS_STATBLOCK_ATRIBUTOS:
        valores[a] = request.form.get(f"campo_{a}", "").strip()
    for chave, _ in wd.CAMPOS_STATBLOCK_LISTAS:
        valores[chave] = request.form.get(f"campo_{chave}", "")

    valores["pericias_treino"] = {
        chave: request.form.get(f"pericia_{chave}", "") for chave, _, _ in wd.PERICIAS_D20
    }
    valores["salvaguardas_treino"] = {
        a: bool(request.form.get(f"salva_{a}")) for a, _ in wd.SALVAGUARDAS_D20
    }
    valores["inventario"] = _ler_grupo_do_form(request.form, "inv", wd.CAMPOS_INVENTARIO_ITEM)
    valores["magias_detalhe"] = _ler_grupo_do_form(request.form, "magia", wd.CAMPOS_MAGIA_ITEM)
    valores["caracteristicas"] = _ler_grupo_do_form(request.form, "carac", wd.CAMPOS_CARACTERISTICA_ITEM)
    valores["efeitos"] = _ler_grupo_do_form(request.form, "efeito", wd.CAMPOS_EFEITO_ITEM)

    arquivo_foto = request.files.get("arquivo_foto")
    if arquivo_foto and arquivo_foto.filename:
        valores["foto"] = wd.salvar_foto_statblock(
            ROOT, pagina_escolhida, arquivo_foto.filename, arquivo_foto.read(),
        )

    contexto = dict(
        paginas=paginas, pagina_escolhida=pagina_escolhida, slug_escolhido=slug_antigo,
        valores=valores, campos_texto=wd.CAMPOS_STATBLOCK_TEXTO,
        campos_atributos=wd.CAMPOS_STATBLOCK_ATRIBUTOS, rotulos_atributos=wd.ROTULOS_ATRIBUTOS,
        campos_listas=wd.CAMPOS_STATBLOCK_LISTAS,
        pericias_d20=wd.PERICIAS_D20, salvaguardas_d20=wd.SALVAGUARDAS_D20,
        campos_inventario_item=wd.CAMPOS_INVENTARIO_ITEM, equipado_opcoes=wd.EQUIPADO_OPCOES,
        campos_magia_item=wd.CAMPOS_MAGIA_ITEM,
        campos_caracteristica_item=wd.CAMPOS_CARACTERISTICA_ITEM,
        categorias_caracteristica=wd.CATEGORIAS_CARACTERISTICA,
        campos_efeito_item=wd.CAMPOS_EFEITO_ITEM, tipos_efeito=wd.TIPOS_EFEITO,
    )

    try:
        novo_slug = wd.salvar_statblock(ROOT, pagina_escolhida, slug_antigo, valores, ancora)
    except ValueError as exc:
        fichas = wd.listar_statblocks(ROOT)
        return render_template("ficha_combate.html", fichas=fichas, salvo=False, erro=str(exc), **contexto)

    build_ok, build_saida = wd.publicar_build(ROOT)
    fichas = wd.listar_statblocks(ROOT)
    contexto["slug_escolhido"] = novo_slug
    return render_template(
        "ficha_combate.html", fichas=fichas, salvo=True, build_ok=build_ok, build_saida=build_saida,
        **contexto,
    )


def _itens_da_pagina(caminho):
    return [{"slug": s, "nome": d.get("nome") or s} for s, d in wd.ler_itens_da_pagina(caminho).items()]


@app.get("/ficha-item")
def escolher_ficha_item():
    paginas = wd.listar_todas_paginas(ROOT)
    pagina_escolhida = request.args.get("pagina", "")
    slug_escolhido = request.args.get("item", "")

    itens: list = []
    valores: dict = {}
    if pagina_escolhida:
        caminho = _resolver_pagina(pagina_escolhida)
        if caminho is None:
            abort(404)
        itens = _itens_da_pagina(caminho)
        if slug_escolhido:
            valores = wd.ler_itens_da_pagina(caminho).get(slug_escolhido, {})

    return render_template(
        "ficha_item.html", paginas=paginas, pagina_escolhida=pagina_escolhida, itens=itens,
        slug_escolhido=slug_escolhido, valores=valores, campos=wd.CAMPOS_ITEM_TEXTO,
        lugares=wd.listar_lugares(ROOT), donos=wd.listar_npcs(ROOT) + wd.listar_jogadores(ROOT),
        salvo=False,
    )


@app.post("/ficha-item")
def salvar_ficha_item():
    paginas = wd.listar_todas_paginas(ROOT)
    pagina_escolhida = request.form.get("pagina", "")
    slug_antigo = request.form.get("slug_antigo", "")
    ancora = request.form.get("ancora", "").strip()

    caminho = _resolver_pagina(pagina_escolhida)
    if caminho is None:
        abort(400)

    valores = {chave: request.form.get(f"campo_{chave}", "").strip() for chave, _, _ in wd.CAMPOS_ITEM_TEXTO}
    contexto = dict(
        paginas=paginas, pagina_escolhida=pagina_escolhida, slug_escolhido=slug_antigo, valores=valores,
        campos=wd.CAMPOS_ITEM_TEXTO, lugares=wd.listar_lugares(ROOT),
        donos=wd.listar_npcs(ROOT) + wd.listar_jogadores(ROOT),
    )

    try:
        novo_slug = wd.salvar_item(ROOT, pagina_escolhida, slug_antigo, valores, ancora)
    except ValueError as exc:
        return render_template("ficha_item.html", itens=_itens_da_pagina(caminho), salvo=False, erro=str(exc), **contexto)

    build_ok, build_saida = wd.publicar_build(ROOT)
    contexto["slug_escolhido"] = novo_slug
    return render_template(
        "ficha_item.html", itens=_itens_da_pagina(caminho), salvo=True, build_ok=build_ok,
        build_saida=build_saida, **contexto,
    )


def _combo_ficha(pagina: str, slug: str) -> str:
    return f"{pagina}::{slug}"


def _parse_combo_ficha(valor: str) -> tuple[str, str]:
    if not valor or "::" not in valor:
        return "", ""
    pagina, slug = valor.split("::", 1)
    return pagina, slug


# --------------------------------------------------------------------------
# API JSON de personagens — monstro, NPC nomeado e jogador, unificados desde 2026-10-31 (ver
# admin/banco.py e admin/personagens_api.py; NPCs genéricos, figurantes de sessão e a ficha de
# cidade continuam em Markdown de propósito, ver .claude/contexto/personagens.md). GET é público
# (leitura livre do site); toda escrita exige Modo Mestre (ver _exigir_login acima). Usada pelo
# widget embutido na própria página do personagem (docs/javascripts/ficha.js) — nenhuma dessas
# rotas dispara `mkdocs build`, é por isso que a edição aparece na hora.
# --------------------------------------------------------------------------

_TIPOS_CATALOGO_VALIDOS = {"equipamentos", "habilidades", "magias", "idiomas", "sentidos", "pericias"}


def _tipo_catalogo_valido(tipo: str) -> bool:
    return tipo in _TIPOS_CATALOGO_VALIDOS


def _tipo_ator_valido(tipo: str) -> bool:
    return tipo in banco.TIPOS_ATOR


def _erro_json(mensagem: str, status: int = 404):
    return jsonify(erro=mensagem), status


@app.get("/api/personagens/<tipo>/<slug>")
def api_ver_personagem(tipo, slug):
    if not _tipo_ator_valido(tipo):
        return _erro_json("Tipo de personagem desconhecido.")
    with SessaoBanco() as sessao:
        personagem = ma.obter_personagem(sessao, tipo, slug)
        if personagem is None:
            return _erro_json("Personagem não encontrado.")
        return jsonify(ma.serializar_personagem(personagem))


@app.put("/api/personagens/<tipo>/<slug>")
def api_atualizar_personagem(tipo, slug):
    if not _tipo_ator_valido(tipo):
        return _erro_json("Tipo de personagem desconhecido.")
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        personagem = ma.obter_personagem(sessao, tipo, slug)
        if personagem is None:
            return _erro_json("Personagem não encontrado.")
        ma.atualizar_personagem(sessao, personagem, dados)
        return jsonify(ma.serializar_personagem(personagem))


@app.get("/api/catalogo/<tipo>")
def api_listar_catalogo(tipo):
    if not _tipo_catalogo_valido(tipo):
        return _erro_json("Catálogo desconhecido.")
    with SessaoBanco() as sessao:
        itens = ma.listar_catalogo(
            sessao, tipo,
            busca=request.args.get("busca", ""), categoria=request.args.get("categoria", ""),
            origem_personagem=request.args.get("origem_personagem", ""),
        )
        return jsonify(itens=itens)


@app.post("/api/catalogo/<tipo>")
def api_criar_item_catalogo(tipo):
    if not _tipo_catalogo_valido(tipo):
        return _erro_json("Catálogo desconhecido.")
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        try:
            item = ma.criar_item_catalogo(sessao, tipo, dados)
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(item)


@app.post("/api/personagens/<tipo>/<slug>/fichas")
def api_criar_variante(tipo, slug):
    if not _tipo_ator_valido(tipo):
        return _erro_json("Tipo de personagem desconhecido.")
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        personagem = ma.obter_personagem(sessao, tipo, slug)
        if personagem is None:
            return _erro_json("Personagem não encontrado.")
        try:
            ma.criar_variante(sessao, personagem, dados.get("rotulo", ""))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ma.obter_personagem(sessao, tipo, slug)))


@app.put("/api/personagens/<tipo>/<slug>/fichas/<int:ficha_id>")
def api_salvar_ficha(tipo, slug, ficha_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None or ficha.personagem.slug != slug or ficha.personagem.tipo != tipo:
            return _erro_json("Ficha não encontrada.")
        ma.atualizar_ficha(sessao, ficha, dados)
        return jsonify(ma.serializar_personagem(ma.obter_personagem(sessao, tipo, slug)))


@app.delete("/api/personagens/<tipo>/<slug>/fichas/<int:ficha_id>")
def api_excluir_ficha(tipo, slug, ficha_id):
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None or ficha.personagem.slug != slug or ficha.personagem.tipo != tipo:
            return _erro_json("Ficha não encontrada.")
        try:
            ma.excluir_ficha(sessao, ficha)
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ma.obter_personagem(sessao, tipo, slug)))


@app.post("/api/fichas/<int:ficha_id>/<tipo>")
def api_adicionar_vinculo(ficha_id, tipo):
    if not _tipo_catalogo_valido(tipo):
        return _erro_json("Catálogo desconhecido.")
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        item_id = dados.get("item_id")
        if not item_id:
            return _erro_json("Informe item_id.", 400)
        try:
            ma.adicionar_vinculo(sessao, ficha, tipo, int(item_id), dados)
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.delete("/api/fichas/<int:ficha_id>/<tipo>/<int:vinculo_id>")
def api_remover_vinculo(ficha_id, tipo, vinculo_id):
    if not _tipo_catalogo_valido(tipo):
        return _erro_json("Catálogo desconhecido.")
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        personagem = ficha.personagem
        ma.remover_vinculo(sessao, tipo, vinculo_id)
        return jsonify(ma.serializar_personagem(personagem))


@app.put("/api/fichas/<int:ficha_id>/<tipo>/<int:vinculo_id>/favorito")
def api_alternar_favorito_vinculo(ficha_id, tipo, vinculo_id):
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        try:
            ma.alternar_favorito_vinculo(sessao, tipo, vinculo_id)
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.put("/api/fichas/<int:ficha_id>/habilidades/<int:vinculo_id>/usos")
def api_definir_usos_habilidade(ficha_id, vinculo_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        try:
            ma.definir_usos_habilidade(sessao, vinculo_id, dados)
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.post("/api/fichas/<int:ficha_id>/habilidades/<int:vinculo_id>/usar")
def api_consumir_uso_habilidade(ficha_id, vinculo_id):
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        try:
            ma.consumir_uso_habilidade(sessao, vinculo_id)
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.post("/api/fichas/<int:ficha_id>/resistencias-dano")
def api_alternar_resistencia_dano(ficha_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        try:
            ma.alternar_resistencia_dano(sessao, ficha, dados.get("nome", ""), dados.get("modo", ""))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.put("/api/fichas/<int:ficha_id>/sentidos/<int:vinculo_id>")
def api_atualizar_valor_sentido(ficha_id, vinculo_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        try:
            ma.atualizar_valor_sentido(sessao, vinculo_id, dados.get("valor", ""))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.put("/api/fichas/<int:ficha_id>/pericias/<int:vinculo_id>")
def api_atualizar_bonus_pericia(ficha_id, vinculo_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        try:
            ma.atualizar_bonus_pericia(sessao, vinculo_id, dados.get("bonus", 0))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.post("/api/fichas/<int:ficha_id>/espacos-magia")
def api_criar_espaco_magia(ficha_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        ma.criar_espaco_magia(sessao, ficha, dados)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.put("/api/fichas/<int:ficha_id>/espacos-magia/<int:vinculo_id>")
def api_atualizar_espaco_magia(ficha_id, vinculo_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        try:
            ma.atualizar_espaco_magia(sessao, vinculo_id, dados)
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.delete("/api/fichas/<int:ficha_id>/espacos-magia/<int:vinculo_id>")
def api_remover_espaco_magia(ficha_id, vinculo_id):
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        ma.remover_espaco_magia(sessao, vinculo_id)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.post("/api/fichas/<int:ficha_id>/condicoes")
def api_adicionar_condicao(ficha_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        try:
            ma.adicionar_condicao(sessao, ficha, dados.get("nome", ""))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.delete("/api/fichas/<int:ficha_id>/condicoes/<int:vinculo_id>")
def api_remover_condicao(ficha_id, vinculo_id):
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        ma.remover_condicao(sessao, vinculo_id)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.post("/api/fichas/<int:ficha_id>/efeitos")
def api_criar_efeito(ficha_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        try:
            ma.criar_efeito(sessao, ficha, dados)
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.put("/api/fichas/<int:ficha_id>/efeitos/<int:vinculo_id>")
def api_atualizar_efeito(ficha_id, vinculo_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        try:
            ma.atualizar_efeito(sessao, vinculo_id, dados)
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.delete("/api/fichas/<int:ficha_id>/efeitos/<int:vinculo_id>")
def api_remover_efeito(ficha_id, vinculo_id):
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None:
            return _erro_json("Ficha não encontrada.")
        ma.remover_efeito(sessao, vinculo_id)
        return jsonify(ma.serializar_personagem(ficha.personagem))


@app.post("/api/personagens/<tipo>/<slug>/diario")
def api_criar_entrada_diario(tipo, slug):
    if not _tipo_ator_valido(tipo):
        return _erro_json("Tipo de personagem desconhecido.")
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        personagem = ma.obter_personagem(sessao, tipo, slug)
        if personagem is None:
            return _erro_json("Personagem não encontrado.")
        ma.criar_entrada_diario(sessao, personagem, dados)
        return jsonify(ma.serializar_personagem(personagem))


@app.put("/api/personagens/<tipo>/<slug>/diario/<int:vinculo_id>")
def api_atualizar_entrada_diario(tipo, slug, vinculo_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        personagem = ma.obter_personagem(sessao, tipo, slug)
        if personagem is None:
            return _erro_json("Personagem não encontrado.")
        try:
            ma.atualizar_entrada_diario(sessao, vinculo_id, dados)
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(personagem))


@app.delete("/api/personagens/<tipo>/<slug>/diario/<int:vinculo_id>")
def api_remover_entrada_diario(tipo, slug, vinculo_id):
    with SessaoBanco() as sessao:
        personagem = ma.obter_personagem(sessao, tipo, slug)
        if personagem is None:
            return _erro_json("Personagem não encontrado.")
        ma.remover_entrada_diario(sessao, vinculo_id)
        return jsonify(ma.serializar_personagem(personagem))


@app.post("/api/personagens/<tipo>/<slug>/foto")
def api_salvar_foto_personagem(tipo, slug):
    if not _tipo_ator_valido(tipo):
        return _erro_json("Tipo de personagem desconhecido.")
    arquivo = request.files.get("foto")
    if not arquivo or not arquivo.filename:
        return _erro_json("Envie um arquivo de imagem.", 400)
    with SessaoBanco() as sessao:
        personagem = ma.obter_personagem(sessao, tipo, slug)
        if personagem is None:
            return _erro_json("Personagem não encontrado.")
        try:
            ma.salvar_foto_personagem(ROOT, sessao, personagem, arquivo.filename, arquivo.read())
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(ma.serializar_personagem(personagem))


@app.delete("/api/personagens/<tipo>/<slug>/foto")
def api_apagar_foto_personagem(tipo, slug):
    if not _tipo_ator_valido(tipo):
        return _erro_json("Tipo de personagem desconhecido.")
    with SessaoBanco() as sessao:
        personagem = ma.obter_personagem(sessao, tipo, slug)
        if personagem is None:
            return _erro_json("Personagem não encontrado.")
        ma.apagar_foto_personagem(ROOT, sessao, personagem)
        return jsonify(ma.serializar_personagem(personagem))


@app.post("/api/personagens/<tipo>/<slug>/fichas/<int:ficha_id>/descanso-longo")
def api_descanso_longo(tipo, slug, ficha_id):
    if tipo not in ("npc", "jogador"):
        return _erro_json("Descanso longo só se aplica a NPC nomeado ou jogador.", 400)
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None or ficha.personagem.slug != slug or ficha.personagem.tipo != tipo:
            return _erro_json("Ficha não encontrada.")
        ma.descanso_longo(sessao, ficha)
        return jsonify(ma.serializar_personagem(ma.obter_personagem(sessao, tipo, slug)))


@app.post("/api/personagens/<tipo>/<slug>/fichas/<int:ficha_id>/descanso-curto")
def api_descanso_curto(tipo, slug, ficha_id):
    if tipo not in ("npc", "jogador"):
        return _erro_json("Descanso curto só se aplica a NPC nomeado ou jogador.", 400)
    with SessaoBanco() as sessao:
        ficha = ma.obter_ficha(sessao, ficha_id)
        if ficha is None or ficha.personagem.slug != slug or ficha.personagem.tipo != tipo:
            return _erro_json("Ficha não encontrada.")
        ma.descanso_curto(sessao, ficha)
        return jsonify(ma.serializar_personagem(ma.obter_personagem(sessao, tipo, slug)))


@app.get("/api/personagens-busca")
def api_buscar_personagens():
    with SessaoBanco() as sessao:
        itens = ma.buscar_personagens(
            sessao, tipo=request.args.get("tipo") or None, busca=request.args.get("q", ""),
        )
        return jsonify(itens=itens)


# --------------------------------------------------------------------------
# API JSON do Combat Tracker (ver admin/banco.py: Combate/CombateParticipante/.../
# admin/combate_api.py) — substitui o antigo Painel de Iniciativa (sessao_viva.py). GET é público
# (leitura livre do site, ver _PREFIXOS_API_LEITURA_LIVRE); toda escrita exige Modo Mestre. Usada
# pela aba "Combat Tracker" das páginas de sessão (docs/javascripts/combate.js).
# --------------------------------------------------------------------------

def _combate_json(combate):
    return jsonify(combate=ca.serializar_combate(combate))


@app.get("/api/combate/<path:pagina>")
def api_ver_combate(pagina):
    with SessaoBanco() as sessao:
        combate = ca.obter_combate_ativo(sessao, pagina)
        if combate is None:
            return jsonify(combate=None)
        return _combate_json(combate)


@app.post("/api/combate/<path:pagina>/iniciar")
def api_iniciar_combate(pagina):
    with SessaoBanco() as sessao:
        combate = ca.iniciar_combate(sessao, pagina)
        return _combate_json(combate)


@app.post("/api/combate/<int:combate_id>/encerrar")
def api_encerrar_combate(combate_id):
    with SessaoBanco() as sessao:
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        ca.encerrar_combate(sessao, combate)
        return _combate_json(combate)


@app.post("/api/combate/<int:combate_id>/participantes")
def api_adicionar_participante(combate_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        try:
            ca.adicionar_participante(
                sessao, combate, int(dados.get("ficha_id")),
                dados.get("nome_exibicao"), dados.get("iniciativa_base", 0),
            )
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return _combate_json(ca.obter_combate(sessao, combate_id))


@app.delete("/api/combate/<int:combate_id>/participantes/<int:participante_id>")
def api_remover_participante(combate_id, participante_id):
    with SessaoBanco() as sessao:
        ca.remover_participante(sessao, participante_id)
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        return _combate_json(combate)


@app.put("/api/combate/<int:combate_id>/participantes/<int:participante_id>/iniciativa")
def api_atualizar_iniciativa(combate_id, participante_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        try:
            ca.atualizar_iniciativa(sessao, participante_id, dados.get("base"), dados.get("desempate"))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        return _combate_json(combate)


@app.post("/api/combate/<int:combate_id>/participantes/<int:participante_id>/pv")
def api_ajustar_pv_combate(combate_id, participante_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        try:
            ca.ajustar_pv(sessao, participante_id, dados.get("delta", 0), bool(dados.get("cura")))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        return _combate_json(combate)


@app.put("/api/combate/<int:combate_id>/participantes/<int:participante_id>/pv-temporario")
def api_definir_pv_temporario(combate_id, participante_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        try:
            ca.definir_pv_temporario(sessao, participante_id, dados.get("valor", 0))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        return _combate_json(combate)


@app.post("/api/combate/<int:combate_id>/participantes/<int:participante_id>/condicoes")
def api_alternar_condicao(combate_id, participante_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        try:
            ca.alternar_condicao(sessao, participante_id, dados.get("nome", ""))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        return _combate_json(combate)


@app.put("/api/combate/<int:combate_id>/participantes/<int:participante_id>/concentracao")
def api_definir_concentracao(combate_id, participante_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        ca.definir_concentracao(sessao, participante_id, dados.get("nome"))
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        return _combate_json(combate)


@app.post("/api/combate/<int:combate_id>/participantes/<int:participante_id>/economia-acao")
def api_alternar_economia_acao(combate_id, participante_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        try:
            ca.alternar_economia_acao(sessao, participante_id, dados.get("campo", ""))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        return _combate_json(combate)


@app.post("/api/combate/<int:combate_id>/participantes/<int:participante_id>/reacao")
def api_oferecer_reacao(combate_id, participante_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        try:
            resultado = ca.oferecer_reacao(sessao, participante_id, dados.get("rotulo", ""))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        return jsonify(combate=ca.serializar_combate(combate), ultima_reacao=resultado)


@app.post("/api/combate/<int:combate_id>/participantes/<int:participante_id>/teste-morte")
def api_rolar_teste_morte(combate_id, participante_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        try:
            resultado = ca.rolar_teste_morte(sessao, participante_id, dados.get("d20", 10))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        return jsonify(combate=ca.serializar_combate(combate), ultimo_teste_morte=resultado)


@app.post("/api/combate/<int:combate_id>/turno/proximo")
def api_proximo_turno_combate(combate_id):
    with SessaoBanco() as sessao:
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        ca.proximo_turno(sessao, combate)
        return _combate_json(ca.obter_combate(sessao, combate_id))


@app.post("/api/combate/<int:combate_id>/ataque")
def api_resolver_ataque(combate_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        resultado = ca.resolver_ataque(
            sessao, combate, [int(a) for a in dados.get("alvos", [])],
            dados.get("d20", 10), dados.get("bonus", 0), dados.get("dano", 0),
            bool(dados.get("cura")),
        )
        return jsonify(combate=ca.serializar_combate(ca.obter_combate(sessao, combate_id)), ultimo_ataque=resultado)


@app.post("/api/combate/<int:combate_id>/resistencia")
def api_resolver_resistencia(combate_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        resultado = ca.resolver_resistencia(
            sessao, dados.get("cd", 10), bool(dados.get("meio_no_sucesso", True)),
            dados.get("condicao_no_erro"), dados.get("alvos", []),
        )
        return jsonify(combate=ca.serializar_combate(ca.obter_combate(sessao, combate_id)), ultima_resistencia=resultado)


@app.post("/api/combate/<int:combate_id>/participantes/<int:participante_id>/concentracao/teste")
def api_checar_concentracao(combate_id, participante_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        resultado = ca.checar_concentracao(
            sessao, participante_id, dados.get("d20", 10), dados.get("bonus", 0), dados.get("dano", 0),
        )
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        return jsonify(combate=ca.serializar_combate(combate), ultima_concentracao=resultado)


@app.post("/api/combate/<int:combate_id>/log")
def api_registrar_log(combate_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        ca.registrar_log(sessao, combate, dados.get("texto", ""), dados.get("tipo"))
        return _combate_json(ca.obter_combate(sessao, combate_id))


@app.get("/api/combate/<int:combate_id>/log/exportar")
def api_exportar_log(combate_id):
    formato = request.args.get("formato", "txt")
    with SessaoBanco() as sessao:
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        conteudo = ca.exportar_log(combate, formato)
        tipo_mime = "application/json" if formato == "json" else "text/plain"
        return conteudo, 200, {"Content-Type": f"{tipo_mime}; charset=utf-8"}


@app.get("/api/combate/<int:combate_id>/resumo")
def api_resumo_pos_combate(combate_id):
    with SessaoBanco() as sessao:
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        return jsonify(xp=ca.calcular_resumo_xp(combate), loot=ca.compilar_loot(combate))


@app.post("/api/combate/<int:combate_id>/distribuir-xp")
def api_distribuir_xp(combate_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        ca.distribuir_xp(sessao, combate, dados.get("xp_por_jogador", 0))
        return jsonify(ok=True)


@app.post("/api/combate/<int:combate_id>/aplicar-loot")
def api_aplicar_loot(combate_id):
    dados = request.get_json(silent=True) or {}
    with SessaoBanco() as sessao:
        combate = ca.obter_combate(sessao, combate_id)
        if combate is None:
            return _erro_json("Combate não encontrado.")
        try:
            resultado = ca.aplicar_loot(sessao, combate, dados.get("escolhas", []))
        except ValueError as exc:
            return _erro_json(str(exc), 400)
        return jsonify(resultado)


# --------------------------------------------------------------------------
# API JSON de criação/listagem de entidades — usada pelos widgets embutidos direto nas páginas
# do site (docs/personagens/index.md, docs/lugares/index.md, docs/mestre/jogadores/index.md),
# para não precisar mais abrir o Painel em outra aba. As rotas HTML abaixo (/npc/novo etc.)
# continuam existindo, como caminho manual de reserva.
# --------------------------------------------------------------------------

@app.get("/api/npcs")
def api_listar_npcs():
    return jsonify(itens=wd.listar_npcs_detalhado(ROOT))


@app.get("/api/npcs/genericos")
def api_listar_npcs_genericos():
    return jsonify(itens=wd.listar_npcs_genericos_detalhado(ROOT))


@app.post("/api/npcs")
def api_criar_npc():
    valores = {chave: request.form.get(chave, "") for chave, _, _ in wd.CAMPOS_NPC_NOVO}
    valores["descricao"] = request.form.get("descricao", "")
    generico = request.form.get("generico") in ("on", "true", "1")
    arquivo = request.files.get("imagem")
    imagem = (arquivo.filename, arquivo.read()) if arquivo and arquivo.filename else None
    try:
        r = wd.criar_npc(ROOT, valores, imagem, generico=generico)
    except ValueError as exc:
        return _erro_json(str(exc), 400)
    return jsonify(r)


@app.get("/api/lugares")
def api_listar_lugares():
    return jsonify(itens=wd.listar_lugares_detalhado(ROOT))


@app.post("/api/lugares")
def api_criar_lugar():
    valores = {chave: request.form.get(chave, "") for chave, _, _ in wd.CAMPOS_LUGAR_NOVO}
    valores["descricao"] = request.form.get("descricao", "")
    try:
        r = wd.criar_lugar(ROOT, valores)
    except ValueError as exc:
        return _erro_json(str(exc), 400)
    return jsonify(r)


@app.get("/api/jogadores")
def api_listar_jogadores():
    return jsonify(itens=wd.listar_jogadores_detalhado(ROOT))


@app.post("/api/jogadores")
def api_criar_jogador():
    valores = {chave: request.form.get(chave, "") for chave, _, _ in wd.CAMPOS_JOGADOR_NOVO}
    try:
        r = wd.criar_jogador(ROOT, valores)
    except ValueError as exc:
        return _erro_json(str(exc), 400)
    return jsonify(r)


@app.get("/api/sessoes/proxima-numero")
def api_proxima_sessao():
    return jsonify(numero=wd.proxima_sessao_preparo(ROOT))


@app.post("/api/sessoes/nova")
def api_criar_sessao():
    corpo = request.get_json(silent=True) or {}
    valores = {chave: (corpo.get("campos") or {}).get(chave, "") for chave, _ in wd.CAMPOS_SESSAO_NOVA}
    valores["resumo"] = corpo.get("resumo", "")
    titulo = corpo.get("titulo", "")
    try:
        numero = int(corpo.get("numero"))
    except (TypeError, ValueError):
        return _erro_json("Número de sessão inválido.", 400)
    try:
        r = wd.criar_sessao_preparo(
            ROOT, numero, titulo, valores,
            npcs=corpo.get("npcs") or [], jogadores=corpo.get("jogadores") or [],
            lugares=corpo.get("lugares") or [], prompt=corpo.get("prompt") or "",
        )
    except ValueError as exc:
        return _erro_json(str(exc), 400)
    return jsonify(r)


# --------------------------------------------------------------------------
# Botões do site: "Adicionar NPC" (tabela de NPCs) e "Nova sessão" (Mestre → Sessões)
# --------------------------------------------------------------------------

@app.get("/npc/novo")
def formulario_npc():
    return render_template(
        "npc_novo.html", campos=wd.CAMPOS_NPC_NOVO, valores={},
        cidades=wd.listar_cidades(ROOT), faccoes=wd.listar_faccoes(ROOT),
    )


@app.post("/npc/novo")
def criar_npc():
    valores = {chave: request.form.get(chave, "") for chave, _, _ in wd.CAMPOS_NPC_NOVO}
    valores["descricao"] = request.form.get("descricao", "")
    generico = request.form.get("generico") == "on"
    arquivo = request.files.get("imagem")
    imagem = (arquivo.filename, arquivo.read()) if arquivo and arquivo.filename else None
    try:
        r = wd.criar_npc(ROOT, valores, imagem, generico=generico)
    except ValueError as exc:
        return render_template(
            "npc_novo.html", campos=wd.CAMPOS_NPC_NOVO, valores={**valores, **request.form.to_dict()},
            erro=str(exc), cidades=wd.listar_cidades(ROOT), faccoes=wd.listar_faccoes(ROOT),
        )
    return render_template(
        "resultado_criacao.html", r=r, titulo_pagina=f"NPC criado: {valores['nome'].strip()}",
        voltar_url="/npc/novo", voltar_rotulo="Adicionar outro NPC",
    )


@app.get("/npc/retrato")
def formulario_retrato():
    return render_template("npc_retrato.html", npcs=wd.listar_npcs(ROOT), escolhido=request.args.get("npc", ""))


@app.post("/npc/retrato")
def salvar_retrato():
    escolhido = request.form.get("npc", "")
    arquivo = request.files.get("imagem")
    contexto = dict(npcs=wd.listar_npcs(ROOT), escolhido=escolhido)
    if _resolver_pagina(escolhido) is None or not escolhido.startswith("personagens/"):
        return render_template("npc_retrato.html", erro="Escolha um NPC da lista.", **contexto)
    if arquivo is None or not arquivo.filename:
        return render_template("npc_retrato.html", erro="Escolha um arquivo de imagem.", **contexto)
    try:
        retrato = wd.definir_retrato(ROOT, escolhido, arquivo.filename, arquivo.read())
    except ValueError as exc:
        return render_template("npc_retrato.html", erro=str(exc), **contexto)
    return render_template("npc_retrato.html", salvo=retrato, **contexto)


@app.get("/lugar/novo")
def formulario_lugar():
    return render_template(
        "lugar_novo.html", campos=wd.CAMPOS_LUGAR_NOVO, valores={}, cidades=wd.listar_cidades(ROOT),
    )


@app.post("/lugar/novo")
def criar_lugar():
    valores = {chave: request.form.get(chave, "") for chave, _, _ in wd.CAMPOS_LUGAR_NOVO}
    valores["descricao"] = request.form.get("descricao", "")
    try:
        r = wd.criar_lugar(ROOT, valores)
    except ValueError as exc:
        return render_template(
            "lugar_novo.html", campos=wd.CAMPOS_LUGAR_NOVO, valores={**valores, **request.form.to_dict()},
            erro=str(exc), cidades=wd.listar_cidades(ROOT),
        )
    return render_template(
        "resultado_criacao.html", r=r, titulo_pagina=f"Lugar criado: {valores['nome'].strip()}",
        voltar_url="/lugar/novo", voltar_rotulo="Adicionar outro lugar",
    )


@app.get("/jogador/novo")
def formulario_jogador():
    return render_template("jogador_novo.html", campos=wd.CAMPOS_JOGADOR_NOVO, valores={})


@app.post("/jogador/novo")
def criar_jogador():
    valores = {chave: request.form.get(chave, "") for chave, _, _ in wd.CAMPOS_JOGADOR_NOVO}
    try:
        r = wd.criar_jogador(ROOT, valores)
    except ValueError as exc:
        return render_template(
            "jogador_novo.html", campos=wd.CAMPOS_JOGADOR_NOVO,
            valores={**valores, **request.form.to_dict()}, erro=str(exc),
        )
    return render_template(
        "resultado_criacao.html", r=r, titulo_pagina=f"Jogador criado: {valores['nome'].strip()}",
        voltar_url="/jogador/novo", voltar_rotulo="Adicionar outro jogador",
    )


# --------------------------------------------------------------------------
# Gerador de NPCs — NPC genérico (nome, raça, papel, equipamento, ficha de combate completa) a
# partir de filtros e/ou um prompt em texto livre. Ver admin/gerador_npc.py: é só tabelas
# aleatórias locais, sem chamada a nenhuma IA/API.
# --------------------------------------------------------------------------

@app.get("/npc/gerador")
def formulario_gerador_npc():
    return render_template(
        "npc_gerador.html", racas=[gn.ALEATORIO] + gn.RACAS,
        papeis=[gn.ALEATORIO] + list(gn.PAPEIS.keys()), niveis=[gn.ALEATORIO] + gn.NIVEIS_POTENCIA,
    )


@app.post("/npc/gerador")
def gerar_npc_rota():
    raca = request.form.get("raca", gn.ALEATORIO)
    papel = request.form.get("papel", gn.ALEATORIO)
    nivel = request.form.get("nivel_potencia", gn.ALEATORIO)
    prompt = request.form.get("prompt", "")
    contexto_form = dict(
        racas=[gn.ALEATORIO] + gn.RACAS, papeis=[gn.ALEATORIO] + list(gn.PAPEIS.keys()),
        niveis=[gn.ALEATORIO] + gn.NIVEIS_POTENCIA, raca=raca, papel=papel, nivel=nivel, prompt=prompt,
    )

    gerado = gn.gerar_npc(raca, papel, nivel, prompt)
    try:
        r = wd.criar_npc(ROOT, gerado["npc"], imagem=None, generico=True, build=False)
    except ValueError as exc:
        return render_template("npc_gerador.html", erro=str(exc), **contexto_form)

    wd.salvar_statblock(ROOT, r["rel_docs"], "", gerado["statblock"], "")
    build_ok, build_saida = wd.publicar_build(ROOT)
    r["build_ok"], r["build_saida"] = build_ok, build_saida

    return render_template(
        "resultado_criacao.html", r=r, titulo_pagina=f"NPC gerado: {gerado['npc']['nome']}",
        voltar_url="/npc/gerador", voltar_rotulo="Gerar outro NPC",
    )


@app.get("/sessoes/participantes")
def formulario_participantes():
    pagina = request.args.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    atuais = wd.ler_participantes(ROOT, pagina)
    return render_template(
        "sessao_participantes.html", pagina=pagina, jogadores=wd.listar_jogadores(ROOT),
        npcs=wd.listar_npcs(ROOT), atuais=atuais,
    )


@app.post("/sessoes/participantes")
def salvar_participantes():
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    jogadores = request.form.getlist("jogadores")
    npcs = request.form.getlist("npcs")
    wd.salvar_participantes(ROOT, pagina, jogadores, npcs)
    return render_template(
        "sessao_participantes.html", pagina=pagina, jogadores=wd.listar_jogadores(ROOT),
        npcs=wd.listar_npcs(ROOT), atuais={"jogadores": jogadores, "npcs": npcs}, salvo=True,
    )


@app.get("/sessoes/nova")
def formulario_sessao_nova():
    return render_template(
        "sessao_nova.html", numero=wd.proxima_sessao_preparo(ROOT), campos=wd.CAMPOS_SESSAO_NOVA, valores={},
    )


@app.post("/sessoes/nova")
def criar_sessao_nova():
    valores = {chave: request.form.get(chave, "") for chave, _ in wd.CAMPOS_SESSAO_NOVA}
    valores["titulo"] = request.form.get("titulo", "")
    valores["resumo"] = request.form.get("resumo", "")
    try:
        numero = int(request.form.get("numero", ""))
        r = wd.criar_sessao_preparo(ROOT, numero, valores["titulo"], valores)
    except ValueError as exc:
        return render_template(
            "sessao_nova.html", numero=request.form.get("numero", ""), campos=wd.CAMPOS_SESSAO_NOVA,
            valores=valores, erro=str(exc) if "invalid literal" not in str(exc) else "Número de sessão inválido.",
        )
    return render_template(
        "resultado_criacao.html", r=r, titulo_pagina=f"Sessão {numero} criada",
        voltar_url="/sessoes/nova", voltar_rotulo="Criar outra sessão",
    )


# --------------------------------------------------------------------------
# Linha do tempo
# --------------------------------------------------------------------------

LINHAS_MUDANCA = 6  # quantas linhas de "mudança de estado" o formulário mostra


def _contexto_linha_tempo(**extra):
    return dict(
        eventos=wd.listar_eventos(ROOT), npcs=wd.listar_npcs(ROOT), cidades=wd.listar_cidades(ROOT),
        faccoes=wd.listar_faccoes(ROOT), campos_mudanca=wd.linha_tempo.CAMPOS_MUDANCA,
        linhas_mudanca=LINHAS_MUDANCA, **extra,
    )


@app.get("/linha-do-tempo")
def formulario_linha_tempo():
    editar = request.args.get("editar", type=int)
    evento = next((e for e in wd.listar_eventos(ROOT) if int(e.get("id") or 0) == editar), None) if editar else None
    return render_template("linha_tempo.html", **_contexto_linha_tempo(evento=evento or {}))


@app.post("/linha-do-tempo")
def salvar_linha_tempo():
    id_evento = request.form.get("id", type=int)
    sessao = request.form.get("sessao", "").strip()
    mudancas = []
    for i in range(LINHAS_MUDANCA):
        pagina = request.form.get(f"mudanca_pagina_{i}", "")
        campo = request.form.get(f"mudanca_campo_{i}", "")
        valor = request.form.get(f"mudanca_valor_{i}", "").strip()
        if pagina and campo and valor:
            mudancas.append({"pagina": pagina, "campo": campo, "valor": valor})
    anterior = next((e for e in wd.listar_eventos(ROOT) if int(e.get("id") or 0) == id_evento), {}) if id_evento else {}
    dados = {
        "data": request.form.get("data", "").strip(),
        "sessao": int(sessao) if sessao.lstrip("-").isdigit() else None,
        "titulo": request.form.get("titulo", "").strip(),
        "descricao": request.form.get("descricao", "").strip(),
        "envolvidos": request.form.getlist("envolvido"),
        "notas": anterior.get("notas"),
        "mudancas": mudancas,
    }
    try:
        novo_id = wd.salvar_evento(ROOT, dados, id_evento)
    except ValueError as exc:
        return render_template("linha_tempo.html", **_contexto_linha_tempo(evento={**dados, "id": id_evento}, erro=str(exc)))
    build_ok, build_saida = wd.publicar_build(ROOT)
    return render_template(
        "linha_tempo.html",
        **_contexto_linha_tempo(evento={}, salvo=novo_id, build_ok=build_ok, build_saida=build_saida),
    )


@app.post("/linha-do-tempo/apagar")
def apagar_linha_tempo():
    id_evento = request.form.get("id", type=int)
    if id_evento:
        wd.apagar_evento(ROOT, id_evento)
    return redirect(url_for("formulario_linha_tempo"))


# --------------------------------------------------------------------------
# Changelog
# --------------------------------------------------------------------------

@app.get("/changelog")
def formulario_changelog():
    return render_template(
        "changelog.html", versoes=list(reversed(wd.listar_changelog(ROOT))),
        hoje=datetime.date.today().isoformat(),
    )


@app.post("/changelog")
def salvar_changelog():
    versao = request.form.get("versao", "")
    data = request.form.get("data", "") or datetime.date.today().isoformat()
    mudancas = [l for l in request.form.get("mudancas", "").splitlines()]
    try:
        novo_id = wd.adicionar_versao_changelog(ROOT, versao, data, mudancas)
    except ValueError as exc:
        return render_template(
            "changelog.html", versoes=list(reversed(wd.listar_changelog(ROOT))), erro=str(exc),
        )
    build_ok, build_saida = wd.publicar_build(ROOT)
    return render_template(
        "changelog.html", versoes=list(reversed(wd.listar_changelog(ROOT))), salvo=novo_id,
        build_ok=build_ok, build_saida=build_saida,
    )


@app.post("/changelog/apagar")
def apagar_changelog():
    id_versao = request.form.get("id", type=int)
    if id_versao:
        wd.apagar_versao_changelog(ROOT, id_versao)
        wd.publicar_build(ROOT)
    return redirect(url_for("formulario_changelog"))


# --------------------------------------------------------------------------
# Roadmap — API JSON (leitura livre; criar/editar/excluir exige Modo Mestre, ver
# _exigir_login/_PREFIXOS_API_LEITURA_LIVRE acima). Usada pelo widget embutido na própria página
# pública do Roadmap (docs/javascripts/roadmap.js) — o formulário HTML abaixo (/roadmap) continua
# funcionando em paralelo, lendo/escrevendo o mesmo dados/roadmap.yml.
# --------------------------------------------------------------------------

@app.get("/api/roadmap")
def api_listar_roadmap():
    return jsonify(
        itens=wd.listar_roadmap(ROOT),
        prioridades=roadmap.PRIORIDADES, tipos=roadmap.TIPOS, status_opcoes=roadmap.STATUS,
    )


@app.post("/api/roadmap")
def api_criar_item_roadmap():
    dados = request.get_json(silent=True) or {}
    try:
        novo_id = wd.salvar_item_roadmap(ROOT, dados)
    except ValueError as exc:
        return _erro_json(str(exc), 400)
    return jsonify(itens=wd.listar_roadmap(ROOT), id=novo_id)


@app.put("/api/roadmap/<int:id_item>")
def api_editar_item_roadmap(id_item):
    dados = request.get_json(silent=True) or {}
    if not any(int(i.get("id") or 0) == id_item for i in wd.listar_roadmap(ROOT)):
        return _erro_json("Item não encontrado.")
    try:
        wd.salvar_item_roadmap(ROOT, dados, id_item)
    except ValueError as exc:
        return _erro_json(str(exc), 400)
    return jsonify(itens=wd.listar_roadmap(ROOT))


@app.delete("/api/roadmap/<int:id_item>")
def api_apagar_item_roadmap(id_item):
    if not any(int(i.get("id") or 0) == id_item for i in wd.listar_roadmap(ROOT)):
        return _erro_json("Item não encontrado.")
    wd.apagar_item_roadmap(ROOT, id_item)
    return jsonify(itens=wd.listar_roadmap(ROOT))


# --------------------------------------------------------------------------
# Roadmap — formulário HTML (Painel do Mestre)
# --------------------------------------------------------------------------

def _contexto_roadmap(**extra):
    return dict(
        itens=wd.listar_roadmap(ROOT), prioridades=roadmap.PRIORIDADES,
        tipos=roadmap.TIPOS, status_opcoes=roadmap.STATUS, **extra,
    )


@app.get("/roadmap")
def formulario_roadmap():
    editar = request.args.get("editar", type=int)
    item = next((i for i in wd.listar_roadmap(ROOT) if int(i.get("id") or 0) == editar), None) if editar else None
    return render_template("roadmap.html", **_contexto_roadmap(item=item or {}))


@app.post("/roadmap")
def salvar_roadmap():
    id_item = request.form.get("id", type=int)
    dados = {
        "item": request.form.get("item", "").strip(),
        "prioridade": request.form.get("prioridade", ""),
        "tipo": request.form.get("tipo", ""),
        "status": request.form.get("status", ""),
        "responsavel": request.form.get("responsavel", "").strip(),
    }
    try:
        novo_id = wd.salvar_item_roadmap(ROOT, dados, id_item)
    except ValueError as exc:
        return render_template("roadmap.html", **_contexto_roadmap(item={**dados, "id": id_item}, erro=str(exc)))
    # Sem rebuild: a página pública do Roadmap lê os itens em runtime pela API (ver
    # docs/javascripts/roadmap.js), não mais de uma tabela gerada no build.
    return render_template("roadmap.html", **_contexto_roadmap(item={}, salvo=novo_id, build_ok=True))


@app.post("/roadmap/apagar")
def apagar_roadmap():
    id_item = request.form.get("id", type=int)
    if id_item:
        wd.apagar_item_roadmap(ROOT, id_item)
    return redirect(url_for("formulario_roadmap"))


# --------------------------------------------------------------------------
# Fontes (livros de referência) — primeiro dado operacional do projeto que mora no banco
# (admin/banco.py) em vez de Markdown/YAML. Ao contrário de Changelog/Roadmap, salvar aqui NÃO
# chama publicar_build(): não mexe em docs/, não precisa reconstruir o site. Ver ARQUITETURA.md.
# --------------------------------------------------------------------------

@app.get("/fontes")
def formulario_fontes():
    with SessaoBanco() as sessao:
        fontes = banco.listar_fontes(sessao)
    return render_template("fontes.html", fontes=fontes)


@app.post("/fontes")
def salvar_fonte():
    nome = request.form.get("nome", "").strip()
    abreviacao = request.form.get("abreviacao", "").strip()
    edicao = request.form.get("edicao", "").strip()
    if nome and abreviacao and edicao:
        with SessaoBanco() as sessao:
            banco.adicionar_fonte(sessao, nome, abreviacao, edicao)
    return redirect(url_for("formulario_fontes"))


@app.post("/fontes/apagar")
def apagar_fonte():
    id_fonte = request.form.get("id", type=int)
    if id_fonte:
        with SessaoBanco() as sessao:
            banco.apagar_fonte(sessao, id_fonte)
    return redirect(url_for("formulario_fontes"))


# --------------------------------------------------------------------------
# Bugs reportados — /api/bugs* é o popup público (qualquer página do site, sem login, ver
# docs/javascripts/bug-report.js e _ROTAS_LIVRES acima); /bugs é a triagem, só pelo Painel.
# --------------------------------------------------------------------------

@app.get("/api/bugs/opcoes")
def api_bugs_opcoes():
    return jsonify(tipos=bugs.TIPOS, versao=wd.versao_atual_changelog(ROOT))


@app.post("/api/bugs")
def api_criar_bug():
    dados = request.get_json(silent=True) or {}
    pagina = str(dados.get("pagina") or "")
    tipo = str(dados.get("tipo") or "")
    descricao = str(dados.get("descricao") or "")
    try:
        novo_id = wd.criar_bug(ROOT, pagina, tipo, descricao)
    except ValueError as exc:
        return jsonify(erro=str(exc)), 400
    wd.publicar_build(ROOT)
    return jsonify(ok=True, id=novo_id)


@app.get("/bugs")
def listar_bugs_painel():
    return render_template("bugs.html", bugs=wd.listar_bugs(ROOT))


@app.post("/bugs/<int:id_bug>/resolver")
def resolver_bug(id_bug: int):
    nota = request.form.get("nota", "")
    wd.marcar_bug_resolvido(ROOT, id_bug, nota)
    wd.publicar_build(ROOT)
    return redirect(url_for("listar_bugs_painel"))


@app.post("/bugs/<int:id_bug>/reabrir")
def reabrir_bug_painel(id_bug: int):
    wd.reabrir_bug(ROOT, id_bug)
    wd.publicar_build(ROOT)
    return redirect(url_for("listar_bugs_painel"))


def _resolver_pagina(rel: str) -> Path | None:
    """Resolve um caminho relativo a docs/ com segurança (sem sair de docs/)."""
    base = wd.docs_dir(ROOT).resolve()
    candidato = (base / rel).resolve()
    if base not in candidato.parents and candidato != base:
        return None
    if not candidato.is_file() or candidato.suffix != ".md":
        return None
    return candidato


# --------------------------------------------------------------------------
# O site em si (pasta site/, já construída pelo MkDocs) — registrada por último, depois de toda
# rota específica do Painel, para nunca disputar caminho com elas. Nenhuma pasta de docs/ colida
# com um prefixo de rota do Painel (conferido: /sessao, /ficha*, /editar, /sessao-ao-vivo, /api,
# /npc, /lugar, /jogador, /sessoes, /linha-do-tempo), então só a raiz precisou mudar (ver /painel
# acima). site/ é (re)construído por publicar_build() a cada escrita — ver wiki_data.py.
# --------------------------------------------------------------------------

@app.get("/", defaults={"caminho": ""})
@app.get("/<path:caminho>")
def servir_site(caminho):
    base = SITE_DIR.resolve()
    candidato = (base / caminho).resolve()
    if candidato != base and base not in candidato.parents:
        abort(404)
    if candidato.is_dir():
        candidato = candidato / "index.html"
    if not candidato.is_file():
        pagina_404 = base / "404.html"
        if pagina_404.is_file():
            return send_file(pagina_404), 404
        abort(404)
    return send_file(candidato)


if __name__ == "__main__":
    # Por padrão só escuta 127.0.0.1 (ninguém mais na rede alcança o painel). Para expor numa
    # rede maior (Tailscale, rede local, ou internet via port forward/Cloudflare Tunnel), rode com
    # PAINEL_HOST=0.0.0.0 — e, nesse caso, defina também PAINEL_SENHA (direto ou em
    # admin/painel_local.env, nunca commitado) para exigir login. Sem PAINEL_SENHA, o login fica
    # desligado — ok para uso só em 127.0.0.1, arriscado para qualquer coisa mais aberta que isso.
    if not (SITE_DIR / "index.html").is_file():
        print("Construindo o site por baixo dos panos (primeira vez)...")
        wd.publicar_build(ROOT)
    host = os.environ.get("PAINEL_HOST", "127.0.0.1")
    if host != "127.0.0.1" and not SENHA_PAINEL:
        print(
            "AVISO: PAINEL_HOST != 127.0.0.1 mas PAINEL_SENHA não está definida — "
            "o Painel vai ficar acessível SEM LOGIN para quem alcançar esse endereço."
        )
    app.run(host=host, port=5001, debug=False)
