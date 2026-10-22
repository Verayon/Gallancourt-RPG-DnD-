"""Lógica de leitura e escrita da wiki, usada pelo Painel do Mestre (admin/app.py).

Isolado do Flask de propósito: pode ser testado chamando as funções diretamente, sem subir um
servidor. Todas as funções que escrevem arquivo recebem `root` (a raiz do projeto, onde ficam
`docs/` e `mkdocs.yml`) para permitir apontar para uma cópia de teste em vez do projeto real.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
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
