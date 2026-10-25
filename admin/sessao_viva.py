"""Sessão ao vivo — bloco de notas e rastreador de iniciativa para usar durante a mesa.

Isolado do Flask de propósito, como wiki_data.py: todas as funções recebem `root` (a raiz do
projeto) para dar para testar contra uma cópia de teste em vez do projeto real. Ao contrário de
wiki_data.py, nada aqui mexe em docs/ nem em mkdocs.yml — o estado mora em admin/dados/, que fica
de fora do repositório git (é rascunho de mesa, não cânone nem conteúdo da wiki).
"""
from __future__ import annotations

import copy
import datetime
import json
from pathlib import Path

TIPOS_COMBATENTE = ["jogador", "npc"]
TIPOS_ACAO = ["ataque", "cura", "outro"]

ESTADO_VAZIO = {
    "resumo": "",
    "notas": [],  # [{hora, texto}]
    "combatentes": [],  # [{id, nome, tipo, iniciativa, pv_atual, pv_maximo, status, caido, morto}]
    "rodada": 1,
    "turno_atual": None,  # id do combatente da vez
    "log_acoes": [],  # [{id, rodada, autor_id, autor_nome, tipo, alvo_id, alvo_nome, valor, obs}]
    "proximo_id": 1,
}


def _arquivo_estado(root: Path) -> Path:
    return root / "admin" / "dados" / "sessao_ao_vivo.json"


def _pasta_arquivadas(root: Path) -> Path:
    return root / "admin" / "dados" / "arquivadas"


def carregar(root: Path) -> dict:
    caminho = _arquivo_estado(root)
    if not caminho.exists():
        return copy.deepcopy(ESTADO_VAZIO)
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return copy.deepcopy(ESTADO_VAZIO)


def salvar(root: Path, estado: dict) -> None:
    caminho = _arquivo_estado(root)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def _novo_id(estado: dict) -> int:
    id_ = estado.get("proximo_id", 1)
    estado["proximo_id"] = id_ + 1
    return id_


def combatentes_ordenados(estado: dict) -> list[dict]:
    """Por iniciativa (maior primeiro); empate desfeito pelo nome, para a ordem não pular a cada
    recarregamento de página."""
    return sorted(estado["combatentes"], key=lambda c: (-c["iniciativa"], c["nome"]))


def _combatente_por_id(estado: dict, cid: int) -> dict | None:
    for c in estado["combatentes"]:
        if c["id"] == cid:
            return c
    return None


# --------------------------------------------------------------------------
# Notas e resumo
# --------------------------------------------------------------------------

def adicionar_nota(root: Path, texto: str) -> dict:
    estado = carregar(root)
    texto = texto.strip()
    if texto:
        hora = datetime.datetime.now().strftime("%H:%M")
        estado["notas"].append({"hora": hora, "texto": texto})
        salvar(root, estado)
    return estado


def remover_nota(root: Path, indice: int) -> dict:
    estado = carregar(root)
    if 0 <= indice < len(estado["notas"]):
        estado["notas"].pop(indice)
        salvar(root, estado)
    return estado


def salvar_resumo(root: Path, resumo: str) -> dict:
    estado = carregar(root)
    estado["resumo"] = resumo
    salvar(root, estado)
    return estado


# --------------------------------------------------------------------------
# Combatentes e iniciativa
# --------------------------------------------------------------------------

def adicionar_combatente(
    root: Path, nome: str, tipo: str, iniciativa: int, pv_atual: int | None, pv_maximo: int | None,
) -> dict:
    estado = carregar(root)
    if tipo not in TIPOS_COMBATENTE:
        tipo = "npc"
    cid = _novo_id(estado)
    estado["combatentes"].append({
        "id": cid,
        "nome": nome.strip() or f"Combatente {cid}",
        "tipo": tipo,
        "iniciativa": iniciativa,
        "pv_atual": pv_atual,
        "pv_maximo": pv_maximo,
        "status": [],
        "caido": False,
        "morto": False,
    })
    # turno_atual fica em None até o Mestre clicar em "Próximo turno" pela primeira vez — assim,
    # adicionar todo mundo antes de começar (o fluxo normal) não fica pulando de combatente em
    # combatente a cada novo nome digitado.
    salvar(root, estado)
    return estado


def remover_combatente(root: Path, cid: int) -> dict:
    estado = carregar(root)
    estado["combatentes"] = [c for c in estado["combatentes"] if c["id"] != cid]
    if estado["turno_atual"] == cid:
        ordenados = combatentes_ordenados(estado)
        estado["turno_atual"] = ordenados[0]["id"] if ordenados else None
    salvar(root, estado)
    return estado


def ajustar_pv(root: Path, cid: int, delta: int) -> dict:
    estado = carregar(root)
    c = _combatente_por_id(estado, cid)
    if c is not None:
        c["pv_atual"] = max(0, (c.get("pv_atual") or 0) + delta)
        salvar(root, estado)
    return estado


def atualizar_status(root: Path, cid: int, status_texto: str) -> dict:
    estado = carregar(root)
    c = _combatente_por_id(estado, cid)
    if c is not None:
        c["status"] = [s.strip() for s in status_texto.split(",") if s.strip()]
        salvar(root, estado)
    return estado


def alternar_flag(root: Path, cid: int, campo: str) -> dict:
    """campo precisa ser 'caido' ou 'morto' — qualquer outro valor é ignorado."""
    if campo not in ("caido", "morto"):
        return carregar(root)
    estado = carregar(root)
    c = _combatente_por_id(estado, cid)
    if c is not None:
        c[campo] = not c[campo]
        salvar(root, estado)
    return estado


def proximo_turno(root: Path) -> dict:
    estado = carregar(root)
    ordenados = combatentes_ordenados(estado)
    if not ordenados:
        return estado
    ids = [c["id"] for c in ordenados]
    if estado["turno_atual"] not in ids:
        estado["turno_atual"] = ids[0]
    else:
        idx = ids.index(estado["turno_atual"])
        if idx + 1 < len(ids):
            estado["turno_atual"] = ids[idx + 1]
        else:
            estado["turno_atual"] = ids[0]
            estado["rodada"] += 1
    salvar(root, estado)
    return estado


# --------------------------------------------------------------------------
# Ações (ataque / cura / outro) — o log usado para a análise depois
# --------------------------------------------------------------------------

def registrar_acao(
    root: Path, autor_id: int | None, tipo: str, alvo_id: int | None, valor: int | None, obs: str,
) -> dict:
    estado = carregar(root)
    if tipo not in TIPOS_ACAO:
        tipo = "outro"
    nomes = {c["id"]: c["nome"] for c in estado["combatentes"]}
    entrada = {
        "id": _novo_id(estado),
        "rodada": estado["rodada"],
        "autor_id": autor_id,
        "autor_nome": nomes.get(autor_id, "—"),
        "tipo": tipo,
        "alvo_id": alvo_id,
        "alvo_nome": nomes.get(alvo_id, "") if alvo_id else "",
        "valor": valor,
        "obs": obs.strip(),
    }
    estado["log_acoes"].append(entrada)

    # Aplica o efeito automaticamente no PV do alvo, pra não precisar lançar duas vezes.
    if alvo_id and valor:
        delta = -valor if tipo == "ataque" else valor if tipo == "cura" else 0
        if delta:
            alvo = _combatente_por_id(estado, alvo_id)
            if alvo is not None:
                alvo["pv_atual"] = max(0, (alvo.get("pv_atual") or 0) + delta)

    salvar(root, estado)
    return estado


def remover_acao(root: Path, acao_id: int) -> dict:
    estado = carregar(root)
    estado["log_acoes"] = [a for a in estado["log_acoes"] if a["id"] != acao_id]
    salvar(root, estado)
    return estado


def resumo_combate(estado: dict) -> dict:
    """Agrega o log de ações para responder 'quem bateu mais, quem recebeu mais dano'."""
    dano_causado: dict[str, int] = {}
    dano_recebido: dict[str, int] = {}
    cura_feita: dict[str, int] = {}
    golpes: dict[str, int] = {}

    for a in estado["log_acoes"]:
        valor = a.get("valor") or 0
        if a["tipo"] == "ataque" and valor:
            dano_causado[a["autor_nome"]] = dano_causado.get(a["autor_nome"], 0) + valor
            golpes[a["autor_nome"]] = golpes.get(a["autor_nome"], 0) + 1
            if a["alvo_nome"]:
                dano_recebido[a["alvo_nome"]] = dano_recebido.get(a["alvo_nome"], 0) + valor
        elif a["tipo"] == "cura" and valor:
            cura_feita[a["autor_nome"]] = cura_feita.get(a["autor_nome"], 0) + valor

    def _ordenado(d: dict[str, int]) -> list[tuple[str, int]]:
        return sorted(d.items(), key=lambda kv: -kv[1])

    return {
        "dano_causado": _ordenado(dano_causado),
        "dano_recebido": _ordenado(dano_recebido),
        "cura_feita": _ordenado(cura_feita),
        "golpes": _ordenado(golpes),
    }


def arquivar_e_limpar(root: Path) -> Path:
    """Guarda o estado atual (notas, combate, log) num arquivo com data/hora e recomeça do zero."""
    estado = carregar(root)
    quando = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    destino = _pasta_arquivadas(root) / f"{quando}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    salvar(root, copy.deepcopy(ESTADO_VAZIO))
    return destino
