"""Master's Shield — fundação (ver admin/banco.py: SessaoAoVivo/Lugar/Interacao/
InteracaoParticipante/Rolagem). Isolado do Flask de propósito, como combate_api.py/
personagens_api.py: toda função recebe uma `Session` já aberta.

Nomes "SessaoAoVivo"/`sessao_viva_api` são temporários (ver .claude/contexto/combate.md) — o
autor pediu pra adiar o nome final. O painel vive na mesma aba de sessão onde hoje só aparecia o
Combat Tracker (docs/mestre/sessoes/sessao-N-*.md, marcador `<!-- combate:painel -->`), mas fica
sempre visível (calendário/localidade/log de interações), não só quando há um Combate ativo — o
Combat Tracker (combate_api.py/combate.js) continua existindo exatamente como está, aninhado
dentro deste painel como um sub-modo (iniciativa/turnos).
"""
from __future__ import annotations

import datetime
import random
import re
import unicodedata

from sqlalchemy.orm import Session, joinedload, selectinload

import banco
import personagens_api as pa

# --------------------------------------------------------------------------
# Lugar
# --------------------------------------------------------------------------


def _slug(nome: str) -> str:
    base = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base or "lugar"


def _slug_unico(sessao: Session, nome: str) -> str:
    base = _slug(nome)
    candidato = base
    i = 2
    while sessao.query(banco.Lugar).filter(banco.Lugar.slug == candidato).first() is not None:
        candidato = f"{base}-{i}"
        i += 1
    return candidato


def listar_lugares(sessao: Session) -> list[banco.Lugar]:
    return sessao.query(banco.Lugar).order_by(banco.Lugar.nome).all()


def criar_lugar_provisorio(sessao: Session, nome: str, lugar_pai_id: int | None = None) -> banco.Lugar:
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O lugar precisa de um nome.")
    if lugar_pai_id is not None and sessao.get(banco.Lugar, lugar_pai_id) is None:
        raise ValueError(f"Lugar pai não encontrado: {lugar_pai_id}")
    lugar = banco.Lugar(
        nome=nome, slug=_slug_unico(sessao, nome), lugar_pai_id=lugar_pai_id, canonico=False,
        criado_em=datetime.datetime.now(datetime.UTC),
    )
    sessao.add(lugar)
    sessao.commit()
    sessao.refresh(lugar)
    return lugar


def serializar_lugar(lugar: banco.Lugar) -> dict:
    return {
        "id": lugar.id,
        "nome": lugar.nome,
        "slug": lugar.slug,
        "pagina_rel_docs": lugar.pagina_rel_docs,
        "lugar_pai_id": lugar.lugar_pai_id,
        "canonico": lugar.canonico,
    }


# --------------------------------------------------------------------------
# SessaoAoVivo — calendário e localidade atual
# --------------------------------------------------------------------------


def obter_ou_criar_sessao_viva(sessao: Session, pagina_rel_docs: str) -> banco.SessaoAoVivo:
    existente = (
        sessao.query(banco.SessaoAoVivo)
        .filter(banco.SessaoAoVivo.pagina_rel_docs == pagina_rel_docs)
        .first()
    )
    if existente is not None:
        return existente
    viva = banco.SessaoAoVivo(
        pagina_rel_docs=pagina_rel_docs, criado_em=datetime.datetime.now(datetime.UTC),
    )
    sessao.add(viva)
    sessao.commit()
    sessao.refresh(viva)
    return viva


def atualizar_momento(sessao: Session, viva: banco.SessaoAoVivo, campos: dict) -> banco.SessaoAoVivo:
    """Edição manual direta dos campos de data/hora — corrige qualquer estouro de
    `avancar_tempo` (ex.: virar de mês, já que a duração dos meses da campanha é livre)."""
    for campo in ("ano", "dia", "hora", "minuto"):
        if campo in campos:
            setattr(viva, campo, pa._para_numero(campos[campo], None))
    if "mes" in campos:
        viva.mes = (campos["mes"] or "").strip() or None
    sessao.commit()
    return viva


def avancar_tempo(sessao: Session, viva: banco.SessaoAoVivo, minutos: int) -> banco.SessaoAoVivo:
    """Soma minutos ao relógio atual — aritmética simples (60 min/hora, 24 horas/dia), sem
    conhecer a duração dos meses da campanha (docs/mundo/calendario.md deixa isso em aberto de
    propósito). Virar de mês/ano é sempre uma correção manual via `atualizar_momento`."""
    minutos = pa._para_numero(minutos, 0)
    total = (viva.hora or 0) * 60 + (viva.minuto or 0) + minutos
    dias_passados, resto = divmod(total, 24 * 60)
    viva.hora, viva.minuto = divmod(resto, 60)
    if dias_passados:
        viva.dia = (viva.dia or 1) + dias_passados
    sessao.commit()
    return viva


def descansar_curto(sessao: Session, viva: banco.SessaoAoVivo) -> banco.SessaoAoVivo:
    return avancar_tempo(sessao, viva, 60)


def descansar_longo(sessao: Session, viva: banco.SessaoAoVivo) -> banco.SessaoAoVivo:
    return avancar_tempo(sessao, viva, 8 * 60)


def definir_lugar_atual(sessao: Session, viva: banco.SessaoAoVivo, lugar_id: int | None) -> banco.SessaoAoVivo:
    if lugar_id is not None and sessao.get(banco.Lugar, lugar_id) is None:
        raise ValueError(f"Lugar não encontrado: {lugar_id}")
    viva.lugar_atual_id = lugar_id
    sessao.commit()
    return viva


def serializar_sessao_viva(viva: banco.SessaoAoVivo) -> dict:
    return {
        "id": viva.id,
        "pagina_rel_docs": viva.pagina_rel_docs,
        "ano": viva.ano, "mes": viva.mes, "dia": viva.dia, "hora": viva.hora, "minuto": viva.minuto,
        "lugar_atual_id": viva.lugar_atual_id,
        "lugar_atual": serializar_lugar(viva.lugar_atual) if viva.lugar_atual else None,
    }


# --------------------------------------------------------------------------
# Interacao / Rolagem — log estruturado
# --------------------------------------------------------------------------


def _opcoes_interacao():
    return (
        joinedload(banco.Interacao.lugar),
        selectinload(banco.Interacao.participantes_vinculo).joinedload(banco.InteracaoParticipante.ficha)
        .joinedload(banco.Ficha.personagem),
        selectinload(banco.Interacao.rolagens_vinculo),
    )


def registrar_interacao(sessao: Session, pagina_rel_docs: str, campos: dict) -> banco.Interacao:
    """`campos`: tipo (ver banco.TIPOS_INTERACAO), combate_id?, lugar_id? (default: localidade
    atual da SessaoAoVivo), pericia_ou_atributo?, cd?, sucesso?, descricao?,
    participantes?: [{"ficha_id", "papel"}], rolagens?: [{"dado", "vantagem"?, "resultado_bruto"?,
    "resultado_total"?, "online"?}]."""
    tipo = campos.get("tipo")
    if tipo not in banco.TIPOS_INTERACAO:
        raise ValueError(f"Tipo de interação desconhecido: {tipo}")
    viva = obter_ou_criar_sessao_viva(sessao, pagina_rel_docs)
    lugar_id = campos.get("lugar_id", viva.lugar_atual_id)
    if lugar_id is not None and sessao.get(banco.Lugar, lugar_id) is None:
        raise ValueError(f"Lugar não encontrado: {lugar_id}")

    interacao = banco.Interacao(
        pagina_rel_docs=pagina_rel_docs,
        combate_id=campos.get("combate_id"),
        lugar_id=lugar_id,
        ano=viva.ano, mes=viva.mes, dia=viva.dia, hora=viva.hora, minuto=viva.minuto,
        tipo=tipo,
        pericia_ou_atributo=(campos.get("pericia_ou_atributo") or "").strip() or None,
        cd=pa._para_numero(campos.get("cd"), None),
        sucesso=campos.get("sucesso"),
        descricao=(campos.get("descricao") or "").strip() or None,
        criado_em=datetime.datetime.now(datetime.UTC),
    )
    sessao.add(interacao)
    sessao.flush()

    for participante in campos.get("participantes") or []:
        ficha_id = participante.get("ficha_id")
        if sessao.get(banco.Ficha, ficha_id) is None:
            raise ValueError(f"Ficha não encontrada: {ficha_id}")
        papel = participante.get("papel") or "ator"
        if papel not in banco.PAPEIS_INTERACAO_PARTICIPANTE:
            raise ValueError(f"Papel desconhecido: {papel}")
        sessao.add(banco.InteracaoParticipante(interacao_id=interacao.id, ficha_id=ficha_id, papel=papel))

    for rolagem in campos.get("rolagens") or []:
        sessao.add(banco.Rolagem(
            interacao_id=interacao.id,
            dado=rolagem.get("dado") or "",
            vantagem=rolagem.get("vantagem"),
            resultado_bruto=pa._para_numero(rolagem.get("resultado_bruto"), None),
            resultado_total=pa._para_numero(rolagem.get("resultado_total"), None),
            online=bool(rolagem.get("online")),
        ))

    sessao.commit()
    sessao.refresh(interacao)
    return interacao


def listar_interacoes(sessao: Session, pagina_rel_docs: str, limite: int = 200) -> list[banco.Interacao]:
    return (
        sessao.query(banco.Interacao)
        .options(*_opcoes_interacao())
        .filter(banco.Interacao.pagina_rel_docs == pagina_rel_docs)
        .order_by(banco.Interacao.id.desc())
        .limit(limite)
        .all()
    )


def serializar_interacao(interacao: banco.Interacao) -> dict:
    return {
        "id": interacao.id,
        "combate_id": interacao.combate_id,
        "lugar_id": interacao.lugar_id,
        "lugar_nome": interacao.lugar.nome if interacao.lugar else None,
        "ano": interacao.ano, "mes": interacao.mes, "dia": interacao.dia,
        "hora": interacao.hora, "minuto": interacao.minuto,
        "tipo": interacao.tipo,
        "pericia_ou_atributo": interacao.pericia_ou_atributo,
        "cd": interacao.cd,
        "sucesso": interacao.sucesso,
        "descricao": interacao.descricao,
        "criado_em": interacao.criado_em.isoformat(),
        "participantes": [
            {
                "ficha_id": p.ficha_id, "papel": p.papel,
                "nome": (
                    p.ficha.personagem.nome if p.ficha.is_base
                    else f"{p.ficha.personagem.nome} ({p.ficha.rotulo})"
                ),
            }
            for p in interacao.participantes_vinculo
        ],
        "rolagens": [
            {
                "id": r.id, "dado": r.dado, "vantagem": r.vantagem,
                "resultado_bruto": r.resultado_bruto, "resultado_total": r.resultado_total,
                "online": r.online,
            }
            for r in interacao.rolagens_vinculo
        ],
    }


# --------------------------------------------------------------------------
# Rolagem online
# --------------------------------------------------------------------------

_RE_DADO = re.compile(r"^\s*(\d*)d(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


def _rolar_formula(dado: str) -> tuple[int, int]:
    """Devolve (bruto, total) de uma fórmula "NdM+B" — bruto é a soma só dos dados, total inclui
    o bônus fixo."""
    m = _RE_DADO.match(dado or "")
    if not m:
        raise ValueError(f"Fórmula de dado inválida: {dado!r} (use algo como '1d20+5').")
    quantidade = int(m.group(1)) if m.group(1) else 1
    lados = int(m.group(2))
    bonus = int(m.group(3).replace(" ", "")) if m.group(3) else 0
    bruto = sum(random.randint(1, lados) for _ in range(max(1, quantidade)))
    return bruto, bruto + bonus


def rolar_online(dado: str, vantagem: str | None = None) -> dict:
    """Vantagem/desvantagem: rola a fórmula inteira duas vezes e fica com o maior/menor total —
    simplificação válida pra qualquer fórmula, não só 1d20 puro."""
    bruto, total = _rolar_formula(dado)
    if vantagem in ("vantagem", "desvantagem"):
        bruto2, total2 = _rolar_formula(dado)
        escolhido = max if vantagem == "vantagem" else min
        bruto, total = escolhido((bruto, total), (bruto2, total2), key=lambda par: par[1])
    return {"dado": dado, "vantagem": vantagem, "resultado_bruto": bruto, "resultado_total": total}
