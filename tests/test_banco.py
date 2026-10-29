"""Testes do banco de dados relacional (admin/banco.py) — a fundação da Etapa B (ver
ARQUITETURA.md). Cada teste usa um banco SQLite temporário próprio (`tmp_path`), nunca o banco
real do autor, e cria o schema direto por `Base.metadata.create_all` (mais rápido que rodar o
Alembic em cada teste; o Alembic continua sendo a fonte de verdade do schema em uso real).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "admin"))

import banco  # noqa: E402


def _sessao_de_teste(tmp_path):
    engine = banco.criar_engine(tmp_path)
    banco.Base.metadata.create_all(engine)
    return banco.fabrica_sessao(engine)()


def test_obter_ou_criar_campanha_e_idempotente(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        primeira = banco.obter_ou_criar_campanha(sessao, "Crônicas de Gallancourt", "2014")
        segunda = banco.obter_ou_criar_campanha(sessao, "Outro nome", "2024")

        assert primeira.id == segunda.id
        assert segunda.nome == "Crônicas de Gallancourt"  # não sobrescreve na segunda chamada
        assert sessao.query(banco.Campanha).count() == 1


def test_adicionar_e_listar_fontes(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        banco.adicionar_fonte(sessao, "Player's Handbook", "PHB", "2014")
        banco.adicionar_fonte(sessao, "Dungeon Master's Guide", "DMG", "2014")

        fontes = banco.listar_fontes(sessao)

        assert [f.abreviacao for f in fontes] == ["DMG", "PHB"]  # ordenado por nome


def test_apagar_fonte(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        fonte = banco.adicionar_fonte(sessao, "Xanathar's Guide to Everything", "XGE", "2014")

        banco.apagar_fonte(sessao, fonte.id)

        assert banco.listar_fontes(sessao) == []


def test_semear_e_reproduzivel(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        banco.semear(sessao)
        banco.semear(sessao)  # rodar de novo não deve duplicar nada

        assert sessao.query(banco.Campanha).count() == 1
        assert len(banco.listar_fontes(sessao)) == len(banco.FONTES_SEED)
