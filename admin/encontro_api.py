"""Encontros planejados (rascunho de combate antes da sessão) — ver admin/banco.py:
EncontroPlanejado/EncontroParticipantePlanejado e .claude/contexto/combate.md.

Isolado do Flask, como personagens_api.py/combate_api.py: toda função recebe uma `Session` já
aberta. Uma página de sessão pode ter vários rascunhos (ex. "Emboscada na ponte", "Boss final");
cada um lista participantes (ficha_id + nome de exibição) que, ao iniciar o Combat Tracker a partir
dele, viram CombateParticipante de verdade (ver carregar_no_combate, que só chama
combate_api.adicionar_participante pra cada linha — nenhuma lógica nova de combate aqui)."""
from __future__ import annotations

import datetime

from sqlalchemy.orm import Session, selectinload

import banco
import combate_api as ca


def serializar_participante_planejado(participante: banco.EncontroParticipantePlanejado) -> dict:
    ficha = participante.ficha
    personagem = ficha.personagem
    return {
        "id": participante.id,
        "ficha_id": ficha.id,
        "tipo": personagem.tipo,
        "slug": personagem.slug,
        "nome": participante.nome_exibicao or personagem.nome,
        "foto": personagem.foto,
        "ordem": participante.ordem,
    }


def serializar_encontro(encontro: banco.EncontroPlanejado) -> dict:
    return {
        "id": encontro.id,
        "pagina_rel_docs": encontro.pagina_rel_docs,
        "nome": encontro.nome,
        "criado_em": encontro.criado_em.isoformat(),
        "participantes": [
            serializar_participante_planejado(p) for p in encontro.participantes_vinculo
        ],
    }


def _opcoes_encontro():
    return (
        selectinload(banco.EncontroPlanejado.participantes_vinculo)
        .selectinload(banco.EncontroParticipantePlanejado.ficha)
        .selectinload(banco.Ficha.personagem),
    )


def listar_encontros(sessao: Session, pagina_rel_docs: str) -> list[banco.EncontroPlanejado]:
    return (
        sessao.query(banco.EncontroPlanejado)
        .options(*_opcoes_encontro())
        .filter(banco.EncontroPlanejado.pagina_rel_docs == pagina_rel_docs)
        .order_by(banco.EncontroPlanejado.id)
        .all()
    )


def obter_encontro(sessao: Session, encontro_id: int) -> banco.EncontroPlanejado | None:
    return (
        sessao.query(banco.EncontroPlanejado)
        .options(*_opcoes_encontro())
        .filter(banco.EncontroPlanejado.id == encontro_id)
        .first()
    )


def criar_encontro(sessao: Session, pagina_rel_docs: str, nome: str) -> banco.EncontroPlanejado:
    encontro = banco.EncontroPlanejado(
        pagina_rel_docs=pagina_rel_docs, nome=(nome or "Encontro").strip() or "Encontro",
        criado_em=datetime.datetime.now(datetime.UTC),
    )
    sessao.add(encontro)
    sessao.commit()
    sessao.refresh(encontro)
    return obter_encontro(sessao, encontro.id)


def excluir_encontro(sessao: Session, encontro_id: int) -> None:
    encontro = sessao.get(banco.EncontroPlanejado, encontro_id)
    if encontro is not None:
        sessao.delete(encontro)
        sessao.commit()


def adicionar_participante_planejado(
    sessao: Session, encontro_id: int, ficha_id: int, nome_exibicao: str | None = None,
) -> banco.EncontroPlanejado:
    encontro = sessao.get(banco.EncontroPlanejado, encontro_id)
    if encontro is None:
        raise ValueError(f"Encontro não encontrado: {encontro_id}")
    ficha = sessao.get(banco.Ficha, ficha_id)
    if ficha is None:
        raise ValueError(f"Ficha não encontrada: {ficha_id}")
    maior_ordem = max((p.ordem for p in encontro.participantes_vinculo), default=-1)
    participante = banco.EncontroParticipantePlanejado(
        encontro_id=encontro_id, ficha_id=ficha_id,
        nome_exibicao=(nome_exibicao or "").strip() or None,
        ordem=maior_ordem + 1,
    )
    sessao.add(participante)
    sessao.commit()
    return obter_encontro(sessao, encontro_id)


def remover_participante_planejado(sessao: Session, participante_id: int) -> banco.EncontroPlanejado | None:
    participante = sessao.get(banco.EncontroParticipantePlanejado, participante_id)
    if participante is None:
        return None
    encontro_id = participante.encontro_id
    sessao.delete(participante)
    sessao.commit()
    return obter_encontro(sessao, encontro_id)


def carregar_no_combate(sessao: Session, combate: banco.Combate, encontro_id: int) -> None:
    """Adiciona ao Combate (já criado) cada participante do encontro planejado, na mesma ordem —
    reaproveita combate_api.adicionar_participante, sem duplicar a lógica de criação de
    CombateParticipante (iniciativa de desempate automática etc. já ficam por conta dela)."""
    encontro = obter_encontro(sessao, encontro_id)
    if encontro is None:
        return
    for planejado in encontro.participantes_vinculo:
        ca.adicionar_participante(
            sessao, combate, planejado.ficha_id, nome_exibicao=planejado.nome_exibicao,
        )
