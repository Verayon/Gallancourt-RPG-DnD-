"""Migração de uso único: cria um `Personagem`/`Ficha` vazios no banco para cada NPC nomeado e
jogador existente, e acrescenta a seção `## Ficha de combate` (com o marcador dinâmico) na
página de cada um, quando ainda não existir (ver admin/banco.py, admin/personagens_api.py e
ARQUITETURA.md — mesmo tratamento já dado aos monstros em 2026-10-30, agora estendido a NPC/
jogador, conforme o autor pediu).

O que faz, nesta ordem:
1. Lê cada `docs/personagens/*.md` (fora de `genericos/`, de propósito — ver
   docs/mestre/manutencao-do-canone.md) e cada `docs/mestre/jogadores/*.md`.
2. Para cada um, cria `Personagem(tipo="npc"|"jogador")` + `Ficha(is_base=True)` com os valores
   padrão — não há nenhuma ficha de combate preenchida hoje pra migrar (confirmado: 0 de 24 NPCs
   e 0 de 7 jogadores têm `<!-- dados:statblock -->` preenchido).
3. Defensivamente, lê qualquer valor já salvo pela Biografia antiga (`## Biografia`, marcadores
   `<!-- campo:x -->` — ver admin/wiki_data.py::ler_campos_ficha) e copia pro `Personagem` novo,
   caso algo tenha sido preenchido entre a escrita deste script e sua execução.
4. Acrescenta `## Ficha de combate` com `<!-- personagem:ficha-dinamica -->` no fim da página,
   se essa seção ainda não existir.

Rode com `--root <pasta>` para testar numa cópia antes de rodar no projeto real (nunca roda em
cima do real sem confirmar — ver `--confirmar`).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROJETO / "admin"))

import banco  # noqa: E402
import personagens_api as pa  # noqa: E402
import wiki_data as wd  # noqa: E402

SECAO_FICHA = "## Ficha de combate\n\n<!-- personagem:ficha-dinamica -->\n"


def _tem_secao_ficha_de_combate(texto: str) -> bool:
    return bool(re.search(r"^##\s+Ficha de combate\s*$", texto, re.M))


def _migrar_entidade(sessao, root: Path, entidade, tipo: str) -> None:
    path = wd.docs_dir(root) / entidade.rel_docs
    personagem = pa.obter_personagem(sessao, tipo, entidade.slug)
    if personagem is None:
        personagem = pa.criar_personagem(sessao, tipo, entidade.slug, entidade.titulo)
        sessao.add(banco.Ficha(personagem_id=personagem.id, rotulo="Base", is_base=True))
        sessao.commit()
        print(f"  + criado: {tipo}/{entidade.slug}")
    else:
        print(f"  = já existia: {tipo}/{entidade.slug}")

    valores_bio = wd.ler_campos_ficha(path, wd.CAMPOS_FICHA_PERSONAGEM)
    campos = {k: v for k, v in valores_bio.items() if v and k in pa.CAMPOS_PERSONAGEM_EDITAVEIS}
    if campos:
        pa.atualizar_personagem(sessao, personagem, campos)
        print(f"    biografia copiada: {', '.join(campos.keys())}")

    texto = path.read_text(encoding="utf-8")
    if not _tem_secao_ficha_de_combate(texto):
        novo_texto = texto.rstrip("\n") + "\n\n" + SECAO_FICHA
        path.write_text(novo_texto, encoding="utf-8")
        print("    seção 'Ficha de combate' acrescentada")


def migrar(root: Path) -> None:
    engine = banco.criar_engine(root)
    Sessao = banco.fabrica_sessao(engine)
    with Sessao() as sessao:
        print("NPCs nomeados:")
        for npc in wd.listar_npcs(root):
            _migrar_entidade(sessao, root, npc, "npc")

        print("Jogadores:")
        for jogador in wd.listar_jogadores(root):
            _migrar_entidade(sessao, root, jogador, "jogador")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=RAIZ_PROJETO, help="raiz do projeto (padrão: o projeto real)")
    parser.add_argument("--confirmar", action="store_true", help="necessário para rodar em cima da raiz real do projeto")
    args = parser.parse_args()

    root = args.root.resolve()
    if root == RAIZ_PROJETO and not args.confirmar:
        print("Rodando sobre a raiz REAL do projeto exige --confirmar (ou use --root pra testar numa cópia).")
        raise SystemExit(1)

    migrar(root)


if __name__ == "__main__":
    main()
