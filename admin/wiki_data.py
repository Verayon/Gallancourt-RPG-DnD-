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

# Módulos compartilhados com a geração do site (cálculos da ficha 5e e linha do tempo)
sys.path.insert(0, str(DEFAULT_ROOT / "hooks"))
import ficha5e  # noqa: E402
import linha_tempo  # noqa: E402


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


def registrar_sessao_na_linha_do_tempo(
    root: Path, numero: int, titulo: str, data_campanha: str, resumo: str,
    atualizacoes: list[tuple[Entidade, str]],
) -> int:
    """Cria o acontecimento da sessão na linha do tempo, com a nota de cada NPC/lugar marcado.

    Devolve o id do acontecimento (para o Mestre acrescentar mudanças de estado depois).
    """
    return salvar_evento(root, {
        "data": data_campanha,
        "sessao": numero,
        "titulo": titulo,
        "descricao": resumo,
        "notas": {e.rel_docs: nota for e, nota in atualizacoes},
    })


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
CAMPOS_FICHA_CIDADE = [
    ("populacao", "População", "texto"),
    ("defesas", "Defesas e guarnição", "textarea"),
]

TITULO_SECAO_FICHA_CIDADE = "Ficha da cidade"

# NPCs usam a ficha de D&D 5e (rota /ficha5e do Painel); esta ficha simples ficou só para cidades.
TIPOS_FICHA = {
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
    id_evento = registrar_sessao_na_linha_do_tempo(root, numero, titulo, data_campanha, resumo, atualizacoes)
    nav_ok = adicionar_sessao_ao_nav(root, numero)
    build_ok, build_saida = validar_build(root)

    return {
        "numero": numero,
        "arquivo": str(caminho_sessao.relative_to(root)),
        "paginas_atualizadas": [e.rel_docs for e, _ in atualizacoes],
        "id_evento": id_evento,
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


# --------------------------------------------------------------------------
# Inserção no menu (nav) do mkdocs.yml
# --------------------------------------------------------------------------

def _indentacao(linha: str) -> int:
    return len(linha) - len(linha.lstrip(" "))


def _fim_do_bloco(linhas: list[str], inicio: int) -> int:
    """Índice da primeira linha depois do bloco que começa em `inicio` (por indentação)."""
    base = _indentacao(linhas[inicio])
    pos = inicio + 1
    while pos < len(linhas) and (not linhas[pos].strip() or _indentacao(linhas[pos]) > base):
        pos += 1
    while pos - 1 > inicio and not linhas[pos - 1].strip():
        pos -= 1
    return pos


def _titulo_nav(titulo: str) -> str:
    """Título entre aspas, seguro para YAML."""
    return json.dumps(titulo, ensure_ascii=False)


def _inserir_no_nav(root: Path, cabecalho: str, nova_linha: str, subgrupo: str = "") -> bool:
    """Insere `nova_linha` no fim do bloco `cabecalho` do nav (ex.: '      - Sessões:').

    Com `subgrupo`, procura dentro do bloco um grupo com esse título (ex.: 'Dodixie') e insere
    no fim dele; se o grupo não existir, cria-o no fim do bloco.
    """
    caminho = mkdocs_yml(root)
    linhas = _ler(caminho).split("\n")
    try:
        inicio = linhas.index(cabecalho)
    except ValueError:
        return False
    fim = _fim_do_bloco(linhas, inicio)
    indent_item = " " * (_indentacao(linhas[inicio]) + 4)
    if subgrupo:
        alvo = None
        for i in range(inicio + 1, fim):
            if linhas[i].rstrip() in (f"{indent_item}- {subgrupo}:", f"{indent_item}- {_titulo_nav(subgrupo)}:"):
                alvo = i
                break
        if alvo is None:
            linhas[fim:fim] = [f"{indent_item}- {_titulo_nav(subgrupo)}:", f"{indent_item}    {nova_linha}"]
        else:
            linhas.insert(_fim_do_bloco(linhas, alvo), f"{indent_item}    {nova_linha}")
    else:
        linhas.insert(fim, f"{indent_item}{nova_linha}")
    _escrever(caminho, "\n".join(linhas))
    return True


# --------------------------------------------------------------------------
# Novo NPC — botão "Adicionar NPC" da tabela de NPCs
# --------------------------------------------------------------------------

CABECALHO_NAV_NPCS = "      - NPCs:"

# (chave, rótulo, obrigatório)
CAMPOS_NPC_NOVO = [
    ("nome", "Nome", True),
    ("titulo", "Título (ex.: Marquesa, Capitão, Mestre)", False),
    ("raca", "Raça", False),
    ("cidade", "Cidade", False),
    ("afiliacao", "Afiliação (casa, facção, organização)", False),
    ("resumo", "Resumo de uma linha (aparece na tabela)", False),
]


def _front_matter(texto: str) -> tuple[dict, str]:
    import yaml

    m = re.match(r"---\n(.*?)\n---\n?(.*)", texto, re.S)
    if not m:
        return {}, texto
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def _com_front_matter(meta: dict, corpo: str) -> str:
    import yaml

    return "---\n" + yaml.dump(meta, allow_unicode=True, sort_keys=False, width=1000) + "---\n" + corpo


def _link_se_existir(root: Path, nome: str, lista: list[Entidade], pagina_rel: str) -> str:
    """Devolve `[nome](caminho)` se houver página com esse título; senão, o texto puro."""
    for e in lista:
        if e.titulo.casefold() == nome.casefold() or e.titulo.casefold().endswith(" " + nome.casefold()):
            destino = os.path.relpath(docs_dir(root) / e.rel_docs, start=(docs_dir(root) / pagina_rel).parent)
            return f"[{nome}]({Path(destino).as_posix()})"
    return nome


def _retrato_relativo(destino_imagem: Path, root: Path, pagina_rel: str) -> str:
    return Path(os.path.relpath(destino_imagem, start=(docs_dir(root) / pagina_rel).parent)).as_posix()


def criar_npc(root: Path, valores: dict, imagem: tuple[str, bytes] | None = None, ficha: dict | None = None) -> dict:
    """Cria docs/personagens/<slug>.md no padrão das páginas de NPC e o adiciona ao menu.

    `imagem`, se informada, é (nome_original, conteúdo) do retrato.
    """
    nome = (valores.get("nome") or "").strip()
    if not nome:
        raise ValueError("O NPC precisa de um nome.")
    slug = slug_statblock(nome)
    rel = f"personagens/{slug}.md"
    caminho = docs_dir(root) / rel
    if caminho.exists():
        raise ValueError(f"Já existe uma página para esse nome: docs/{rel}")

    campos = {chave: (valores.get(chave) or "").strip() for chave, _, _ in CAMPOS_NPC_NOVO}
    retrato = ""
    if imagem and imagem[0]:
        destino, _ = salvar_imagem(root, rel, "personagens", imagem[0], imagem[1])
        retrato = _retrato_relativo(destino, root, rel)

    if ficha and ficha.get("raca") and not campos["raca"]:
        campos["raca"] = ficha["raca"]
    ficha_rapida = {}
    if campos["titulo"]:
        ficha_rapida["Título"] = campos["titulo"]
    if campos["raca"]:
        ficha_rapida["Raça"] = campos["raca"]
    if campos["cidade"]:
        ficha_rapida["Cidade"] = _link_se_existir(root, campos["cidade"], listar_cidades(root), rel)
    if campos["afiliacao"]:
        ficha_rapida["Afiliação"] = _link_se_existir(root, campos["afiliacao"], listar_faccoes(root), rel)

    meta = {
        "tags": ["Personagens"] + ([campos["cidade"]] if campos["cidade"] else []),
        "hide": ["toc"],
        "npc": {
            "titulo": campos["titulo"] or "—",
            "raca": campos["raca"] or "—",
            "cidade": campos["cidade"] or "—",
            "afiliacao": campos["afiliacao"] or "—",
            "resumo": campos["resumo"],
            "retrato": retrato,
            "ficha": ficha_rapida,
        },
    }
    if ficha:
        meta["ficha5e"] = ficha
    descricao = (valores.get("descricao") or "").strip()
    corpo = "\n".join([
        "",
        f"# {nome}",
        "",
        descricao or campos["resumo"] or "*(Descrição a preencher.)*",
        "",
        '!!! question "Em aberto"',
        "    História, motivações e relações deste NPC ainda não foram detalhadas.",
        "",
    ])
    _escrever(caminho, _com_front_matter(meta, corpo))

    grupo = campos["cidade"] or "Outros"
    nav_ok = _inserir_no_nav(root, CABECALHO_NAV_NPCS, f"- {_titulo_nav(nome)}: {rel}", subgrupo=grupo)
    build_ok, build_saida = validar_build(root)
    return {"arquivo": f"docs/{rel}", "rel_docs": rel, "nav_ok": nav_ok, "build_ok": build_ok, "build_saida": build_saida}


def definir_retrato(root: Path, npc_rel_docs: str, nome_original: str, conteudo: bytes) -> str:
    """Salva a imagem enviada e a define como retrato do NPC (campo `npc.retrato`)."""
    caminho = docs_dir(root) / npc_rel_docs
    meta, corpo = _front_matter(_ler(caminho))
    if not isinstance(meta.get("npc"), dict):
        raise ValueError("Essa página não tem o bloco `npc:` no topo.")
    destino, _ = salvar_imagem(root, npc_rel_docs, "personagens", nome_original, conteudo)
    meta["npc"]["retrato"] = _retrato_relativo(destino, root, npc_rel_docs)
    _escrever(caminho, _com_front_matter(meta, corpo))
    return meta["npc"]["retrato"]


# --------------------------------------------------------------------------
# Nova sessão — botão "Nova sessão" da página Mestre → Sessões
# --------------------------------------------------------------------------

CABECALHO_NAV_SESSOES = "      - Sessões:"

# (chave, rótulo na ficha da sessão)
CAMPOS_SESSAO_NOVA = [
    ("jogadores", "Jogadores"),
    ("nivel", "Nível sugerido"),
    ("duracao", "Duração estimada"),
    ("tom", "Tom"),
    ("local", "Local"),
    ("missao", "Missão oferecida"),
    ("recompensa", "Recompensa"),
]


def pasta_sessoes(root: Path) -> Path:
    return docs_dir(root) / "mestre" / "sessoes"


def proxima_sessao_preparo(root: Path) -> int:
    numeros = []
    for p in pasta_sessoes(root).glob("sessao-*.md"):
        m = re.match(r"sessao-(\d+)", p.stem)
        if m:
            numeros.append(int(m.group(1)))
    return max(numeros) + 1 if numeros else 0


def _modelo_sessao(numero: int, titulo: str, valores: dict) -> str:
    """Página de sessão com o mesmo layout da Sessão 0: ficha + abas."""
    ficha = "\n".join(
        f"| **{rotulo}** | {(valores.get(chave) or '').strip() or '—'} |" for chave, rotulo in CAMPOS_SESSAO_NOVA
    )
    resumo = (valores.get("resumo") or "").strip() or "*(Resumo da sessão a escrever.)*"
    resumo = "\n".join("    " + l if l.strip() else "" for l in resumo.splitlines())
    vazio = "    *(a preencher)*"
    return f"""---
tags:
  - Mestre
  - Sessão
sessao:
  numero: {numero}
---

# Sessão {numero} — {titulo}

!!! warning "Conteúdo de campanha, não cânone do mundo"
    Esta página é um roteiro de preparação de sessão — não documenta o mundo pré-campanha como o
    resto da wiki. Depois de jogada, registre o que aconteceu pelo [Painel do Mestre](../painel.md)
    ou pelo [modelo manual](../registro-manual-de-sessao.md); só promova para o cânone do mundo o
    que você decidir manter como fato definitivo.

<div class="ficha" markdown>

| | |
|---|---|
{ficha}

</div>

=== "Resumo"

    ## Resumo rápido

{resumo}

    ## Antes de sentar à mesa

{vazio}

=== "NPCs"

    ## Aliados

{vazio}

    ## Inimigos

{vazio}

    ## Fichas de combate

    Crie as fichas pela aba **Ficha de combate** do [Painel do Mestre](../painel.md), escolhendo
    esta página.

    ## Figurantes

{vazio}

=== "Cenas"

    ### Cena 1

{vazio}

=== "Loot & Pistas"

    ## Recompensa

{vazio}

    ## Itens encontrados

{vazio}

=== "Lugares"

{vazio}

=== "Segredo do Mestre"

    ## Quem está por trás

{vazio}

    ## Pistas para distribuir

{vazio}

## Depois da sessão

- Registre o que realmente aconteceu pelo [Painel do Mestre](../painel.md) (ou o
  [modelo manual](../registro-manual-de-sessao.md)) — isso cria uma entrada no
  [Diário de Sessões](../../diario/index.md).
- Se algum elemento desta sessão virar fato definitivo do mundo, formalize-o nas páginas da wiki.
"""


def criar_sessao_preparo(root: Path, numero: int, titulo: str, valores: dict) -> dict:
    """Cria docs/mestre/sessoes/sessao-<n>-<slug>.md e o adiciona ao menu, em Mestre → Sessões."""
    titulo = titulo.strip()
    if not titulo:
        raise ValueError("A sessão precisa de um título.")
    if any(re.match(rf"sessao-{numero}(-|$)", p.stem) for p in pasta_sessoes(root).glob("sessao-*.md")):
        raise ValueError(f"Já existe uma página para a Sessão {numero}.")
    rel = f"mestre/sessoes/sessao-{numero}-{slug_statblock(titulo)}.md"
    _escrever(docs_dir(root) / rel, _modelo_sessao(numero, titulo, valores))
    nav_ok = _inserir_no_nav(root, CABECALHO_NAV_SESSOES, f"- {_titulo_nav(f'Sessão {numero} — {titulo}')}: {rel}")
    build_ok, build_saida = validar_build(root)
    return {"arquivo": f"docs/{rel}", "rel_docs": rel, "nav_ok": nav_ok, "build_ok": build_ok, "build_saida": build_saida}


# --------------------------------------------------------------------------
# Ficha de personagem D&D 5e (bloco `ficha5e:` da página do NPC)
# --------------------------------------------------------------------------

def ler_ficha5e(root: Path, npc_rel_docs: str) -> dict:
    meta, _ = _front_matter(_ler(docs_dir(root) / npc_rel_docs))
    return meta.get("ficha5e") or {}


def salvar_ficha5e(root: Path, npc_rel_docs: str, ficha: dict) -> None:
    """Grava a ficha no front matter. Ficha vazia remove o bloco."""
    caminho = docs_dir(root) / npc_rel_docs
    meta, corpo = _front_matter(_ler(caminho))
    if not isinstance(meta.get("npc"), dict):
        raise ValueError("Essa página não tem o bloco `npc:` no topo — não é uma página de NPC.")
    if ficha:
        meta["ficha5e"] = ficha
        if ficha.get("raca") and meta["npc"].get("raca") in (None, "", "—"):
            meta["npc"]["raca"] = ficha["raca"]
    else:
        meta.pop("ficha5e", None)
    _escrever(caminho, _com_front_matter(meta, corpo))


# --------------------------------------------------------------------------
# Linha do tempo (dados/linha-do-tempo.yml)
# --------------------------------------------------------------------------

def listar_eventos(root: Path) -> list[dict]:
    return linha_tempo.ordenar(linha_tempo.carregar(root))


def paginas_rastreaveis(root: Path) -> list[Entidade]:
    """NPCs, cidades e facções — o que pode aparecer numa linha do tempo."""
    return listar_npcs(root) + listar_cidades(root) + listar_faccoes(root)


def salvar_evento(root: Path, dados: dict, id_evento: int | None = None) -> int:
    """Cria (sem id) ou substitui (com id) um acontecimento. Devolve o id."""
    if not (dados.get("titulo") or "").strip():
        raise ValueError("O acontecimento precisa de um título.")
    validas = {e.rel_docs for e in paginas_rastreaveis(root)}
    paginas = set(dados.get("envolvidos") or []) | {m["pagina"] for m in dados.get("mudancas") or []}
    paginas |= set((dados.get("notas") or {}).keys())
    invalidas = sorted(p for p in paginas if p not in validas)
    if invalidas:
        raise ValueError("Página desconhecida: " + ", ".join(invalidas))

    eventos = linha_tempo.carregar(root)
    evento = {"id": id_evento or (max((int(e.get("id") or 0) for e in eventos), default=0) + 1)}
    for chave in ("data", "sessao", "titulo", "descricao", "envolvidos", "notas", "mudancas"):
        valor = dados.get(chave)
        if valor not in (None, "", [], {}):
            evento[chave] = valor
    if id_evento:
        if not any(int(e.get("id") or 0) == id_evento for e in eventos):
            raise ValueError(f"Acontecimento {id_evento} não encontrado.")
        eventos = [evento if int(e.get("id") or 0) == id_evento else e for e in eventos]
    else:
        eventos.append(evento)
    linha_tempo.salvar(root, eventos)
    return evento["id"]


def apagar_evento(root: Path, id_evento: int) -> None:
    eventos = linha_tempo.carregar(root)
    linha_tempo.salvar(root, [e for e in eventos if int(e.get("id") or 0) != id_evento])
