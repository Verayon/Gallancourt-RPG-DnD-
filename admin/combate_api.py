"""Lógica do Combat Tracker (ver admin/banco.py: Combate/CombateParticipante/
CombateParticipanteCondicao/CombateLogEntrada) — isolado do Flask de propósito, como
personagens_api.py/wiki_data.py: toda função recebe uma `Session` já aberta.

Substitui o antigo admin/sessao_viva.py (estado em JSON fora do banco, só utilizável com o Painel
local rodando). O Combat Tracker vive numa aba das páginas de sessão
(docs/mestre/sessoes/sessao-N-*.md), lida/escrita por docs/javascripts/combate.js.

Regra central (confirmada com o autor, ver o plano "Combat Tracker integrado..."): ao adicionar um
participante de tipo "monstro" (`Personagem.tipo`), PV/PV temporário/condições ficam numa CÓPIA
isolada (`CombateParticipante.copia_pv_atual`/`copia_pv_temporario` +
`CombateParticipanteCondicao`) — nada toca a Ficha real do catálogo, porque a mesma Ficha de
"Goblin" pode estar em várias cópias simultâneas no mesmo combate. Para "npc"/"jogador" (únicos,
nunca duplicados), o tracker lê e escreve direto na Ficha real (`Ficha.pv_atual`/`pv_temporario`,
`FichaCondicao`) — isso persiste entre sessões, só "resetando" com um Descanso Longo (ver
personagens_api.py::descanso_longo).
"""
from __future__ import annotations

import datetime
import json
import random

from sqlalchemy.orm import Session, joinedload, selectinload

import banco
import personagens_api as pa

# --------------------------------------------------------------------------
# Helpers de tipo e serialização
# --------------------------------------------------------------------------


def _e_copia(participante: banco.CombateParticipante) -> bool:
    """True quando este participante é uma cópia isolada (monstro) — False quando lê/escreve
    direto na Ficha real (npc/jogador)."""
    return participante.ficha.personagem.tipo == "monstro"


def _carregar_participante(sessao: Session, participante_id: int) -> banco.CombateParticipante | None:
    return (
        sessao.query(banco.CombateParticipante)
        .options(
            joinedload(banco.CombateParticipante.ficha).joinedload(banco.Ficha.personagem),
            selectinload(banco.CombateParticipante.condicoes_vinculo),
        )
        .filter(banco.CombateParticipante.id == participante_id)
        .first()
    )


def pv_atual(participante: banco.CombateParticipante) -> int:
    if _e_copia(participante):
        return participante.copia_pv_atual if participante.copia_pv_atual is not None else participante.ficha.pv_maximo
    return participante.ficha.pv_atual


def pv_temporario(participante: banco.CombateParticipante) -> int:
    if _e_copia(participante):
        return participante.copia_pv_temporario or 0
    return participante.ficha.pv_temporario


def condicoes_ativas(participante: banco.CombateParticipante) -> list[str]:
    return [c.nome for c in participante.condicoes_vinculo]


def serializar_participante(participante: banco.CombateParticipante) -> dict:
    ficha = participante.ficha
    personagem = ficha.personagem
    pv_max = ficha.pv_maximo
    pv_at = pv_atual(participante)
    return {
        "id": participante.id,
        "ficha_id": ficha.id,
        "tipo": personagem.tipo,
        "slug": personagem.slug,
        "e_copia": _e_copia(participante),
        "nome": (
            participante.nome_exibicao
            or (f"{personagem.nome} ({ficha.rotulo})" if not ficha.is_base else personagem.nome)
        ),
        "foto": personagem.foto,
        "iniciativa_base": participante.iniciativa_base,
        "iniciativa_desempate": participante.iniciativa_desempate,
        "iniciativa_ordenacao": participante.iniciativa_base + participante.iniciativa_desempate * 0.01,
        "ca_total": ficha.ca_total,
        "pv_maximo": pv_max,
        "pv_atual": pv_at,
        "pv_temporario": pv_temporario(participante),
        "caido": pv_at <= 0,
        "acao_usada": participante.acao_usada,
        "acao_bonus_usada": participante.acao_bonus_usada,
        "reacao_usada": participante.reacao_usada,
        "concentrando_em": participante.concentrando_em,
        "death_save_sucessos": participante.death_save_sucessos,
        "death_save_falhas": participante.death_save_falhas,
        "morto": participante.death_save_falhas >= 3,
        "condicoes": condicoes_ativas(participante),
        "habilidades": [
            {"vinculo_id": v.id, "nome": v.habilidade.nome, "tipo": v.habilidade.tipo,
             "bonus_acerto": v.habilidade.bonus_acerto, "dano_formula": v.habilidade.dano_formula,
             "dano_tipo": v.habilidade.dano_tipo, "descricao": v.habilidade.descricao,
             "favorito": v.favorito, "usos_maximo": v.usos_maximo, "usos_restantes": v.usos_restantes}
            for v in sorted(ficha.habilidades_vinculo, key=lambda v: not v.favorito)
        ],
        "magias": [
            {"nome": v.magia.nome, "nivel": v.magia.nivel, "resistencia": v.magia.resistencia,
             "dano_formula": v.magia.dano_formula, "dano_tipo": v.magia.dano_tipo, "favorito": v.favorito}
            for v in sorted(ficha.magias_vinculo, key=lambda v: not v.favorito)
        ],
        "espacos_magia": [
            {"nivel": e.nivel, "maximo": e.maximo, "usado": e.usado, "rotulo": e.rotulo}
            for e in ficha.espacos_magia_vinculo
        ] if not _e_copia(participante) else [],
    }


def serializar_combate(combate: banco.Combate) -> dict:
    participantes = sorted(
        combate.participantes,
        key=lambda p: -(p.iniciativa_base + p.iniciativa_desempate * 0.01),
    )
    return {
        "id": combate.id,
        "pagina_rel_docs": combate.pagina_rel_docs,
        "rodada": combate.rodada,
        "turno_participante_id": combate.turno_participante_id,
        "ativo": combate.ativo,
        "participantes": [serializar_participante(p) for p in participantes],
        "log": [
            {"id": e.id, "rodada": e.rodada, "texto": e.texto, "tipo": e.tipo,
             "criado_em": e.criado_em.isoformat()}
            for e in sorted(combate.log_vinculo, key=lambda e: e.id)
        ],
    }


# --------------------------------------------------------------------------
# Ciclo de vida do Combate
# --------------------------------------------------------------------------

def _opcoes_combate():
    return (
        selectinload(banco.Combate.participantes)
        .joinedload(banco.CombateParticipante.ficha)
        .joinedload(banco.Ficha.personagem),
        selectinload(banco.Combate.participantes).selectinload(banco.CombateParticipante.condicoes_vinculo),
        selectinload(banco.Combate.log_vinculo),
    )


def obter_combate_ativo(sessao: Session, pagina_rel_docs: str) -> banco.Combate | None:
    return (
        sessao.query(banco.Combate)
        .options(*_opcoes_combate())
        .filter(banco.Combate.pagina_rel_docs == pagina_rel_docs, banco.Combate.ativo.is_(True))
        .order_by(banco.Combate.id.desc())
        .first()
    )


def obter_combate(sessao: Session, combate_id: int) -> banco.Combate | None:
    return (
        sessao.query(banco.Combate)
        .options(*_opcoes_combate())
        .filter(banco.Combate.id == combate_id)
        .first()
    )


def iniciar_combate(sessao: Session, pagina_rel_docs: str) -> banco.Combate:
    """Cria um novo Combate ativo nesta página — se já existir um ativo, devolve ele mesmo (não
    duplica)."""
    existente = obter_combate_ativo(sessao, pagina_rel_docs)
    if existente is not None:
        return existente
    combate = banco.Combate(
        pagina_rel_docs=pagina_rel_docs, rodada=1, ativo=True,
        criado_em=datetime.datetime.now(datetime.UTC),
    )
    sessao.add(combate)
    sessao.commit()
    sessao.refresh(combate)
    return obter_combate(sessao, combate.id)


def encerrar_combate(sessao: Session, combate: banco.Combate) -> banco.Combate:
    combate.ativo = False
    combate.finalizado_em = datetime.datetime.now(datetime.UTC)
    sessao.commit()
    return combate


# --------------------------------------------------------------------------
# Participantes
# --------------------------------------------------------------------------

def adicionar_participante(
    sessao: Session, combate: banco.Combate, ficha_id: int,
    nome_exibicao: str | None = None, iniciativa_base: int = 0,
) -> banco.CombateParticipante:
    ficha = sessao.get(banco.Ficha, ficha_id)
    if ficha is None:
        raise ValueError(f"Ficha não encontrada: {ficha_id}")
    e_monstro = ficha.personagem.tipo == "monstro"
    participante = banco.CombateParticipante(
        combate_id=combate.id, ficha_id=ficha_id,
        nome_exibicao=(nome_exibicao or "").strip() or None,
        iniciativa_base=pa._para_numero(iniciativa_base, 0),
        # Desempate automático pelo mod. de Destreza (ver especificação do Combat Tracker) — ainda
        # editável depois via atualizar_iniciativa, pra casos especiais.
        iniciativa_desempate=pa.modificador(ficha.destreza),
        copia_pv_atual=ficha.pv_maximo if e_monstro else None,
        copia_pv_temporario=0 if e_monstro else None,
    )
    sessao.add(participante)
    sessao.commit()
    sessao.refresh(participante)
    return participante


def remover_participante(sessao: Session, participante_id: int) -> None:
    participante = sessao.get(banco.CombateParticipante, participante_id)
    if participante is None:
        return
    combate = participante.combate
    sessao.delete(participante)
    sessao.commit()
    if combate.turno_participante_id == participante_id:
        combate.turno_participante_id = None
        sessao.commit()


def atualizar_iniciativa(sessao: Session, participante_id: int, base=None, desempate=None) -> None:
    participante = sessao.get(banco.CombateParticipante, participante_id)
    if participante is None:
        raise ValueError("Participante não encontrado.")
    if base is not None:
        participante.iniciativa_base = pa._para_numero(base, participante.iniciativa_base)
    if desempate is not None:
        participante.iniciativa_desempate = pa._para_numero(desempate, participante.iniciativa_desempate)
    sessao.commit()


# --------------------------------------------------------------------------
# PV, condições, concentração — cópia (monstro) vs. Ficha real (npc/jogador)
# --------------------------------------------------------------------------

def ajustar_pv(sessao: Session, participante_id: int, delta: int, cura: bool = False) -> dict:
    """`delta` sempre positivo; `cura=True` soma respeitando o PV máximo, `cura=False` (dano)
    deduz, consumindo primeiro o PV temporário."""
    participante = _carregar_participante(sessao, participante_id)
    if participante is None:
        raise ValueError("Participante não encontrado.")
    ficha = participante.ficha
    delta = max(0, pa._para_numero(delta, 0))
    copia = _e_copia(participante)

    atual = pv_atual(participante)
    temp = pv_temporario(participante)

    if cura:
        novo_atual = min(ficha.pv_maximo, atual + delta)
        novo_temp = temp
    else:
        absorvido = min(temp, delta)
        novo_temp = temp - absorvido
        restante = delta - absorvido
        novo_atual = max(0, atual - restante)

    if copia:
        participante.copia_pv_atual = novo_atual
        participante.copia_pv_temporario = novo_temp
    else:
        ficha.pv_atual = novo_atual
        ficha.pv_temporario = novo_temp

    # PV chegando a 0 aplica "Caído" automaticamente (módulo 4.1); voltar a ter PV remove.
    if novo_atual <= 0:
        _aplicar_condicao(sessao, participante, "Caído", copia)
    elif atual <= 0 < novo_atual:
        _remover_condicao_por_nome(sessao, participante, "Caído", copia)
        participante.death_save_sucessos = 0
        participante.death_save_falhas = 0

    sessao.commit()
    return {"pv_atual": novo_atual, "pv_temporario": novo_temp}


def definir_pv_temporario(sessao: Session, participante_id: int, valor: int) -> None:
    participante = _carregar_participante(sessao, participante_id)
    if participante is None:
        raise ValueError("Participante não encontrado.")
    valor = max(0, pa._para_numero(valor, 0))
    if _e_copia(participante):
        participante.copia_pv_temporario = valor
    else:
        participante.ficha.pv_temporario = valor
    sessao.commit()


def _aplicar_condicao(sessao: Session, participante: banco.CombateParticipante, nome: str, copia: bool) -> None:
    if nome in condicoes_ativas(participante):
        return
    sessao.add(banco.CombateParticipanteCondicao(participante_id=participante.id, nome=nome))
    if not copia:
        ja_tem = any(c.nome == nome for c in participante.ficha.condicoes_vinculo)
        if not ja_tem:
            sessao.add(banco.FichaCondicao(ficha_id=participante.ficha_id, nome=nome))


def _remover_condicao_por_nome(sessao: Session, participante: banco.CombateParticipante, nome: str, copia: bool) -> None:
    for c in list(participante.condicoes_vinculo):
        if c.nome == nome:
            sessao.delete(c)
    if not copia:
        for c in list(participante.ficha.condicoes_vinculo):
            if c.nome == nome:
                sessao.delete(c)


def alternar_condicao(sessao: Session, participante_id: int, nome: str) -> list[str]:
    if nome not in banco.CONDICOES_D20 and nome not in ("Caído", "Morto"):
        raise ValueError(f"Condição desconhecida: {nome}")
    participante = _carregar_participante(sessao, participante_id)
    if participante is None:
        raise ValueError("Participante não encontrado.")
    copia = _e_copia(participante)
    if nome in condicoes_ativas(participante):
        _remover_condicao_por_nome(sessao, participante, nome, copia)
    else:
        _aplicar_condicao(sessao, participante, nome, copia)
    sessao.commit()
    sessao.refresh(participante)
    return condicoes_ativas(participante)


def definir_concentracao(sessao: Session, participante_id: int, nome: str | None) -> None:
    participante = sessao.get(banco.CombateParticipante, participante_id)
    if participante is None:
        raise ValueError("Participante não encontrado.")
    participante.concentrando_em = (nome or "").strip() or None
    sessao.commit()


# --------------------------------------------------------------------------
# Turnos, rodadas, economia de ação (módulo 2.3 e 5.1)
# --------------------------------------------------------------------------

def _ordem(combate: banco.Combate) -> list[banco.CombateParticipante]:
    return sorted(
        combate.participantes,
        key=lambda p: (-(p.iniciativa_base + p.iniciativa_desempate * 0.01), p.id),
    )


def _resetar_economia_acao(participante: banco.CombateParticipante) -> None:
    participante.acao_usada = False
    participante.acao_bonus_usada = False
    participante.reacao_usada = False


def proximo_turno(sessao: Session, combate: banco.Combate) -> banco.Combate:
    ordem = _ordem(combate)
    if not ordem:
        return combate
    ids = [p.id for p in ordem]
    if combate.turno_participante_id not in ids:
        novo_atual = ordem[0]
    else:
        idx = ids.index(combate.turno_participante_id)
        if idx + 1 < len(ids):
            novo_atual = ordem[idx + 1]
        else:
            novo_atual = ordem[0]
            combate.rodada += 1
            _decrementar_duracoes(sessao, combate)
    combate.turno_participante_id = novo_atual.id
    _resetar_economia_acao(novo_atual)
    sessao.commit()
    return combate


def _decrementar_duracoes(sessao: Session, combate: banco.Combate) -> None:
    """Ao voltar ao topo da iniciativa (nova rodada) — decrementa a duração de FichaEfeito com
    duração numérica (ex.: "3 rodadas"), removendo quando chega a zero. Efeitos com duração em
    texto livre não numérico (ex.: "até o fim do combate") não são tocados aqui de propósito."""
    for participante in combate.participantes:
        for efeito in list(participante.ficha.efeitos_vinculo):
            restante = _duracao_em_rodadas(efeito.duracao)
            if restante is None:
                continue
            restante -= 1
            if restante <= 0:
                sessao.delete(efeito)
            else:
                efeito.duracao = f"{restante} rodada" if restante == 1 else f"{restante} rodadas"


def _duracao_em_rodadas(texto: str | None) -> int | None:
    if not texto:
        return None
    primeira_palavra = texto.strip().split(" ", 1)[0]
    try:
        return int(primeira_palavra)
    except ValueError:
        return None


def alternar_economia_acao(sessao: Session, participante_id: int, campo: str) -> bool:
    if campo not in ("acao_usada", "acao_bonus_usada", "reacao_usada"):
        raise ValueError(f"Campo de economia de ação desconhecido: {campo}")
    participante = sessao.get(banco.CombateParticipante, participante_id)
    if participante is None:
        raise ValueError("Participante não encontrado.")
    setattr(participante, campo, not getattr(participante, campo))
    sessao.commit()
    return getattr(participante, campo)


def oferecer_reacao(sessao: Session, participante_id: int, rotulo: str) -> dict:
    """Botão manual "Oferecer reação" (módulo 3.4-3.6) — sem detecção automática nesta versão; o
    Mestre confirma que o participante tem a reação disponível e aciona. Marca `reacao_usada`."""
    participante = sessao.get(banco.CombateParticipante, participante_id)
    if participante is None:
        raise ValueError("Participante não encontrado.")
    if participante.reacao_usada:
        raise ValueError("Este participante já usou a reação nesta rodada.")
    participante.reacao_usada = True
    sessao.commit()
    return {"participante_id": participante_id, "rotulo": rotulo}


# --------------------------------------------------------------------------
# Testes contra a morte (módulo 4)
# --------------------------------------------------------------------------

def rolar_teste_morte(sessao: Session, participante_id: int, d20_bruto: int) -> dict:
    participante = _carregar_participante(sessao, participante_id)
    if participante is None:
        raise ValueError("Participante não encontrado.")
    d20_bruto = pa._para_numero(d20_bruto, 10)
    resultado = {"d20": d20_bruto}
    if d20_bruto == 20:
        participante.death_save_sucessos = 0
        participante.death_save_falhas = 0
        if _e_copia(participante):
            participante.copia_pv_atual = 1
        else:
            participante.ficha.pv_atual = 1
        _remover_condicao_por_nome(sessao, participante, "Caído", _e_copia(participante))
        resultado["efeito"] = "levanta_com_1_pv"
    elif d20_bruto == 1:
        participante.death_save_falhas = min(3, participante.death_save_falhas + 2)
        resultado["efeito"] = "duas_falhas"
    elif d20_bruto >= 10:
        participante.death_save_sucessos = min(3, participante.death_save_sucessos + 1)
        resultado["efeito"] = "sucesso"
    else:
        participante.death_save_falhas = min(3, participante.death_save_falhas + 1)
        resultado["efeito"] = "falha"
    resultado["morto"] = participante.death_save_falhas >= 3
    sessao.commit()
    return resultado


# --------------------------------------------------------------------------
# Motor híbrido de resolução (módulo 3)
# --------------------------------------------------------------------------

def resolver_ataque(
    sessao: Session, combate: banco.Combate, alvos_ids: list[int], d20_bruto: int, bonus: int,
    dano: int, cura: bool,
) -> dict:
    d20_bruto = pa._para_numero(d20_bruto, 10)
    bonus = pa._para_numero(bonus, 0)
    total = d20_bruto + bonus
    resultados = []
    for alvo_id in alvos_ids:
        alvo = _carregar_participante(sessao, alvo_id)
        if alvo is None:
            continue
        if cura:
            acertou = True
        else:
            acertou = total >= alvo.ficha.ca_total or d20_bruto == 20
            if d20_bruto == 1:
                acertou = False
        novo_pv = None
        if acertou and dano:
            novo_pv = ajustar_pv(sessao, alvo_id, dano, cura=cura)
        resultados.append({
            "alvo_id": alvo_id, "acertou": acertou, "total": total,
            "ca": alvo.ficha.ca_total, "pv": novo_pv,
        })
    return {"d20": d20_bruto, "bonus": bonus, "total": total, "alvos": resultados}


def _tem_evasao(participante: banco.CombateParticipante) -> bool:
    """Evasão (ver especificação, módulo de resistência em área) — checada pelo nome na lista de
    Habilidades já vinculadas à Ficha, sem campo de schema novo só pra isso."""
    return any(v.habilidade.nome.strip().lower() == "evasão" for v in participante.ficha.habilidades_vinculo)


def resolver_resistencia(
    sessao: Session, cd: int, meio_no_sucesso: bool, condicao_no_erro: str | None,
    alvos: list[dict],
) -> list[dict]:
    """`alvos`: [{"participante_id", "d20_bruto", "dano"}] — calcula sucesso/falha por alvo,
    aplica dano total, metade (se `meio_no_sucesso`) ou zero (sucesso + Habilidade "Evasão") e,
    se marcado, uma condição secundária em quem falhar."""
    cd = pa._para_numero(cd, 10)
    resultados = []
    for alvo in alvos:
        participante = _carregar_participante(sessao, alvo["participante_id"])
        d20_bruto = pa._para_numero(alvo.get("d20_bruto"), 10)
        dano = pa._para_numero(alvo.get("dano"), 0)
        sucesso = d20_bruto >= cd
        if sucesso and participante is not None and _tem_evasao(participante):
            dano_aplicado = 0
        else:
            dano_aplicado = (dano // 2 if meio_no_sucesso else 0) if sucesso else dano
        novo_pv = ajustar_pv(sessao, alvo["participante_id"], dano_aplicado, cura=False) if dano_aplicado else None
        if not sucesso and condicao_no_erro:
            alternar_condicao(sessao, alvo["participante_id"], condicao_no_erro)
        resultados.append({
            "participante_id": alvo["participante_id"], "d20": d20_bruto, "sucesso": sucesso,
            "dano_aplicado": dano_aplicado, "pv": novo_pv,
        })
    return resultados


def checar_concentracao(sessao: Session, participante_id: int, d20_bruto: int, bonus: int, dano_sofrido: int) -> dict:
    cd = max(10, dano_sofrido // 2)
    total = pa._para_numero(d20_bruto, 10) + pa._para_numero(bonus, 0)
    sucesso = total >= cd
    if not sucesso:
        definir_concentracao(sessao, participante_id, None)
    return {"cd": cd, "total": total, "sucesso": sucesso}


# --------------------------------------------------------------------------
# Log de combate (módulo 5.2)
# --------------------------------------------------------------------------

def registrar_log(sessao: Session, combate: banco.Combate, texto: str, tipo: str | None = None) -> banco.CombateLogEntrada:
    entrada = banco.CombateLogEntrada(
        combate_id=combate.id, rodada=combate.rodada, texto=texto.strip(), tipo=tipo,
        criado_em=datetime.datetime.now(datetime.UTC),
    )
    sessao.add(entrada)
    sessao.commit()
    sessao.refresh(entrada)
    return entrada


def exportar_log(combate: banco.Combate, formato: str) -> str:
    entradas = sorted(combate.log_vinculo, key=lambda e: e.id)
    if formato == "json":
        return json.dumps(
            [{"rodada": e.rodada, "texto": e.texto, "tipo": e.tipo, "criado_em": e.criado_em.isoformat()}
             for e in entradas],
            ensure_ascii=False, indent=2,
        )
    linhas = [f"[{e.criado_em.strftime('%H:%M')}] Rodada {e.rodada}: {e.texto}" for e in entradas]
    return "\n".join(linhas)


# --------------------------------------------------------------------------
# Resumo pós-combate: XP e Loot (módulo 6)
# --------------------------------------------------------------------------

def _cr_para_numero(cr: str | None) -> float:
    if not cr:
        return 0.0
    if "/" in cr:
        num, _, den = cr.partition("/")
        return pa._para_numero(num, 0) / max(1, pa._para_numero(den, 1))
    return pa._para_numero(cr, 0)


# Faixas de moeda extra automática por CR médio do encontro — rolagem de verdade (random), não
# mais um mock fixo (ver especificação, módulo 6.5: "rolagem automática... gerando moedas... aleatórios").
# Não gera itens mágicos aleatórios — exigiria uma tabela de raridade que o projeto não tem ainda
# (ver .claude/contexto/combate.md, decisão de escopo documentada).
def _rolar_moeda_por_cr_medio(cr_medio: float) -> dict:
    if cr_medio <= 4:
        return {"moeda_pp": random.randint(5, 15), "moeda_po": random.randint(0, 10)}
    if cr_medio <= 10:
        return {"moeda_pp": random.randint(10, 30), "moeda_po": random.randint(10, 40), "moeda_pl": random.randint(0, 3)}
    return {"moeda_po": random.randint(30, 70), "moeda_pl": random.randint(5, 20)}


def calcular_resumo_xp(combate: banco.Combate) -> dict:
    monstros_mortos = [
        p for p in combate.participantes
        if p.ficha.personagem.tipo == "monstro" and pv_atual(p) <= 0
    ]
    xp_total = sum(pa.CR_PARA_XP.get(p.ficha.cr or "", 0) for p in monstros_mortos)
    jogadores_vivos = [
        p for p in combate.participantes
        if p.ficha.personagem.tipo == "jogador" and pv_atual(p) > 0
    ]
    n_jogadores = max(1, len(jogadores_vivos))
    return {
        "xp_total": xp_total,
        "xp_por_jogador": xp_total // n_jogadores,
        "jogadores": [{"participante_id": p.id, "ficha_id": p.ficha_id, "nome": p.ficha.personagem.nome}
                      for p in jogadores_vivos],
        "monstros_mortos": [{"participante_id": p.id, "nome": p.nome_exibicao or p.ficha.personagem.nome}
                            for p in monstros_mortos],
    }


def distribuir_xp(sessao: Session, combate: banco.Combate, xp_por_jogador: int) -> None:
    xp_por_jogador = max(0, pa._para_numero(xp_por_jogador, 0))
    for p in combate.participantes:
        if p.ficha.personagem.tipo == "jogador" and pv_atual(p) > 0:
            p.ficha.xp = (p.ficha.xp or 0) + xp_por_jogador
    sessao.commit()


def compilar_loot(combate: banco.Combate) -> dict:
    """Lista de itens/moedas do inventário dos participantes MORTOS de tipo monstro — não inclui
    npc/jogador (ver plano: não removemos item do inventário real de um personagem nomeado sem
    uma ação própria). Só leitura — não altera a Ficha real do monstro. Soma automaticamente uma
    moeda extra sorteada pelo CR médio do encontro (ver _rolar_moeda_por_cr_medio)."""
    itens: dict[str, dict] = {}
    moedas = {"moeda_pc": 0, "moeda_pp": 0, "moeda_pe": 0, "moeda_po": 0, "moeda_pl": 0}
    crs_mortos = []
    for p in combate.participantes:
        if p.ficha.personagem.tipo != "monstro" or pv_atual(p) > 0:
            continue
        ficha = p.ficha
        crs_mortos.append(_cr_para_numero(ficha.cr))
        for v in ficha.equipamentos_vinculo:
            chave = v.equipamento.nome
            if chave not in itens:
                itens[chave] = {"nome": chave, "quantidade": 0, "equipamento_id": v.equipamento_id}
            itens[chave]["quantidade"] += v.quantidade
        for campo in moedas:
            moedas[campo] += getattr(ficha, campo) or 0
    if crs_mortos:
        cr_medio = sum(crs_mortos) / len(crs_mortos)
        for campo, valor in _rolar_moeda_por_cr_medio(cr_medio).items():
            moedas[campo] = moedas.get(campo, 0) + valor
    return {"itens": list(itens.values()), "moedas": moedas}


def aplicar_loot(sessao: Session, combate: banco.Combate, escolhas: list[dict]) -> dict:
    """`escolhas`: lista de {"tipo": "item"|"moeda", "equipamento_id"?, "campo_moeda"?,
    "quantidade", "modo": "dividir"|"individual", "ficha_id"?} — "dividir" aplica a todos os
    jogadores participantes (quantidade // n, resto fica com o primeiro); "individual" exige
    `ficha_id` do jogador escolhido."""
    jogadores = [p.ficha for p in combate.participantes if p.ficha.personagem.tipo == "jogador"]
    if not jogadores:
        raise ValueError("Nenhum jogador participou deste combate.")
    aplicado = []
    for escolha in escolhas:
        quantidade = max(0, pa._para_numero(escolha.get("quantidade"), 0))
        if quantidade <= 0:
            continue
        if escolha.get("modo") == "individual":
            destino_id = escolha.get("ficha_id")
            destinos = [f for f in jogadores if f.id == destino_id]
            if not destinos:
                raise ValueError("Jogador de destino não encontrado entre os participantes.")
            partes = [(destinos[0], quantidade)]
        else:
            n = len(jogadores)
            base_q = quantidade // n
            resto = quantidade - base_q * n
            partes = [(f, base_q + (resto if i == 0 else 0)) for i, f in enumerate(jogadores)]

        for ficha, parte in partes:
            if parte <= 0:
                continue
            if escolha.get("tipo") == "moeda":
                campo = escolha["campo_moeda"]
                setattr(ficha, campo, (getattr(ficha, campo) or 0) + parte)
            else:
                equipamento_id = escolha["equipamento_id"]
                vinculo = next(
                    (v for v in ficha.equipamentos_vinculo if v.equipamento_id == equipamento_id), None,
                )
                if vinculo is None:
                    sessao.add(banco.FichaEquipamento(
                        ficha_id=ficha.id, equipamento_id=equipamento_id, quantidade=parte, equipado=False,
                    ))
                else:
                    vinculo.quantidade += parte
            aplicado.append({"ficha_id": ficha.id, "quantidade": parte, "escolha": escolha})
    sessao.commit()
    return {"aplicado": aplicado}
