"""Lógica de leitura e escrita da wiki, usada pelo Painel do Mestre (admin/app.py).

Isolado do Flask de propósito: pode ser testado chamando as funções diretamente, sem subir um
servidor. Todas as funções que escrevem arquivo recebem `root` (a raiz do projeto, onde ficam
`docs/` e `mkdocs.yml`) para permitir apontar para uma cópia de teste em vez do projeto real.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Entidade:
    slug: str
    titulo: str
    rel_docs: str  # caminho relativo a docs/, ex: "personagens/scyras-corbeau.md"


def docs_dir(root: Path) -> Path:
    return root / "docs"


def mkdocs_yml(root: Path) -> Path:
    return root / "mkdocs.yml"


def _titulo_do_arquivo(path: Path) -> str:
    """Extrai o título de uma página pelo primeiro cabeçalho `# ...`."""
    try:
        texto = path.read_text(encoding="utf-8")
    except OSError:
        return path.stem
    m = re.search(r"^#\s+(.+?)\s*$", texto, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return path.stem.replace("-", " ").title()


def _listar_entidades(pasta: Path, rel_prefixo: str) -> list[Entidade]:
    if not pasta.is_dir():
        return []
    itens = []
    for p in sorted(pasta.glob("*.md")):
        if p.stem == "index":
            continue
        itens.append(
            Entidade(
                slug=p.stem,
                titulo=_titulo_do_arquivo(p),
                rel_docs=f"{rel_prefixo}/{p.name}",
            )
        )
    itens.sort(key=lambda e: e.titulo)
    return itens


def listar_npcs(root: Path) -> list[Entidade]:
    return _listar_entidades(docs_dir(root) / "personagens", "personagens")


def listar_cidades(root: Path) -> list[Entidade]:
    return _listar_entidades(docs_dir(root) / "cidades", "cidades")


def listar_faccoes(root: Path) -> list[Entidade]:
    return _listar_entidades(docs_dir(root) / "faccoes", "faccoes")


def listar_todas_paginas(root: Path) -> list[Entidade]:
    """Toda página .md dentro de docs/, para o editor genérico."""
    base = docs_dir(root)
    itens = []
    for p in sorted(base.rglob("*.md")):
        rel = p.relative_to(base).as_posix()
        itens.append(Entidade(slug=rel, titulo=_titulo_do_arquivo(p), rel_docs=rel))
    itens.sort(key=lambda e: e.rel_docs)
    return itens


def proxima_sessao(root: Path) -> int:
    pasta = docs_dir(root) / "diario"
    maior = 0
    for p in pasta.glob("sessao-*.md"):
        m = re.match(r"sessao-(\d+)\.md$", p.name)
        if m:
            maior = max(maior, int(m.group(1)))
    return maior + 1


def _num_para_nome(numero: int) -> str:
    return f"sessao-{numero:02d}.md"


def _ler(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _escrever(path: Path, texto: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")


def _bloco_entre_marcadores(texto: str, inicio: str, fim: str) -> tuple[int, int] | None:
    i = texto.find(inicio)
    f = texto.find(fim)
    if i == -1 or f == -1 or f < i:
        return None
    return i + len(inicio), f


def criar_pagina_sessao(
    root: Path,
    numero: int,
    titulo: str,
    data_real: str,
    data_campanha: str,
    locais: list[Entidade],
    npcs: list[Entidade],
    resumo: str,
    atualizacoes: list[tuple[Entidade, str]],
) -> Path:
    diario = docs_dir(root) / "diario"
    nome_arquivo = _num_para_nome(numero)
    caminho = diario / nome_arquivo

    locais_links = ", ".join(f"[{e.titulo}](../{e.rel_docs})" for e in locais) or "—"
    npcs_links = ", ".join(f"[{e.titulo}](../{e.rel_docs})" for e in npcs) or "—"

    linhas_atualizacoes = "\n".join(
        f"- [{e.titulo}](../{e.rel_docs}) — {nota}" for e, nota in atualizacoes
    ) or "- (nenhuma página específica marcada)"

    anterior_link = "—"
    if numero > 1:
        anterior_nome = _num_para_nome(numero - 1)
        if (diario / anterior_nome).exists():
            anterior_link = f"[Sessão {numero - 1}]({anterior_nome})"

    conteudo = f"""---
tags:
  - Diário
---

# Sessão {numero} — {titulo}

<div class="ficha" markdown>

| | |
|---|---|
| **Data real** | {data_real} |
| **Data na campanha** | {data_campanha} |
| **Local(is)** | {locais_links} |
| **NPCs em cena** | {npcs_links} |

</div>

## O que aconteceu

{resumo}

## Atualizações no cânone

{linhas_atualizacoes}

---

**Anterior:** {anterior_link} · **Próxima:** —
"""
    _escrever(caminho, conteudo)

    # Liga a sessão anterior a esta.
    if numero > 1:
        anterior_path = diario / _num_para_nome(numero - 1)
        if anterior_path.exists():
            texto_anterior = _ler(anterior_path)
            alvo = "**Próxima:** —"
            if alvo in texto_anterior:
                novo = texto_anterior.replace(
                    alvo, f"**Próxima:** [Sessão {numero}]({nome_arquivo})", 1
                )
                _escrever(anterior_path, novo)

    return caminho


def atualizar_indice_diario(
    root: Path, numero: int, data_real: str, data_campanha: str, titulo: str
) -> None:
    caminho = docs_dir(root) / "diario" / "index.md"
    texto = _ler(caminho)
    nome_arquivo = _num_para_nome(numero)

    # --- Tabela de sessões ---
    limites = _bloco_entre_marcadores(texto, "<!-- inicio:sessoes -->", "<!-- fim:sessoes -->")
    if limites:
        ini, fim = limites
        bloco = texto[ini:fim]
        linhas = [l for l in bloco.splitlines() if l.strip()]
        nova_linha = (
            f"| [Sessão {numero}](sessao-{numero:02d}.md) | {data_real} | {data_campanha} "
            f"| {titulo} |"
        )
        linhas_finais = []
        for l in linhas:
            if l.strip().startswith("| —") or "Nenhuma sessão registrada ainda" in l:
                continue
            linhas_finais.append(l)
        linhas_finais.append(nova_linha)
        novo_bloco = "\n" + "\n".join(linhas_finais) + "\n"
        texto = texto[:ini] + novo_bloco + texto[fim:]

    # --- Linha do tempo mermaid ---
    limites = _bloco_entre_marcadores(texto, "<!-- inicio:timeline -->", "<!-- fim:timeline -->")
    if limites:
        ini, fim = limites
        bloco = texto[ini:fim]
        placeholder = "    Hoje : (a primeira sessão aparecerá aqui)"
        nova_linha = f"    {data_campanha} : Sessão {numero} — {titulo}"
        if placeholder in bloco:
            bloco = bloco.replace(placeholder, nova_linha, 1)
        else:
            # insere antes do fence de fechamento ```
            pos_fence = bloco.rfind("```")
            if pos_fence != -1:
                bloco = bloco[:pos_fence] + nova_linha + "\n" + bloco[pos_fence:]
        texto = texto[:ini] + bloco + texto[fim:]

    _escrever(caminho, texto)


def registrar_historico(entidade: Entidade, root: Path, numero: int, data_campanha: str, nota: str) -> None:
    caminho = docs_dir(root) / entidade.rel_docs
    if not caminho.exists():
        return
    texto = _ler(caminho)
    heading = "## Histórico de sessões"
    bullet = (
        f"- **[Sessão {numero}](../diario/{_num_para_nome(numero)})** ({data_campanha}) — {nota}"
    )
    if heading in texto:
        idx = texto.index(heading) + len(heading)
        resto = texto[idx:]
        m = re.search(r"\n#{1,6}\s", resto)
        insere_em = idx + (m.start() if m else len(resto))
        antes = texto[:insere_em].rstrip("\n")
        depois = texto[insere_em:]
        texto = antes + "\n" + bullet + "\n" + depois
    else:
        texto = texto.rstrip("\n") + "\n\n" + heading + "\n\n" + bullet + "\n"
    _escrever(caminho, texto)


def adicionar_sessao_ao_nav(root: Path, numero: int) -> bool:
    caminho = mkdocs_yml(root)
    texto = _ler(caminho)
    linhas = texto.split("\n")
    ancora = None
    indent = None
    for i, linha in enumerate(linhas):
        m = re.match(r"^(\s*)- diario/index\.md\s*$", linha)
        if m:
            ancora = i
            indent = m.group(1)
            break
    if ancora is None:
        return False
    padrao_sessao = re.compile(rf"^{re.escape(indent)}- Sessão \d+: diario/sessao-\d+\.md\s*$")
    pos = ancora + 1
    while pos < len(linhas) and padrao_sessao.match(linhas[pos]):
        pos += 1
    nova_linha = f"{indent}- Sessão {numero}: diario/sessao-{numero:02d}.md"
    linhas.insert(pos, nova_linha)
    _escrever(caminho, "\n".join(linhas))
    return True


def validar_build(root: Path) -> tuple[bool, str]:
    """Roda `mkdocs build --strict` num diretório temporário, sem afetar o site já servido."""
    python = sys.executable
    with tempfile.TemporaryDirectory() as tmp:
        try:
            resultado = subprocess.run(
                [python, "-m", "mkdocs", "build", "--strict", "-d", tmp],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=120,
            )
        except Exception as exc:  # noqa: BLE001 — queremos mostrar qualquer falha ao usuário
            return False, f"Não consegui rodar o mkdocs build: {exc}"
        saida = (resultado.stdout or "") + (resultado.stderr or "")
        return resultado.returncode == 0, saida.strip()


# --------------------------------------------------------------------------
# Ficha de personagem / ficha da cidade
# --------------------------------------------------------------------------

# Cada campo: (chave interna, rótulo mostrado, tipo de campo no formulário).
CAMPOS_FICHA_NPC = [
    ("aparencia", "Aparência física", "textarea"),
    ("personalidade", "Personalidade", "textarea"),
    ("traco", "Traço marcante", "texto"),
    ("ideal", "Ideal", "texto"),
    ("vinculo", "Vínculo", "texto"),
    ("defeito", "Defeito", "texto"),
    ("proficiencias", "Proficiências e idiomas", "textarea"),
]

CAMPOS_FICHA_CIDADE = [
    ("populacao", "População", "texto"),
    ("defesas", "Defesas e guarnição", "textarea"),
]

TITULO_SECAO_FICHA = "Ficha de personagem"
TITULO_SECAO_FICHA_CIDADE = "Ficha da cidade"

TIPOS_FICHA = {
    "npc": (listar_npcs, CAMPOS_FICHA_NPC, TITULO_SECAO_FICHA),
    "cidade": (listar_cidades, CAMPOS_FICHA_CIDADE, TITULO_SECAO_FICHA_CIDADE),
}


def _remover_secao(texto: str, heading: str) -> str:
    """Remove a seção `## heading` inteira (até o próximo cabeçalho ou o fim do arquivo)."""
    if heading not in texto:
        return texto
    idx = texto.index(heading)
    fim_heading = idx + len(heading)
    resto = texto[fim_heading:]
    m = re.search(r"\n#{1,6}\s", resto)
    fim_secao = fim_heading + (m.start() if m else len(resto))
    antes = texto[:idx].rstrip("\n")
    depois = texto[fim_secao:].lstrip("\n")
    if antes and depois:
        return antes + "\n\n" + depois
    return (antes + depois).strip("\n") + "\n"


def ler_campos_ficha(path: Path, campos: list[tuple[str, str, str]]) -> dict[str, str]:
    """Lê os valores atuais de cada campo (string vazia se a seção ainda não existir)."""
    texto = _ler(path)
    valores = {}
    for chave, _, _ in campos:
        limites = _bloco_entre_marcadores(texto, f"<!-- campo:{chave} -->", f"<!-- /campo:{chave} -->")
        if limites:
            valor = texto[limites[0]:limites[1]].strip()
            valores[chave] = "" if valor == "*(não preenchido)*" else valor
        else:
            valores[chave] = ""
    return valores


def escrever_ficha(
    path: Path, titulo_secao: str, campos: list[tuple[str, str, str]], valores: dict[str, str]
) -> None:
    """Substitui a seção `## {titulo_secao}` inteira pelos valores atuais dos campos.

    Reescreve a seção do zero: qualquer texto colado ali manualmente, fora dos campos
    reconhecidos, some na próxima vez que a ficha for salva pelo painel.
    """
    texto = _ler(path)
    heading = f"## {titulo_secao}"
    texto_sem_secao = _remover_secao(texto, heading)

    partes = [heading, ""]
    for chave, rotulo, _ in campos:
        valor = (valores.get(chave) or "").strip() or "*(não preenchido)*"
        partes += [f"**{rotulo}**", f"<!-- campo:{chave} -->", valor, f"<!-- /campo:{chave} -->", ""]
    bloco = "\n".join(partes).rstrip() + "\n"

    novo_texto = texto_sem_secao.rstrip("\n") + "\n\n" + bloco
    _escrever(path, novo_texto)


def aplicar_sessao(
    root: Path,
    titulo: str,
    data_real: str,
    data_campanha: str,
    resumo: str,
    npcs_selecionados: list[tuple[Entidade, str]],
    locais_selecionados: list[tuple[Entidade, str]],
) -> dict:
    """Executa o fluxo completo de registrar uma sessão. Retorna um resumo do que foi feito."""
    numero = proxima_sessao(root)
    todos_locais = [e for e, _ in locais_selecionados]
    todos_npcs = [e for e, _ in npcs_selecionados]
    atualizacoes = locais_selecionados + npcs_selecionados

    caminho_sessao = criar_pagina_sessao(
        root, numero, titulo, data_real, data_campanha, todos_locais, todos_npcs, resumo,
        atualizacoes,
    )
    atualizar_indice_diario(root, numero, data_real, data_campanha, titulo)
    for entidade, nota in atualizacoes:
        registrar_historico(entidade, root, numero, data_campanha, nota)
    nav_ok = adicionar_sessao_ao_nav(root, numero)
    build_ok, build_saida = validar_build(root)

    return {
        "numero": numero,
        "arquivo": str(caminho_sessao.relative_to(root)),
        "paginas_atualizadas": [e.rel_docs for e, _ in atualizacoes],
        "nav_ok": nav_ok,
        "build_ok": build_ok,
        "build_saida": build_saida,
    }


# --------------------------------------------------------------------------
# Imagens — upload pelo Painel, sem precisar copiar arquivo à mão antes
# --------------------------------------------------------------------------

PASTAS_IMAGENS = ["cidades", "personagens", "faccoes", "eventos", "geografia", "mapas", "mundo"]

EXTENSOES_IMAGEM_PERMITIDAS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def salvar_imagem(
    root: Path, pagina_rel_docs: str, pasta: str, nome_original: str, conteudo: bytes,
) -> tuple[Path, str]:
    """Salva uma imagem enviada em docs/assets/imagens/<pasta>/ (criando um nome novo se já
    existir um arquivo com o mesmo nome) e devolve o caminho no disco e o trecho Markdown,
    já com o caminho relativo certo para funcionar a partir da página editada."""
    from werkzeug.utils import secure_filename

    if pasta not in PASTAS_IMAGENS:
        pasta = "mundo"

    nome = secure_filename(nome_original) or "imagem"
    sufixo = Path(nome).suffix.lower()
    if sufixo not in EXTENSOES_IMAGEM_PERMITIDAS:
        raise ValueError(f"Tipo de arquivo não permitido: {sufixo or '(sem extensão)'}")

    pasta_destino = docs_dir(root) / "assets" / "imagens" / pasta
    pasta_destino.mkdir(parents=True, exist_ok=True)

    base = Path(nome).stem
    destino = pasta_destino / nome
    contador = 1
    while destino.exists():
        destino = pasta_destino / f"{base}-{contador}{sufixo}"
        contador += 1

    destino.write_bytes(conteudo)

    pagina_path = docs_dir(root) / pagina_rel_docs
    rel_para_pagina = Path(os.path.relpath(destino, start=pagina_path.parent)).as_posix()
    legenda = base.replace("-", " ").replace("_", " ")
    snippet = f"\n![{legenda}]({rel_para_pagina})\n"
    return destino, snippet


# --------------------------------------------------------------------------
# Ficha de combate (stat block) — cartão de NPC com atributos, perícias,
# equipamento, ações e magias, parecido com uma ficha oficial. Os valores
# ficam guardados em JSON dentro de um comentário HTML invisível, junto do
# cartão renderizado, para que o Painel consiga reler e editar depois.
# --------------------------------------------------------------------------

# (chave, rótulo, obrigatório)
CAMPOS_STATBLOCK_TEXTO = [
    ("nome", "Nome", True),
    ("subtitulo", "Tipo / papel (ex.: Humanoide médio, qualquer alinhamento)", False),
    ("ca", "Classe de Armadura", True),
    ("pv", "Pontos de Vida (ex.: 11 (2d8+2))", True),
    ("deslocamento", "Deslocamento (ex.: 9 m)", True),
    ("pericias", "Perícias (ex.: Furtividade +3, Intimidação +1)", False),
    ("sentidos", "Sentidos (ex.: Percepção passiva 10)", False),
    ("idiomas", "Idiomas", False),
    ("equipamento", "Equipamento", False),
]

CAMPOS_STATBLOCK_ATRIBUTOS = ["for", "des", "con", "int", "sab", "car"]
ROTULOS_ATRIBUTOS = {
    "for": "FOR", "des": "DES", "con": "CON", "int": "INT", "sab": "SAB", "car": "CAR",
}

# (chave, rótulo) — textarea de múltiplas linhas
CAMPOS_STATBLOCK_LISTAS = [
    ("tracos", "Traços (um por linha: Nome: descrição)"),
    ("acoes", "Ações (um por linha: Nome: descrição)"),
    ("reacoes", "Reações (um por linha: Nome: descrição)"),
    ("magias", "Magias (texto livre)"),
]

_MARCADOR_INICIO = "<!-- inicio:statblock:{slug} -->"
_MARCADOR_FIM = "<!-- fim:statblock:{slug} -->"
_MARCADOR_DADOS = re.compile(
    r"<!-- inicio:statblock:([a-z0-9-]+) -->\s*<!-- dados:statblock (.*?) -->", re.DOTALL,
)


def slug_statblock(nome: str) -> str:
    base = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base or "npc"


def _modificador(valor: str) -> str:
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError):
        return "+0"
    mod = (numero - 10) // 2
    return f"+{mod}" if mod >= 0 else str(mod)


def _linhas_para_trechos(texto: str) -> list[tuple[str, str]]:
    trechos = []
    for linha in (texto or "").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        if ":" in linha:
            nome, resto = linha.split(":", 1)
            trechos.append((nome.strip(), resto.strip()))
        else:
            trechos.append(("", linha))
    return trechos


def _renderizar_trechos(texto: str) -> str:
    partes = []
    for nome, resto in _linhas_para_trechos(texto):
        partes.append(f"***{nome}.*** {resto}" if nome else resto)
    return "\n\n".join(partes)


def renderizar_statblock(slug: str, v: dict) -> str:
    """Gera o markdown do cartão (com os dados embutidos) a partir dos valores da ficha."""
    rotulos_linha = " | ".join(ROTULOS_ATRIBUTOS[a] for a in CAMPOS_STATBLOCK_ATRIBUTOS)
    separador_linha = "|".join("---" for _ in CAMPOS_STATBLOCK_ATRIBUTOS)
    valores_linha = " | ".join(
        f"{(v.get(a) or '').strip() or '—'} ({_modificador(v.get(a, ''))})"
        for a in CAMPOS_STATBLOCK_ATRIBUTOS
    )

    linhas_extra = []
    for chave, rotulo in (
        ("pericias", "Perícias"), ("sentidos", "Sentidos"),
        ("idiomas", "Idiomas"), ("equipamento", "Equipamento"),
    ):
        valor = (v.get(chave) or "").strip()
        if valor:
            linhas_extra.append(f"**{rotulo}** {valor}")

    blocos_texto = []
    for chave, rotulo in (("tracos", None), ("acoes", "Ações"), ("reacoes", "Reações"), ("magias", "Magias")):
        valor = (v.get(chave) or "").strip()
        if not valor:
            continue
        corpo = valor if chave == "magias" else _renderizar_trechos(valor)
        blocos_texto.append(f"**{rotulo}**\n\n{corpo}" if rotulo else corpo)

    dados_json = json.dumps(v, ensure_ascii=False)
    if "-->" in dados_json:
        raise ValueError("Um dos campos contém a sequência '-->', que não pode ser salva. Reescreva sem ela.")

    subtitulo = (v.get("subtitulo") or "").strip()

    partes = [
        _MARCADOR_INICIO.format(slug=slug),
        f"<!-- dados:statblock {dados_json} -->",
        '<div class="stat-block" markdown>',
        "",
        f"### {(v.get('nome') or '').strip() or 'NPC sem nome'} {{: #{slug} }}",
    ]
    if subtitulo:
        partes.append(f"*{subtitulo}*")
    partes += [
        "",
        "---",
        "",
        "| | |",
        "|---|---|",
        f"| **CA** | {(v.get('ca') or '').strip() or '—'} |",
        f"| **PV** | {(v.get('pv') or '').strip() or '—'} |",
        f"| **Deslocamento** | {(v.get('deslocamento') or '').strip() or '—'} |",
        "",
        f"| {rotulos_linha} |",
        f"|{separador_linha}|",
        f"| {valores_linha} |",
        "",
    ]
    if linhas_extra:
        partes += linhas_extra + [""]
    if blocos_texto:
        partes += ["---", "", "\n\n".join(blocos_texto), ""]
    partes += ["</div>", _MARCADOR_FIM.format(slug=slug)]
    return "\n".join(partes)


def ler_statblocks_da_pagina(path: Path) -> dict[str, dict]:
    """Lê todas as fichas de combate de uma página, pelo JSON embutido em cada uma."""
    texto = _ler(path)
    resultado: dict[str, dict] = {}
    for m in _MARCADOR_DADOS.finditer(texto):
        slug, dados_raw = m.group(1), m.group(2)
        try:
            resultado[slug] = json.loads(dados_raw)
        except json.JSONDecodeError:
            continue
    return resultado


def listar_statblocks(root: Path) -> list[dict]:
    """Toda ficha de combate do site, em qualquer página — para o seletor do Painel."""
    base = docs_dir(root)
    resultado = []
    for p in sorted(base.rglob("*.md")):
        blocos = ler_statblocks_da_pagina(p)
        if not blocos:
            continue
        rel = p.relative_to(base).as_posix()
        titulo_pagina = _titulo_do_arquivo(p)
        for slug, dados in blocos.items():
            resultado.append({
                "slug": slug,
                "nome": dados.get("nome") or slug,
                "pagina_rel_docs": rel,
                "pagina_titulo": titulo_pagina,
            })
    resultado.sort(key=lambda d: (d["pagina_rel_docs"], d["nome"]))
    return resultado


def salvar_statblock(
    root: Path, pagina_rel_docs: str, slug_antigo: str, valores: dict, ancora: str = "",
) -> str:
    """Cria ou atualiza uma ficha de combate na página indicada.

    Com `slug_antigo` preenchido, substitui aquele cartão (mesmo que o nome, e portanto o
    slug novo, tenha mudado). Sem `slug_antigo`, cria um cartão novo — inserido depois do
    primeiro trecho da página igual a `ancora`, ou no final do arquivo se `ancora` estiver
    vazia ou não for encontrada. Retorna o slug final do cartão salvo.
    """
    caminho = docs_dir(root) / pagina_rel_docs
    texto = _ler(caminho)
    nome = (valores.get("nome") or "").strip() or "npc"
    slug_base = slug_statblock(nome)

    if slug_antigo:
        novo_slug = slug_base
        bloco = renderizar_statblock(novo_slug, valores)
        padrao = re.search(
            rf"<!-- inicio:statblock:{re.escape(slug_antigo)} -->.*?<!-- fim:statblock:{re.escape(slug_antigo)} -->",
            texto, re.DOTALL,
        )
        if padrao:
            texto = texto[:padrao.start()] + bloco + texto[padrao.end():]
        else:
            texto = texto.rstrip("\n") + "\n\n" + bloco + "\n"
    else:
        novo_slug = slug_base
        contador = 2
        while re.search(rf"<!-- inicio:statblock:{re.escape(novo_slug)} -->", texto):
            novo_slug = f"{slug_base}-{contador}"
            contador += 1
        bloco = renderizar_statblock(novo_slug, valores)
        if ancora and ancora in texto:
            idx = texto.index(ancora) + len(ancora)
            resto = texto[idx:]
            m = re.search(r"\n#{1,6}\s", resto)
            insere_em = idx + (m.start() if m else len(resto))
            antes = texto[:insere_em].rstrip("\n")
            depois = texto[insere_em:]
            texto = antes + "\n\n" + bloco + "\n\n" + depois
        else:
            texto = texto.rstrip("\n") + "\n\n" + bloco + "\n"

    _escrever(caminho, texto)
    return novo_slug
