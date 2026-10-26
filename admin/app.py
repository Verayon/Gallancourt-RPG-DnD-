"""Painel do Mestre — ferramenta local para registrar sessões e editar páginas da wiki
de Gallancourt sem editar arquivos à mão.

Uso:
    .venv\\Scripts\\python admin\\app.py
    (ou dê duplo clique em admin\\iniciar-painel.bat)

Depois abra http://127.0.0.1:5001/. Roda só em 127.0.0.1 (não aparece na rede). Veja
docs/mestre/painel.md para o guia de uso.
"""
from __future__ import annotations

import datetime
import os
import re
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for

import sessao_viva as sv
import wiki_data as wd

ROOT = Path(os.environ.get("GALLANCOURT_ADMIN_ROOT", wd.DEFAULT_ROOT)).resolve()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB por envio


@app.context_processor
def _globais_template():
    return {"pastas_imagens": wd.PASTAS_IMAGENS}


def _entidade_por_slug(lista: list[wd.Entidade], slug: str) -> wd.Entidade | None:
    for e in lista:
        if e.slug == slug:
            return e
    return None


@app.get("/")
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
    build_ok, build_saida = wd.validar_build(ROOT)

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
        salvo=False,
    )


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

    contexto = dict(
        paginas=paginas, pagina_escolhida=pagina_escolhida, slug_escolhido=slug_antigo,
        valores=valores, campos_texto=wd.CAMPOS_STATBLOCK_TEXTO,
        campos_atributos=wd.CAMPOS_STATBLOCK_ATRIBUTOS, rotulos_atributos=wd.ROTULOS_ATRIBUTOS,
        campos_listas=wd.CAMPOS_STATBLOCK_LISTAS,
    )

    try:
        novo_slug = wd.salvar_statblock(ROOT, pagina_escolhida, slug_antigo, valores, ancora)
    except ValueError as exc:
        fichas = wd.listar_statblocks(ROOT)
        return render_template("ficha_combate.html", fichas=fichas, salvo=False, erro=str(exc), **contexto)

    build_ok, build_saida = wd.validar_build(ROOT)
    fichas = wd.listar_statblocks(ROOT)
    contexto["slug_escolhido"] = novo_slug
    return render_template(
        "ficha_combate.html", fichas=fichas, salvo=True, build_ok=build_ok, build_saida=build_saida,
        **contexto,
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

    ficha_da_vez = None
    atual = next((c for c in estado["combatentes"] if c["id"] == estado["turno_atual"]), None)
    if atual and atual.get("ficha_pagina") and atual.get("ficha_slug"):
        caminho_ficha = _resolver_pagina(atual["ficha_pagina"])
        if caminho_ficha is not None:
            ficha_da_vez = wd.ler_statblocks_da_pagina(caminho_ficha).get(atual["ficha_slug"])

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
    arquivo = request.files.get("imagem")
    imagem = (arquivo.filename, arquivo.read()) if arquivo and arquivo.filename else None
    try:
        r = wd.criar_npc(ROOT, valores, imagem)
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
    build_ok, build_saida = wd.validar_build(ROOT)
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


def _resolver_pagina(rel: str) -> Path | None:
    """Resolve um caminho relativo a docs/ com segurança (sem sair de docs/)."""
    base = wd.docs_dir(ROOT).resolve()
    candidato = (base / rel).resolve()
    if base not in candidato.parents and candidato != base:
        return None
    if not candidato.is_file() or candidato.suffix != ".md":
        return None
    return candidato


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
