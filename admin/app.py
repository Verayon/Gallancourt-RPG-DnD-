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
import re
import secrets
import time
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, session, url_for

import sessao_viva as sv
import wiki_data as wd
import roadmap
import bugs
import gerador_npc as gn

ROOT = Path(os.environ.get("GALLANCOURT_ADMIN_ROOT", wd.DEFAULT_ROOT)).resolve()
SITE_DIR = ROOT / "site"


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
_ROTAS_LIVRES = {"tela_login", "fazer_login", "static"}
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


@app.before_request
def _exigir_login():
    if not SENHA_PAINEL:
        return None  # sem PAINEL_SENHA configurada: autenticação desligada (uso só local)
    if request.endpoint in _ROTAS_LIVRES:
        return None
    if session.get("autenticado"):
        return None
    destino = request.full_path if request.query_string else request.path
    return redirect(url_for("tela_login", next=destino))


@app.context_processor
def _globais_template():
    return {"pastas_imagens": wd.PASTAS_IMAGENS, "autenticacao_ativa": bool(SENHA_PAINEL)}


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


@app.get("/ficha-combate")
def escolher_ficha_combate():
    paginas = wd.listar_todas_paginas(ROOT)
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
    paginas = wd.listar_todas_paginas(ROOT)
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


def _int_ou_none(valor: str) -> int | None:
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return int(valor)
    except ValueError:
        return None


def _combo_ficha(pagina: str, slug: str) -> str:
    return f"{pagina}::{slug}"


def _parse_combo_ficha(valor: str) -> tuple[str, str]:
    if not valor or "::" not in valor:
        return "", ""
    pagina, slug = valor.split("::", 1)
    return pagina, slug


def _pv_inicial_da_ficha(dados_ficha: dict | None) -> int | None:
    m = re.match(r"\s*(\d+)", (dados_ficha or {}).get("pv", "") or "")
    return int(m.group(1)) if m else None


def _redirect_sessao_ao_vivo(pagina: str, ancora: str = ""):
    url = url_for("ver_sessao_ao_vivo", pagina=pagina)
    if ancora:
        url += f"#{ancora}"
    return redirect(url)


def _ficha_da_vez(estado: dict) -> dict | None:
    """A ficha de combate do combatente da vez, se ele tiver uma vinculada — para mostrar o
    cartão completo (atributos, ações…) sem precisar abrir a página dele."""
    atual = next((c for c in estado["combatentes"] if c["id"] == estado["turno_atual"]), None)
    if atual and atual.get("ficha_pagina") and atual.get("ficha_slug"):
        caminho_ficha = _resolver_pagina(atual["ficha_pagina"])
        if caminho_ficha is not None:
            return wd.ler_statblocks_da_pagina(caminho_ficha).get(atual["ficha_slug"])
    return None


@app.get("/sessao-ao-vivo")
def ver_sessao_ao_vivo():
    paginas = wd.listar_todas_paginas(ROOT)
    pagina_escolhida = request.args.get("pagina", "")
    contexto = dict(
        paginas=paginas,
        pagina_escolhida=pagina_escolhida,
        fichas_disponiveis=wd.listar_statblocks(ROOT),
        combo_ficha=_combo_ficha,
    )
    if not pagina_escolhida:
        return render_template("sessao_ao_vivo.html", **contexto)

    if _resolver_pagina(pagina_escolhida) is None:
        abort(404)

    estado = sv.carregar(ROOT, pagina_escolhida)
    ficha_da_vez = _ficha_da_vez(estado)

    return render_template(
        "sessao_ao_vivo.html",
        estado=estado,
        combatentes=sv.ordem_de_exibicao(estado),
        resumo_combate=sv.resumo_combate(estado),
        diario_combate=sv.gerar_diario_de_combate(estado),
        tipos_combatente=sv.TIPOS_COMBATENTE,
        tipos_acao=sv.TIPOS_ACAO,
        rotulos_acao=sv.ROTULOS_ACAO,
        ficha_da_vez=ficha_da_vez,
        atributos_ficha=wd.CAMPOS_STATBLOCK_ATRIBUTOS,
        rotulos_atributos=wd.ROTULOS_ATRIBUTOS,
        modificador=wd.modificador,
        linhas_para_trechos=wd.linhas_para_trechos,
        **contexto,
    )


@app.post("/sessao-ao-vivo/nota")
def adicionar_nota_ao_vivo():
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    sv.adicionar_nota(ROOT, pagina, request.form.get("texto", ""))
    return _redirect_sessao_ao_vivo(pagina, "notas")


@app.post("/sessao-ao-vivo/nota/<int:indice>/remover")
def remover_nota_ao_vivo(indice: int):
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    sv.remover_nota(ROOT, pagina, indice)
    return _redirect_sessao_ao_vivo(pagina, "notas")


@app.post("/sessao-ao-vivo/resumo")
def salvar_resumo_ao_vivo():
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    sv.salvar_resumo(ROOT, pagina, request.form.get("resumo", ""))
    return _redirect_sessao_ao_vivo(pagina, "notas")


@app.post("/sessao-ao-vivo/combatente")
def adicionar_combatente_ao_vivo():
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)

    nome = request.form.get("nome", "").strip()
    tipo = request.form.get("tipo", "npc")
    iniciativa = _int_ou_none(request.form.get("iniciativa", "")) or 0
    pv_atual = _int_ou_none(request.form.get("pv_atual", ""))
    pv_maximo = _int_ou_none(request.form.get("pv_maximo", ""))
    ficha_pagina, ficha_slug = _parse_combo_ficha(request.form.get("ficha", ""))

    if ficha_pagina and ficha_slug:
        caminho_ficha = _resolver_pagina(ficha_pagina)
        dados_ficha = wd.ler_statblocks_da_pagina(caminho_ficha).get(ficha_slug) if caminho_ficha else None
        if dados_ficha:
            if not nome:
                nome = dados_ficha.get("nome", "")
            pv_da_ficha = _pv_inicial_da_ficha(dados_ficha)
            if pv_da_ficha is not None:
                pv_atual = pv_da_ficha if pv_atual is None else pv_atual
                pv_maximo = pv_da_ficha if pv_maximo is None else pv_maximo

    if nome:
        sv.adicionar_combatente(
            ROOT, pagina, nome, tipo, iniciativa, pv_atual, pv_maximo, ficha_pagina, ficha_slug,
        )
    return _redirect_sessao_ao_vivo(pagina, "iniciativa")


@app.post("/sessao-ao-vivo/combatente/<int:cid>/remover")
def remover_combatente_ao_vivo(cid: int):
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    sv.remover_combatente(ROOT, pagina, cid)
    return _redirect_sessao_ao_vivo(pagina, "iniciativa")


@app.post("/sessao-ao-vivo/combatente/<int:cid>/pv")
def ajustar_pv_ao_vivo(cid: int):
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    delta = _int_ou_none(request.form.get("delta", "")) or 0
    sv.ajustar_pv(ROOT, pagina, cid, delta)
    return _redirect_sessao_ao_vivo(pagina, "iniciativa")


@app.post("/sessao-ao-vivo/combatente/<int:cid>/status")
def atualizar_status_ao_vivo(cid: int):
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    sv.atualizar_status(ROOT, pagina, cid, request.form.get("status", ""))
    return _redirect_sessao_ao_vivo(pagina, "iniciativa")


@app.post("/sessao-ao-vivo/combatente/<int:cid>/flag/<campo>")
def alternar_flag_ao_vivo(cid: int, campo: str):
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    sv.alternar_flag(ROOT, pagina, cid, campo)
    return _redirect_sessao_ao_vivo(pagina, "iniciativa")


@app.post("/sessao-ao-vivo/turno/proximo")
def proximo_turno_ao_vivo():
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    sv.proximo_turno(ROOT, pagina)
    return _redirect_sessao_ao_vivo(pagina, "iniciativa")


@app.post("/sessao-ao-vivo/acao")
def registrar_acao_ao_vivo():
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    autor_id = _int_ou_none(request.form.get("autor_id", ""))
    alvo_id = _int_ou_none(request.form.get("alvo_id", ""))
    valor = _int_ou_none(request.form.get("valor", ""))
    tipo = request.form.get("tipo", "outro")
    meio = request.form.get("meio", "")
    obs = request.form.get("obs", "")
    sv.registrar_acao(ROOT, pagina, autor_id, tipo, alvo_id, meio, valor, obs)
    return _redirect_sessao_ao_vivo(pagina, "acoes")


@app.post("/sessao-ao-vivo/acao/<int:acao_id>/remover")
def remover_acao_ao_vivo(acao_id: int):
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    sv.remover_acao(ROOT, pagina, acao_id)
    return _redirect_sessao_ao_vivo(pagina, "acoes")


@app.post("/sessao-ao-vivo/arquivar")
def arquivar_sessao_ao_vivo():
    pagina = request.form.get("pagina", "")
    if _resolver_pagina(pagina) is None:
        abort(404)
    sv.arquivar_e_limpar(ROOT, pagina)
    return _redirect_sessao_ao_vivo(pagina)


# --------------------------------------------------------------------------
# API JSON do Painel de Iniciativa — mesma lógica das rotas acima (sessao_viva.py continua
# sendo a única fonte de verdade das regras), só devolvendo o estado como JSON em vez de uma
# página HTML inteira. Usada pelo widget embutido na própria página da sessão
# (docs/javascripts/painel-iniciativa.js); as rotas HTML acima continuam existindo, para quem
# preferir usar o Painel direto, sem o site aberto. Site e Painel são a mesma origem (ver
# servir_site, mais abaixo), então não precisa de CORS.
# --------------------------------------------------------------------------


def _erro_json(mensagem: str, status: int = 404):
    return jsonify(erro=mensagem), status


def _fichas_disponiveis_sessao(pagina_rel_docs: str) -> list[dict]:
    """Fichas de combate que fazem sentido oferecer nesta sessão: as que já estão na própria
    página, mais as dos jogadores/NPCs marcados como participantes dela (ver
    /sessoes/participantes) — nunca todo stat-block do site."""
    titulos = {p.rel_docs: p.titulo for p in wd.listar_todas_paginas(ROOT)}
    participantes = wd.ler_participantes(ROOT, pagina_rel_docs)
    paginas_relevantes = [pagina_rel_docs] + participantes["jogadores"] + participantes["npcs"]

    resultado = []
    vistos = set()
    for rel in paginas_relevantes:
        caminho = _resolver_pagina(rel)
        if caminho is None:
            continue
        for slug, dados in wd.ler_statblocks_da_pagina(caminho).items():
            if (rel, slug) in vistos:
                continue
            vistos.add((rel, slug))
            resultado.append({
                "slug": slug, "nome": dados.get("nome") or slug,
                "pagina_rel_docs": rel, "pagina_titulo": titulos.get(rel, rel),
            })
    return resultado


def _estado_json(pagina: str):
    estado = sv.carregar(ROOT, pagina)
    return jsonify(
        pagina=pagina,
        estado=estado,
        combatentes=sv.ordem_de_exibicao(estado),
        resumo_combate=sv.resumo_combate(estado),
        diario_combate=sv.gerar_diario_de_combate(estado),
        ficha_da_vez=_ficha_da_vez(estado),
        fichas_disponiveis=_fichas_disponiveis_sessao(pagina),
        tipos_combatente=sv.TIPOS_COMBATENTE,
        tipos_acao=sv.TIPOS_ACAO,
        rotulos_acao=sv.ROTULOS_ACAO,
        atributos_ficha=wd.CAMPOS_STATBLOCK_ATRIBUTOS,
        rotulos_atributos=wd.ROTULOS_ATRIBUTOS,
    )


@app.get("/api/sessao-ao-vivo/<path:pagina>")
def api_ver_sessao_ao_vivo(pagina):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    return _estado_json(pagina)


@app.post("/api/sessao-ao-vivo/<path:pagina>/nota")
def api_adicionar_nota(pagina):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    dados = request.get_json(silent=True) or {}
    sv.adicionar_nota(ROOT, pagina, dados.get("texto", ""))
    return _estado_json(pagina)


@app.post("/api/sessao-ao-vivo/<path:pagina>/nota/<int:indice>/remover")
def api_remover_nota(pagina, indice):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    sv.remover_nota(ROOT, pagina, indice)
    return _estado_json(pagina)


@app.post("/api/sessao-ao-vivo/<path:pagina>/resumo")
def api_salvar_resumo(pagina):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    dados = request.get_json(silent=True) or {}
    sv.salvar_resumo(ROOT, pagina, dados.get("resumo", ""))
    return _estado_json(pagina)


@app.post("/api/sessao-ao-vivo/<path:pagina>/combatente")
def api_adicionar_combatente(pagina):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or "").strip()
    tipo = dados.get("tipo") or "npc"
    iniciativa = _int_ou_none(str(dados.get("iniciativa", ""))) or 0
    pv_atual = _int_ou_none(str(dados.get("pv_atual", "")))
    pv_maximo = _int_ou_none(str(dados.get("pv_maximo", "")))
    ficha_pagina = dados.get("ficha_pagina") or ""
    ficha_slug = dados.get("ficha_slug") or ""

    if ficha_pagina and ficha_slug:
        caminho_ficha = _resolver_pagina(ficha_pagina)
        dados_ficha = wd.ler_statblocks_da_pagina(caminho_ficha).get(ficha_slug) if caminho_ficha else None
        if dados_ficha:
            if not nome:
                nome = dados_ficha.get("nome", "")
            pv_da_ficha = _pv_inicial_da_ficha(dados_ficha)
            if pv_da_ficha is not None:
                pv_atual = pv_da_ficha if pv_atual is None else pv_atual
                pv_maximo = pv_da_ficha if pv_maximo is None else pv_maximo

    if nome:
        sv.adicionar_combatente(
            ROOT, pagina, nome, tipo, iniciativa, pv_atual, pv_maximo, ficha_pagina, ficha_slug,
        )
    return _estado_json(pagina)


@app.post("/api/sessao-ao-vivo/<path:pagina>/combatente/<int:cid>/remover")
def api_remover_combatente(pagina, cid):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    sv.remover_combatente(ROOT, pagina, cid)
    return _estado_json(pagina)


@app.post("/api/sessao-ao-vivo/<path:pagina>/combatente/<int:cid>/pv")
def api_ajustar_pv(pagina, cid):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    dados = request.get_json(silent=True) or {}
    delta = _int_ou_none(str(dados.get("delta", ""))) or 0
    sv.ajustar_pv(ROOT, pagina, cid, delta)
    return _estado_json(pagina)


@app.post("/api/sessao-ao-vivo/<path:pagina>/combatente/<int:cid>/status")
def api_atualizar_status(pagina, cid):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    dados = request.get_json(silent=True) or {}
    sv.atualizar_status(ROOT, pagina, cid, dados.get("status", ""))
    return _estado_json(pagina)


@app.post("/api/sessao-ao-vivo/<path:pagina>/combatente/<int:cid>/flag/<campo>")
def api_alternar_flag(pagina, cid, campo):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    sv.alternar_flag(ROOT, pagina, cid, campo)
    return _estado_json(pagina)


@app.post("/api/sessao-ao-vivo/<path:pagina>/turno/proximo")
def api_proximo_turno(pagina):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    sv.proximo_turno(ROOT, pagina)
    return _estado_json(pagina)


@app.post("/api/sessao-ao-vivo/<path:pagina>/acao")
def api_registrar_acao(pagina):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    dados = request.get_json(silent=True) or {}
    autor_id = _int_ou_none(str(dados.get("autor_id", "")))
    alvo_id = _int_ou_none(str(dados.get("alvo_id", "")))
    valor = _int_ou_none(str(dados.get("valor", "")))
    tipo = dados.get("tipo") or "outro"
    meio = dados.get("meio") or ""
    obs = dados.get("obs") or ""
    sv.registrar_acao(ROOT, pagina, autor_id, tipo, alvo_id, meio, valor, obs)
    return _estado_json(pagina)


@app.post("/api/sessao-ao-vivo/<path:pagina>/acao/<int:acao_id>/remover")
def api_remover_acao(pagina, acao_id):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    sv.remover_acao(ROOT, pagina, acao_id)
    return _estado_json(pagina)


@app.post("/api/sessao-ao-vivo/<path:pagina>/arquivar")
def api_arquivar(pagina):
    if _resolver_pagina(pagina) is None:
        return _erro_json("Página não encontrada.")
    sv.arquivar_e_limpar(ROOT, pagina)
    return _estado_json(pagina)


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
# Roadmap
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
    }
    try:
        novo_id = wd.salvar_item_roadmap(ROOT, dados, id_item)
    except ValueError as exc:
        return render_template("roadmap.html", **_contexto_roadmap(item={**dados, "id": id_item}, erro=str(exc)))
    build_ok, build_saida = wd.publicar_build(ROOT)
    return render_template(
        "roadmap.html", **_contexto_roadmap(item={}, salvo=novo_id, build_ok=build_ok, build_saida=build_saida),
    )


@app.post("/roadmap/apagar")
def apagar_roadmap():
    id_item = request.form.get("id", type=int)
    if id_item:
        wd.apagar_item_roadmap(ROOT, id_item)
        wd.publicar_build(ROOT)
    return redirect(url_for("formulario_roadmap"))


# --------------------------------------------------------------------------
# Bugs reportados — /bug/novo é o botão público (qualquer página do site); /bugs é a triagem,
# só pelo Painel.
# --------------------------------------------------------------------------

@app.get("/bug/novo")
def formulario_bug():
    return render_template("bug_novo.html", areas=bugs.AREAS, salvo=False)


@app.post("/bug/novo")
def criar_bug():
    area = request.form.get("area", "")
    descricao = request.form.get("descricao", "")
    try:
        novo_id = wd.criar_bug(ROOT, area, descricao)
    except ValueError as exc:
        return render_template("bug_novo.html", areas=bugs.AREAS, salvo=False, erro=str(exc))
    wd.publicar_build(ROOT)
    return render_template("bug_novo.html", areas=bugs.AREAS, salvo=novo_id)


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
