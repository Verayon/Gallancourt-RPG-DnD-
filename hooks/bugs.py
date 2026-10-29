"""Bugs reportados no site.

Fonte única: `dados/bugs.yml` (fora de `docs/`, não é publicado como arquivo). Qualquer pessoa
pode reportar um bug pelo botão "Reportar bug", visível em qualquer página do site (abre
`/bug/novo`, servido pelo Painel). Cada bug tem uma área, uma descrição e um status —
"Aguardando" até alguém (hoje, um agente do Claude Code, a pedido do Mestre) investigar,
corrigir e testar a correção; aí passa para "Resolvido".

Usado em dois lugares:

- `hooks/gallancourt.py` (geração do site) monta a tabela em `docs/configuracoes/bugs.md` e o
  botão flutuante de report, presente em toda página;
- `admin/wiki_data.py` (Painel do Mestre) cria bugs e muda o status.
"""
from __future__ import annotations

import datetime
from pathlib import Path

import yaml

ARQUIVO = Path("dados") / "bugs.yml"

CABECALHO_ARQUIVO = """\
# Bugs reportados em Crônicas de Gallancourt.
#
# Criados pelo botão "Reportar bug" do site (qualquer página) e processados pelo Painel do
# Mestre (aba "Bugs"). Status: Aguardando (ainda não corrigido) ou Resolvido.
#
# Campos de cada bug:
#   id             número único (o Painel preenche)
#   area           parte do site afetada
#   descricao      o que está errado, descrito por quem reportou
#   status         Aguardando ou Resolvido
#   criado_em      data em que foi reportado (AAAA-MM-DD)
#   resolvido_em   data em que foi corrigido (AAAA-MM-DD, vazio até ser resolvido)
#   nota_resolucao o que foi feito para corrigir (preenchido ao marcar como Resolvido)
"""

AREAS = [
    "Wiki (conteúdo e páginas)",
    "Painel do Mestre",
    "Sessão ao vivo / Iniciativa",
    "Busca e navegação",
    "Outro",
]

STATUS = ["Aguardando", "Resolvido"]


def caminho(raiz: Path) -> Path:
    return Path(raiz) / ARQUIVO


def carregar(raiz: Path) -> list[dict]:
    arq = caminho(raiz)
    if not arq.exists():
        return []
    dados = yaml.safe_load(arq.read_text(encoding="utf-8")) or {}
    bugs = dados.get("bugs") or []
    return [b for b in bugs if isinstance(b, dict)]


def salvar(raiz: Path, bugs: list[dict]) -> None:
    arq = caminho(raiz)
    arq.parent.mkdir(parents=True, exist_ok=True)
    corpo = yaml.dump({"bugs": bugs}, allow_unicode=True, sort_keys=False, width=100)
    arq.write_text(CABECALHO_ARQUIVO + "\n" + corpo, encoding="utf-8")


def criar(raiz: Path, area: str, descricao: str) -> int:
    bugs = carregar(raiz)
    novo_id = max((int(b.get("id") or 0) for b in bugs), default=0) + 1
    bugs.append({
        "id": novo_id,
        "area": area or "Outro",
        "descricao": descricao,
        "status": "Aguardando",
        "criado_em": datetime.date.today().isoformat(),
        "resolvido_em": "",
        "nota_resolucao": "",
    })
    salvar(raiz, bugs)
    return novo_id


def marcar_resolvido(raiz: Path, id_bug: int, nota: str) -> bool:
    bugs = carregar(raiz)
    for b in bugs:
        if int(b.get("id") or 0) == id_bug:
            b["status"] = "Resolvido"
            b["resolvido_em"] = datetime.date.today().isoformat()
            b["nota_resolucao"] = nota
            salvar(raiz, bugs)
            return True
    return False


def reabrir(raiz: Path, id_bug: int) -> bool:
    bugs = carregar(raiz)
    for b in bugs:
        if int(b.get("id") or 0) == id_bug:
            b["status"] = "Aguardando"
            b["resolvido_em"] = ""
            salvar(raiz, bugs)
            return True
    return False


def ordenar(bugs: list[dict]) -> list[dict]:
    """Mais recentes primeiro."""
    return sorted(bugs, key=lambda b: int(b.get("id") or 0), reverse=True)


def _celula(valor) -> str:
    return str(valor if valor not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


_CLASSE_STATUS = {"Aguardando": "aguardando", "Resolvido": "resolvido"}


def _selo_status(status: str | None) -> str:
    classe = _CLASSE_STATUS.get(status, "neutro")
    return f'<span class="selo selo--{classe}">{status or "—"}</span>'


def tabela(bugs: list[dict]) -> str:
    if not bugs:
        return "*Nenhum bug reportado ainda.*"
    linhas = ordenar(bugs)
    cabecalho = "| # | Área | Descrição | Status | Reportado em |"
    separador = "|---|---|---|---|---|"
    corpo = [
        f"| {b.get('id')} | {_celula(b.get('area'))} | {_celula(b.get('descricao'))} | "
        f"{_selo_status(b.get('status'))} | {_celula(b.get('criado_em'))} |"
        for b in linhas
    ]
    partes = [
        '<div class="bug-ferramentas" markdown>',
        "",
        '<input type="search" class="bug-busca" placeholder="Filtrar por texto…" aria-label="Filtrar">',
        '<span class="bug-contagem" aria-live="polite"></span>',
        "",
        "</div>",
        "",
        '<div class="bug-tabela" markdown>',
        "",
        cabecalho,
        separador,
        *corpo,
        "",
        "</div>",
    ]
    return "\n".join(partes)
