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
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for

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
    tipo = request.args.get("tipo", "npc")
    item_slug = request.args.get("item", "")
    if tipo not in wd.TIPOS_FICHA:
        tipo = "npc"
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
    tipo = request.form.get("tipo", "npc")
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
