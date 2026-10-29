"""Roadmap do projeto: o que falta implementar no site.

Fonte única: `dados/roadmap.yml` (fora de `docs/`, não é publicado como arquivo). Cada item tem
uma descrição, uma prioridade e uma funcionalidade (área do site que ele afeta) — lista aberta,
dá para acrescentar itens à vontade pelo Painel.

Usado em dois lugares:

- `hooks/gallancourt.py` (geração do site) monta a tabela em `docs/roadmap/index.md`;
- `admin/wiki_data.py` (Painel do Mestre) acrescenta, edita e apaga itens.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ARQUIVO = Path("dados") / "roadmap.yml"

CABECALHO_ARQUIVO = """\
# Roadmap de Crônicas de Gallancourt — o que falta implementar.
#
# Edite pelo Painel do Mestre (aba "Roadmap"). Lista aberta: acrescente itens à vontade.
#
# Campos de cada item:
#   id          número único (o Painel preenche)
#   item        descrição do que falta fazer
#   prioridade  Alta, Média ou Baixa
#   tipo        UI, Engine, Conteúdo, Infra ou Dados
#   status      Planejado, Em andamento ou Concluído
"""

PRIORIDADES = ["Alta", "Média", "Baixa"]
TIPOS = ["UI", "Engine", "Conteúdo", "Infra", "Dados"]
STATUS = ["Planejado", "Em andamento", "Concluído"]

_RANK_PRIORIDADE = {p: i for i, p in enumerate(PRIORIDADES)}


def caminho(raiz: Path) -> Path:
    return Path(raiz) / ARQUIVO


def carregar(raiz: Path) -> list[dict]:
    arq = caminho(raiz)
    if not arq.exists():
        return []
    dados = yaml.safe_load(arq.read_text(encoding="utf-8")) or {}
    itens = dados.get("itens") or []
    return [i for i in itens if isinstance(i, dict)]


def salvar(raiz: Path, itens: list[dict]) -> None:
    arq = caminho(raiz)
    arq.parent.mkdir(parents=True, exist_ok=True)
    corpo = yaml.dump({"itens": itens}, allow_unicode=True, sort_keys=False, width=100)
    arq.write_text(CABECALHO_ARQUIVO + "\n" + corpo, encoding="utf-8")


def ordenar(itens: list[dict]) -> list[dict]:
    """Prioridade (Alta primeiro) e, em caso de igual, o mais antigo primeiro."""
    def chave(i):
        return (_RANK_PRIORIDADE.get(i.get("prioridade"), len(PRIORIDADES)), int(i.get("id") or 0))
    return sorted(itens, key=chave)


def _celula(valor) -> str:
    return str(valor if valor not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


_CLASSE_PRIORIDADE = {"Alta": "alta", "Média": "media", "Baixa": "baixa"}
_CLASSE_STATUS = {"Planejado": "planejado", "Em andamento": "andamento", "Concluído": "concluido"}


def _selo(texto: str | None, classes: dict) -> str:
    if not texto:
        return "—"
    classe = classes.get(texto, "neutro")
    return f'<span class="selo selo--{classe}">{texto}</span>'


def tabela(itens: list[dict]) -> str:
    if not itens:
        return "*Nada no roadmap por enquanto.*"
    linhas = ordenar(itens)
    cabecalho = "| Item | Prioridade | Funcionalidade | Status |"
    separador = "|---|---|---|---|"
    corpo = [
        f"| {_celula(i.get('item'))} | {_selo(i.get('prioridade'), _CLASSE_PRIORIDADE)} | "
        f"{_celula(i.get('tipo'))} | {_selo(i.get('status'), _CLASSE_STATUS)} |"
        for i in linhas
    ]
    partes = [
        '<div class="roadmap-ferramentas" markdown>',
        "",
        '<input type="search" class="roadmap-busca" placeholder="Filtrar por texto…" aria-label="Filtrar">',
        '<span class="roadmap-contagem" aria-live="polite"></span>',
        "",
        "</div>",
        "",
        '<div class="roadmap-tabela" markdown>',
        "",
        cabecalho,
        separador,
        *corpo,
        "",
        "</div>",
    ]
    return "\n".join(partes)
