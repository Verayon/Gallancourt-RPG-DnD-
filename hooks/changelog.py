"""Changelog do projeto: o que mudou em cada versão.

Fonte única: `dados/changelog.yml` (fora de `docs/`, não é publicado como arquivo). Cada versão
tem um número, uma data e a lista do que mudou. A versão mais recente (a última da lista) é "a
versão atual" — mostrada no selo no canto inferior esquerdo do site. A versão 1.0 só existe
quando o Mestre decidir, pelo Painel, que o projeto está pronto; até então os números ficam
abaixo de 1.0.

Usado em dois lugares:

- `hooks/gallancourt.py` (geração do site) monta a página geral do changelog e o selo de versão
  que aparece em todas as páginas;
- `admin/wiki_data.py` (Painel do Mestre) acrescenta e apaga versões.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ARQUIVO = Path("dados") / "changelog.yml"

CABECALHO_ARQUIVO = """\
# Changelog de Crônicas de Gallancourt.
#
# Edite pelo Painel do Mestre (aba "Changelog"). A última versão da lista é "a versão atual",
# mostrada no selo no canto inferior esquerdo do site. A versão 1.0 só existe quando o projeto
# for considerado pronto — até lá, use números abaixo de 1.0 (0.1, 0.2...).
#
# Campos de cada versão:
#   id        número único (o Painel preenche)
#   versao    rótulo da versão (ex.: "0.1")
#   data      data real do lançamento (ex.: "2026-10-28")
#   mudancas  lista de textos, um por mudança
"""


def caminho(raiz: Path) -> Path:
    return Path(raiz) / ARQUIVO


def carregar(raiz: Path) -> list[dict]:
    arq = caminho(raiz)
    if not arq.exists():
        return []
    dados = yaml.safe_load(arq.read_text(encoding="utf-8")) or {}
    versoes = dados.get("versoes") or []
    return [v for v in versoes if isinstance(v, dict)]


def salvar(raiz: Path, versoes: list[dict]) -> None:
    arq = caminho(raiz)
    arq.parent.mkdir(parents=True, exist_ok=True)
    corpo = yaml.dump({"versoes": versoes}, allow_unicode=True, sort_keys=False, width=100)
    arq.write_text(CABECALHO_ARQUIVO + "\n" + corpo, encoding="utf-8")


def versao_atual(versoes: list[dict]) -> dict | None:
    """A última versão lançada (a mais recente, lida pela ordem de inclusão da lista)."""
    return versoes[-1] if versoes else None


def pagina_geral(versoes: list[dict]) -> str:
    if not versoes:
        return "*Nenhuma versão lançada ainda — o projeto está em desenvolvimento.*"
    partes = []
    for v in reversed(versoes):
        cabeca = f"## Versão {v.get('versao') or '?'}"
        if v.get("data"):
            cabeca += f" — {v['data']}"
        partes.append(cabeca)
        partes.append("")
        mudancas = v.get("mudancas") or []
        if mudancas:
            partes += [f"- {m}" for m in mudancas]
        else:
            partes.append("*(sem detalhes registrados)*")
        partes.append("")
    return "\n".join(partes).rstrip() + "\n"
