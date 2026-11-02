"""Roadmap do projeto: o que falta implementar no site.

Fonte única: `dados/roadmap.yml` (fora de `docs/`, não é publicado como arquivo). Cada item tem
uma descrição, uma prioridade, uma funcionalidade (área do site que ele afeta) e, opcionalmente,
um responsável — lista aberta, dá para acrescentar itens à vontade.

Usado em três lugares:

- `admin/app.py` (API `/api/roadmap`, ver `docs/javascripts/roadmap.js`) lê/escreve os itens
  direto na página pública, em Modo Mestre — sem passar por `mkdocs build`;
- `admin/wiki_data.py` (Painel do Mestre, formulário próprio) também acrescenta, edita e apaga
  itens, pelas mesmas funções;
- `hooks/gallancourt.py` (geração do site) só troca o marcador de `docs/roadmap/index.md` por
  uma raiz vazia que o widget JS preenche — não lê mais os itens no build.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ARQUIVO = Path("dados") / "roadmap.yml"

CABECALHO_ARQUIVO = """\
# Roadmap de Crônicas de Gallancourt — o que falta implementar.
#
# Edite em Modo Mestre direto na página do Roadmap, ou pelo Painel do Mestre (aba "Roadmap").
# Lista aberta: acrescente itens à vontade.
#
# Campos de cada item:
#   id          número único (preenchido automaticamente)
#   item        descrição do que falta fazer
#   prioridade  Alta, Média ou Baixa
#   tipo        UI, Engine, Conteúdo, Infra ou Dados
#   status      Planejado, Em andamento ou Concluído
#   responsavel quem está cuidando do item (texto livre; pode ficar em branco)
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
