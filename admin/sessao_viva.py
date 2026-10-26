"""Combate ao vivo — rastreador de iniciativa e notas para usar durante a mesa, preso à página da
sessão (ex.: docs/mestre/sessao-0-os-grilhoes-da-estrada.md).

Isolado do Flask de propósito, como wiki_data.py: todas as funções recebem `root` (a raiz do
projeto) para dar para testar contra uma cópia de teste em vez do projeto real. Ao contrário de
wiki_data.py, nada aqui mexe em docs/ nem em mkdocs.yml — o estado mora em admin/dados/, que fica
de fora do repositório git (é rascunho de mesa, não cânone nem conteúdo da wiki).

Cada página tem seu próprio arquivo de estado (espelhando o caminho dela dentro de
admin/dados/combates/), então o combate da Sessão 0 não se mistura com o de outra sessão.
"""
from __future__ import annotations

import copy
import datetime
import json
from pathlib import Path

TIPOS_COMBATENTE = ["jogador", "npc"]
TIPOS_ACAO = ["ataque", "cura", "outro"]
ROTULOS_ACAO = {"ataque": "Ataque", "cura": "Cura", "outro": "Outro"}

ESTADO_VAZIO = {
    "resumo": "",
    "notas": [],  # [{hora, texto}]
    "combatentes": [],  # ver adicionar_combatente()
    "rodada": 1,
    "turno_atual": None,  # id do combatente da vez
    "log_acoes": [],  # ver registrar_acao()
    "proximo_id": 1,
}


def _arquivo_estado(root: Path, pagina_rel_docs: str) -> Path:
    relativo = Path(pagina_rel_docs).with_suffix(".json")
    return root / "admin" / "dados" / "combates" / relativo


def _pasta_arquivadas(root: Path, pagina_rel_docs: str) -> Path:
    nome_base = Path(pagina_rel_docs).stem
    return root / "admin" / "dados" / "combates" / "arquivadas" / Path(pagina_rel_docs).parent / nome_base


def carregar(root: Path, pagina_rel_docs: str) -> dict:
    caminho = _arquivo_estado(root, pagina_rel_docs)
    if not caminho.exists():
        return copy.deepcopy(ESTADO_VAZIO)
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return copy.deepcopy(ESTADO_VAZIO)


def salvar(root: Path, pagina_rel_docs: str, estado: dict) -> None:
    caminho = _arquivo_estado(root, pagina_rel_docs)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def tem_combate_salvo(root: Path, pagina_rel_docs: str) -> bool:
    return _arquivo_estado(root, pagina_rel_docs).exists()


def _novo_id(estado: dict) -> int:
    id_ = estado.get("proximo_id", 1)
    estado["proximo_id"] = id_ + 1
    return id_


def combatentes_ordenados(estado: dict) -> list[dict]:
    """Por iniciativa (maior primeiro); empate desfeito pelo nome, pra ordem não embaralhar à
    toa a cada recarregamento de página."""
    return sorted(estado["combatentes"], key=lambda c: (-c["iniciativa"], c["nome"]))


def ordem_de_exibicao(estado: dict) -> list[dict]:
    """A mesma ordem de iniciativa, mas girada para começar em quem está na vez — assim o
    combatente ativo sempre aparece no topo da lista, sem precisar caçar a linha destacada."""
    ordenados = combatentes_ordenados(estado)
    if not ordenados or estado.get("turno_atual") is None:
        return ordenados
    ids = [c["id"] for c in ordenados]
    if estado["turno_atual"] not in ids:
        return ordenados
    idx = ids.index(estado["turno_atual"])
    return ordenados[idx:] + ordenados[:idx]


def _combatente_por_id(estado: dict, cid: int) -> dict | None:
    for c in estado["combatentes"]:
        if c["id"] == cid:
            return c
    return None


# --------------------------------------------------------------------------
# Notas e resumo
# --------------------------------------------------------------------------

def adicionar_nota(root: Path, pagina_rel_docs: str, texto: str) -> dict:
    estado = carregar(root, pagina_rel_docs)
    texto = texto.strip()
    if texto:
        hora = datetime.datetime.now().strftime("%H:%M")
        estado["notas"].append({"hora": hora, "texto": texto})
        salvar(root, pagina_rel_docs, estado)
    return estado


def remover_nota(root: Path, pagina_rel_docs: str, indice: int) -> dict:
    estado = carregar(root, pagina_rel_docs)
    if 0 <= indice < len(estado["notas"]):
        estado["notas"].pop(indice)
        salvar(root, pagina_rel_docs, estado)
    return estado


def salvar_resumo(root: Path, pagina_rel_docs: str, resumo: str) -> dict:
    estado = carregar(root, pagina_rel_docs)
    estado["resumo"] = resumo
    salvar(root, pagina_rel_docs, estado)
    return estado


# --------------------------------------------------------------------------
# Combatentes e iniciativa
# --------------------------------------------------------------------------

def adicionar_combatente(
    root: Path,
    pagina_rel_docs: str,
    nome: str,
    tipo: str,
    iniciativa: int,
    pv_atual: int | None,
    pv_maximo: int | None,
    ficha_pagina: str = "",
    ficha_slug: str = "",
) -> dict:
    estado = carregar(root, pagina_rel_docs)
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
        "ficha_pagina": ficha_pagina or "",
        "ficha_slug": ficha_slug or "",
    })
    # turno_atual fica em None até o Mestre clicar em "Próximo turno" pela primeira vez — assim,
    # adicionar todo mundo antes de começar (o fluxo normal) não fica pulando de combatente em
    # combatente a cada novo nome digitado.
    salvar(root, pagina_rel_docs, estado)
    return estado


def remover_combatente(root: Path, pagina_rel_docs: str, cid: int) -> dict:
    estado = carregar(root, pagina_rel_docs)
    estado["combatentes"] = [c for c in estado["combatentes"] if c["id"] != cid]
    if estado["turno_atual"] == cid:
        ordenados = combatentes_ordenados(estado)
        estado["turno_atual"] = ordenados[0]["id"] if ordenados else None
    salvar(root, pagina_rel_docs, estado)
    return estado


def ajustar_pv(root: Path, pagina_rel_docs: str, cid: int, delta: int) -> dict:
    estado = carregar(root, pagina_rel_docs)
    c = _combatente_por_id(estado, cid)
    if c is not None:
        c["pv_atual"] = max(0, (c.get("pv_atual") or 0) + delta)
        salvar(root, pagina_rel_docs, estado)
    return estado


def atualizar_status(root: Path, pagina_rel_docs: str, cid: int, status_texto: str) -> dict:
    estado = carregar(root, pagina_rel_docs)
    c = _combatente_por_id(estado, cid)
    if c is not None:
        c["status"] = [s.strip() for s in status_texto.split(",") if s.strip()]
        salvar(root, pagina_rel_docs, estado)
    return estado


def alternar_flag(root: Path, pagina_rel_docs: str, cid: int, campo: str) -> dict:
    """campo precisa ser 'caido' ou 'morto' — qualquer outro valor é ignorado."""
    if campo not in ("caido", "morto"):
        return carregar(root, pagina_rel_docs)
    estado = carregar(root, pagina_rel_docs)
    c = _combatente_por_id(estado, cid)
    if c is not None:
        c[campo] = not c[campo]
        salvar(root, pagina_rel_docs, estado)
    return estado


def proximo_turno(root: Path, pagina_rel_docs: str) -> dict:
    estado = carregar(root, pagina_rel_docs)
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
    salvar(root, pagina_rel_docs, estado)
    return estado


# --------------------------------------------------------------------------
# Ações (ataque / cura / outro) — o log usado pro diário de combate e a análise depois
# --------------------------------------------------------------------------

def registrar_acao(
    root: Path,
    pagina_rel_docs: str,
    autor_id: int | None,
    tipo: str,
    alvo_id: int | None,
    meio: str,
    valor: int | None,
    obs: str,
) -> dict:
    estado = carregar(root, pagina_rel_docs)
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
        "meio": meio.strip(),
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

    salvar(root, pagina_rel_docs, estado)
    return estado


def remover_acao(root: Path, pagina_rel_docs: str, acao_id: int) -> dict:
    estado = carregar(root, pagina_rel_docs)
    estado["log_acoes"] = [a for a in estado["log_acoes"] if a["id"] != acao_id]
    salvar(root, pagina_rel_docs, estado)
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


def _frase_acao(a: dict) -> str:
    meio = f" com {a['meio']}" if a.get("meio") else ""
    if a["tipo"] == "ataque":
        alvo = f" {a['alvo_nome']}" if a["alvo_nome"] else ""
        valor = f", causando {a['valor']} de dano" if a.get("valor") else ""
        frase = f"**{a['autor_nome']}** atacou{alvo}{meio}{valor}."
    elif a["tipo"] == "cura":
        alvo = f" {a['alvo_nome']}" if a["alvo_nome"] else ""
        valor = f" em {a['valor']} pontos de vida" if a.get("valor") else ""
        frase = f"**{a['autor_nome']}** curou{alvo}{valor}{meio}."
    else:
        frase = f"**{a['autor_nome']}**{meio}: {a['obs'] or '(sem detalhes)'}"
    if a["tipo"] != "outro" and a.get("obs"):
        frase += f" {a['obs']}"
    return frase


def gerar_diario_de_combate(estado: dict) -> list[dict]:
    """Agrupa o log por rodada e gera uma frase pronta por ação — rascunho pra colar (e editar)
    na história da campanha depois."""
    por_rodada: dict[int, list[str]] = {}
    for a in estado["log_acoes"]:
        por_rodada.setdefault(a["rodada"], []).append(_frase_acao(a))
    return [
        {"rodada": rodada, "frases": frases}
        for rodada, frases in sorted(por_rodada.items())
    ]


def arquivar_e_limpar(root: Path, pagina_rel_docs: str) -> Path:
    """Guarda o estado atual (notas, combate, log) num arquivo com data/hora e recomeça do zero
    — útil quando a mesma página de sessão vai ter mais de um combate ao longo do tempo."""
    estado = carregar(root, pagina_rel_docs)
    quando = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    destino = _pasta_arquivadas(root, pagina_rel_docs) / f"{quando}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    salvar(root, pagina_rel_docs, copy.deepcopy(ESTADO_VAZIO))
    return destino
