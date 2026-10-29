"""Banco de dados relacional (SQLite) — fundação para dados operacionais que precisam de consulta
de verdade, ao contrário do Markdown/YAML (que continuam sendo a fonte do lore e dos registros já
em produção: fichas de combate, NPCs, linha do tempo, Changelog, Roadmap — ver ARQUITETURA.md).

Isolado do Flask de propósito, como wiki_data.py/sessao_viva.py: toda função que precisa do banco
recebe uma `Session` já aberta (não abre/fecha conexão sozinha), e `criar_engine` recebe `root`
para permitir apontar para uma cópia de teste em vez do banco real do autor.
"""
from __future__ import annotations

import datetime
from pathlib import Path

from sqlalchemy import DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Campanha(Base):
    __tablename__ = "campanhas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    sistema_regras: Mapped[str] = mapped_column(String(10))  # "2014" ou "2024"
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.UTC)
    )


class Fonte(Base):
    __tablename__ = "fontes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    abreviacao: Mapped[str] = mapped_column(String(20))
    edicao: Mapped[str] = mapped_column(String(10))  # "2014" ou "2024"


def caminho_banco(root: Path) -> Path:
    return root / "dados" / "gallancourt.db"


def criar_engine(root: Path):
    """Engine SQLite apontando para `dados/gallancourt.db` dentro de `root`. Não cria as tabelas
    sozinho — isso é trabalho das migrações do Alembic (ver alembic/) em uso real, ou de
    `Base.metadata.create_all(engine)` direto em testes, que não precisam de histórico de
    migração."""
    caminho = caminho_banco(root)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{caminho}")


def fabrica_sessao(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine)


def obter_ou_criar_campanha(sessao: Session, nome: str, sistema_regras: str) -> Campanha:
    """Idempotente: só cria a campanha na primeira chamada; chamadas seguintes devolvem a mesma
    linha sem duplicar (hoje há sempre uma única campanha — Gallancourt)."""
    campanha = sessao.query(Campanha).first()
    if campanha is not None:
        return campanha
    campanha = Campanha(nome=nome, sistema_regras=sistema_regras)
    sessao.add(campanha)
    sessao.commit()
    sessao.refresh(campanha)
    return campanha


def listar_fontes(sessao: Session) -> list[Fonte]:
    return sessao.query(Fonte).order_by(Fonte.nome).all()


def adicionar_fonte(sessao: Session, nome: str, abreviacao: str, edicao: str) -> Fonte:
    fonte = Fonte(nome=nome, abreviacao=abreviacao, edicao=edicao)
    sessao.add(fonte)
    sessao.commit()
    sessao.refresh(fonte)
    return fonte


def apagar_fonte(sessao: Session, id_fonte: int) -> None:
    fonte = sessao.get(Fonte, id_fonte)
    if fonte is not None:
        sessao.delete(fonte)
        sessao.commit()


FONTES_SEED = [
    ("Player's Handbook", "PHB", "2014"),
    ("Dungeon Master's Guide", "DMG", "2014"),
    ("Monster Manual", "MM", "2014"),
    ("Xanathar's Guide to Everything", "XGE", "2014"),
    ("Systems Reference Document", "SRD", "2014"),
]


def semear(sessao: Session) -> None:
    """Popula o banco recém-criado com os dados iniciais, de forma reproduzível e idempotente —
    chamar de novo não duplica nada. Os valores vêm do que já está em uso hoje como texto livre
    nos catálogos (`fonte: PHB/DMG/XGE` em docs/itens/*.md) mais SRD/MM, base do catálogo de
    Monstros."""
    obter_ou_criar_campanha(sessao, "Crônicas de Gallancourt", "2014")
    existentes = {f.abreviacao for f in listar_fontes(sessao)}
    for nome, abreviacao, edicao in FONTES_SEED:
        if abreviacao not in existentes:
            adicionar_fonte(sessao, nome, abreviacao, edicao)
