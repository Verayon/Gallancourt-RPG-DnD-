"""Lógica de leitura/escrita das fichas de personagem no banco (ver admin/banco.py) — isolado do
Flask de propósito, como wiki_data.py/sessao_viva.py: toda função recebe uma `Session` já aberta.

Modelo: um `Personagem` (monstro, NPC nomeado ou jogador — ver `banco.TIPOS_ATOR`) tem uma ou mais
`Ficha` (a primeira é sempre a "Base", nunca removível; as demais são variantes, cópias
independentes e totalmente editáveis — ver docs/mestre/manutencao-do-canone.md). Equipamento/
Habilidades/Magias/Idiomas/Sentidos/Perícias são catálogos compartilhados (`banco.Equipamento` etc.),
vinculados a cada ficha por uma tabela de associação própria. Espaços de magia/Condições/Efeitos
NÃO são catálogos — são próprios de cada ficha, sem valor de reuso entre personagens. Biografia e
Diário moram no `Personagem`, não na `Ficha` — pertencem ao personagem, não a uma variante.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session, selectinload

import banco

EXTENSOES_FOTO_PERMITIDAS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# Mapeia a chave curta usada em toda a UI/API (igual a admin/wiki_data.py::CAMPOS_STATBLOCK_ATRIBUTOS)
# para o nome da coluna em Ficha (não dá pra usar "for" como nome de coluna — é palavra
# reservada do Python).
CAMPO_ATRIBUTO_DB = {
    "for": "forca", "des": "destreza", "con": "constituicao",
    "int": "inteligencia", "sab": "sabedoria", "car": "carisma",
}
ATRIBUTOS_CURTOS = list(CAMPO_ATRIBUTO_DB.keys())

# Campos simples de Ficha que a tela de edição pode gravar direto (fora os vínculos de catálogo e
# as listas próprias — espaços de magia/condições/efeitos —, que têm suas próprias funções
# abaixo). `pv_atual` fica de fora de propósito — só importa durante um combate (sistema futuro),
# não faz sentido editar numa ficha de catálogo.
CAMPOS_FICHA_EDITAVEIS = [
    "rotulo", "cr", "nivel", "xp", "classe", "subclasse", "antecedente", "bonus_proficiencia",
    "ca_total", "pv_formula", "pv_maximo", "pv_temporario", "dados_vida_total",
    "dados_vida_usados", "deslocamento_m", "deslocamento_extra", "percepcao_passiva",
    "investigacao_passiva", "intuicao_passiva", "iniciativa_extra", "cd_conjuracao",
    "bonus_ataque_magico", "carga_maxima", "moeda_pc", "moeda_pp", "moeda_pe", "moeda_po",
    "moeda_pl", *CAMPO_ATRIBUTO_DB.values(),
]

# Campos de Personagem (biografia) que a tela de edição pode gravar direto.
CAMPOS_PERSONAGEM_EDITAVEIS = [
    "genero", "idade", "altura", "peso_corporal", "olhos", "cabelo", "pele", "fe",
    "aparencia", "personalidade", "traco", "ideal", "vinculo", "defeito",
    "pessoas_interesse", "lugares_interesse",
]

# Valores padrão de CR do D&D 5e (SRD) e o XP equivalente — pra alimentar a lista suspensa e
# mostrar o XP sem precisar guardar os dois juntos no banco (ver Ficha.cr, usado só por monstro).
CR_OPCOES = [
    "0", "1/8", "1/4", "1/2", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24",
    "25", "26", "27", "28", "29", "30",
]
CR_PARA_XP = {
    "0": 10, "1/8": 25, "1/4": 50, "1/2": 100, "1": 200, "2": 450, "3": 700, "4": 1100,
    "5": 1800, "6": 2300, "7": 2900, "8": 3900, "9": 5000, "10": 5900, "11": 7200, "12": 8400,
    "13": 10000, "14": 11500, "15": 13000, "16": 15000, "17": 18000, "18": 20000, "19": 22000,
    "20": 25000, "21": 33000, "22": 41000, "23": 50000, "24": 62000, "25": 75000, "26": 90000,
    "27": 105000, "28": 120000, "29": 135000, "30": 155000,
}

# (tipo da API, modelo do catálogo, modelo de vínculo, coluna FK do vínculo pro catálogo)
_CATALOGOS = {
    "equipamentos": (banco.Equipamento, banco.FichaEquipamento, "equipamento_id"),
    "habilidades": (banco.Habilidade, banco.FichaHabilidade, "habilidade_id"),
    "magias": (banco.Magia, banco.FichaMagia, "magia_id"),
    "idiomas": (banco.Idioma, banco.FichaIdioma, "idioma_id"),
    "sentidos": (banco.Sentido, banco.FichaSentido, "sentido_id"),
    "pericias": (banco.Pericia, banco.FichaPericia, "pericia_id"),
}

CAMPOS_EQUIPAMENTO = [
    "nome", "categoria", "custo", "peso_kg", "dano_formula", "dano_tipo", "propriedades",
    "ca_bonus", "ca_formula", "raridade", "fonte", "descricao", "slug_origem", "origem_tipo",
    "origem_personagem_slug", "tipo_acao", "cargas_maximo", "e_container", "capacidade_kg",
]

# Campos do vínculo (FichaEquipamento) que a UI pode editar depois que o item já foi adicionado —
# diferente dos outros tipos de vínculo, que só favoritam/removem (ver PUT /equipamentos/<vinculo>).
CAMPOS_FICHA_EQUIPAMENTO_EDITAVEIS = ["quantidade", "equipado", "guardado_em_vinculo_id"]
CAMPOS_HABILIDADE = [
    "nome", "tipo", "bonus_acerto", "dano_formula", "dano_tipo", "alcance", "usos", "descricao",
    "origem_tipo", "origem_personagem_slug", "tipo_acao",
]
CAMPOS_MAGIA = [
    "nome", "nivel", "escola", "tempo", "alcance", "componentes", "duracao", "classes",
    "dano_formula", "dano_tipo", "resistencia", "fonte", "descricao", "slug_origem", "tipo_acao",
]
CAMPOS_IDIOMA = ["nome"]
CAMPOS_SENTIDO = ["nome"]
CAMPOS_PERICIA = ["nome", "atributo", "fonte", "slug_origem"]
_CAMPOS_CATALOGO = {
    "equipamentos": CAMPOS_EQUIPAMENTO, "habilidades": CAMPOS_HABILIDADE, "magias": CAMPOS_MAGIA,
    "idiomas": CAMPOS_IDIOMA, "sentidos": CAMPOS_SENTIDO, "pericias": CAMPOS_PERICIA,
}


def modificador(valor: int) -> int:
    return (valor - 10) // 2


def _assinado(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _obj_para_dict(obj, campos: list[str]) -> dict:
    return {c: getattr(obj, c) for c in campos} | {"id": obj.id}


def _para_numero(valor, padrao):
    try:
        if isinstance(padrao, float):
            return float(valor)
        return int(float(valor))
    except (TypeError, ValueError):
        return padrao


def obter_personagem(sessao: Session, tipo: str, slug: str) -> banco.Personagem | None:
    return (
        sessao.query(banco.Personagem)
        .options(selectinload(banco.Personagem.fichas), selectinload(banco.Personagem.diario_vinculo))
        .filter(banco.Personagem.tipo == tipo, banco.Personagem.slug == slug)
        .first()
    )


def obter_ficha(sessao: Session, ficha_id: int) -> banco.Ficha | None:
    return sessao.get(banco.Ficha, ficha_id)


def criar_personagem(
    sessao: Session, tipo: str, slug: str, nome: str,
    tamanho: str | None = None, tipo_criatura: str | None = None, alinhamento: str | None = None,
) -> banco.Personagem:
    if tipo not in banco.TIPOS_ATOR:
        raise ValueError(f"Tipo de personagem desconhecido: {tipo}")
    personagem = banco.Personagem(
        tipo=tipo, slug=slug, nome=nome, tamanho=tamanho, tipo_criatura=tipo_criatura,
        alinhamento=alinhamento,
    )
    sessao.add(personagem)
    sessao.flush()
    return personagem


def serializar_ficha(ficha: banco.Ficha) -> dict:
    atributos = {}
    for curto, coluna in CAMPO_ATRIBUTO_DB.items():
        valor = getattr(ficha, coluna)
        atributos[curto] = {"valor": valor, "modificador": _assinado(modificador(valor))}
    return {
        "id": ficha.id,
        "rotulo": ficha.rotulo,
        "is_base": ficha.is_base,
        "cr": ficha.cr,
        "cr_xp": CR_PARA_XP.get(ficha.cr or ""),
        "nivel": ficha.nivel,
        "xp": ficha.xp,
        "classe": ficha.classe,
        "subclasse": ficha.subclasse,
        "antecedente": ficha.antecedente,
        "bonus_proficiencia": ficha.bonus_proficiencia,
        "atributos": atributos,
        "ca_total": ficha.ca_total,
        "pv_formula": ficha.pv_formula,
        "pv_maximo": ficha.pv_maximo,
        "pv_atual": ficha.pv_atual,
        "pv_temporario": ficha.pv_temporario,
        "dados_vida_total": ficha.dados_vida_total,
        "dados_vida_usados": ficha.dados_vida_usados,
        "deslocamento_m": ficha.deslocamento_m,
        "deslocamento_extra": ficha.deslocamento_extra,
        "percepcao_passiva": ficha.percepcao_passiva,
        "investigacao_passiva": ficha.investigacao_passiva,
        "intuicao_passiva": ficha.intuicao_passiva,
        "iniciativa_extra": ficha.iniciativa_extra,
        "cd_conjuracao": ficha.cd_conjuracao,
        "bonus_ataque_magico": ficha.bonus_ataque_magico,
        "carga_maxima": ficha.carga_maxima,
        "moeda_pc": ficha.moeda_pc, "moeda_pp": ficha.moeda_pp, "moeda_pe": ficha.moeda_pe,
        "moeda_po": ficha.moeda_po, "moeda_pl": ficha.moeda_pl,
        "equipamentos": [
            {"vinculo_id": v.id, "quantidade": v.quantidade, "equipado": v.equipado,
             "favorito": v.favorito, "guardado_em_vinculo_id": v.guardado_em_vinculo_id,
             "cargas_atual": (v.cargas_atual if v.cargas_atual is not None else v.equipamento.cargas_maximo),
             **_obj_para_dict(v.equipamento, CAMPOS_EQUIPAMENTO)}
            for v in sorted(ficha.equipamentos_vinculo, key=lambda v: not v.favorito)
        ],
        "habilidades": [
            {
                "vinculo_id": v.id, "favorito": v.favorito, "usos_maximo": v.usos_maximo,
                "usos_restantes": v.usos_restantes, "tipo_descanso": v.tipo_descanso,
                **_obj_para_dict(v.habilidade, CAMPOS_HABILIDADE),
            }
            for v in sorted(ficha.habilidades_vinculo, key=lambda v: not v.favorito)
        ],
        "magias": [
            {"vinculo_id": v.id, "favorito": v.favorito, **_obj_para_dict(v.magia, CAMPOS_MAGIA)}
            for v in sorted(ficha.magias_vinculo, key=lambda v: not v.favorito)
        ],
        "idiomas": [
            {"vinculo_id": v.id, **_obj_para_dict(v.idioma, CAMPOS_IDIOMA)}
            for v in ficha.idiomas_vinculo
        ],
        "sentidos": [
            {"vinculo_id": v.id, "valor": v.valor, **_obj_para_dict(v.sentido, CAMPOS_SENTIDO)}
            for v in ficha.sentidos_vinculo
        ],
        "pericias": [
            {"vinculo_id": v.id, "bonus": v.bonus, **_obj_para_dict(v.pericia, CAMPOS_PERICIA)}
            for v in ficha.pericias_vinculo
        ],
        "espacos_magia": [
            {"vinculo_id": v.id, "nivel": v.nivel, "maximo": v.maximo, "usado": v.usado, "rotulo": v.rotulo}
            for v in ficha.espacos_magia_vinculo
        ],
        "classes": [
            {
                "vinculo_id": v.id, "classe_id": v.classe_id, "classe_nome": v.classe.nome,
                "subclasse_id": v.subclasse_id, "subclasse_nome": v.subclasse.nome if v.subclasse_id else None,
                "nivel": v.nivel,
            }
            for v in sorted(ficha.classes_vinculo, key=lambda v: -v.nivel)
        ],
        "condicoes": [
            {"vinculo_id": v.id, "nome": v.nome} for v in ficha.condicoes_vinculo
        ],
        "resistencias_dano": [
            {"vinculo_id": v.id, "nome": v.nome, "modo": v.modo} for v in ficha.resistencias_dano_vinculo
        ],
        "efeitos": [
            {"vinculo_id": v.id, "nome": v.nome, "tipo": v.tipo, "origem": v.origem, "duracao": v.duracao}
            for v in ficha.efeitos_vinculo
        ],
    }


def serializar_personagem(personagem: banco.Personagem) -> dict:
    fichas = sorted(personagem.fichas, key=lambda f: (0 if f.is_base else 1, f.id))
    entradas_diario = sorted(personagem.diario_vinculo, key=lambda e: e.id, reverse=True)
    return {
        "tipo": personagem.tipo, "slug": personagem.slug, "nome": personagem.nome,
        "tamanho": personagem.tamanho, "tipo_criatura": personagem.tipo_criatura,
        "alinhamento": personagem.alinhamento, "foto": personagem.foto,
        "genero": personagem.genero, "idade": personagem.idade, "altura": personagem.altura,
        "peso_corporal": personagem.peso_corporal, "olhos": personagem.olhos,
        "cabelo": personagem.cabelo, "pele": personagem.pele, "fe": personagem.fe,
        "aparencia": personagem.aparencia, "personalidade": personagem.personalidade,
        "traco": personagem.traco,
        "ideal": personagem.ideal, "vinculo": personagem.vinculo, "defeito": personagem.defeito,
        "pessoas_interesse": personagem.pessoas_interesse,
        "lugares_interesse": personagem.lugares_interesse,
        "diario": [
            {"id": e.id, "data": e.data, "titulo": e.titulo, "texto": e.texto}
            for e in entradas_diario
        ],
        "fichas": [serializar_ficha(f) for f in fichas],
    }


def criar_variante(sessao: Session, personagem: banco.Personagem, rotulo: str) -> banco.Ficha:
    base = next((f for f in personagem.fichas if f.is_base), None)
    if base is None:
        raise ValueError("Este personagem não tem uma ficha Base ainda.")
    nova = banco.Ficha(
        personagem_id=personagem.id, rotulo=rotulo.strip() or "Variante", is_base=False,
        cr=base.cr, nivel=base.nivel, xp=base.xp, classe=base.classe, subclasse=base.subclasse,
        antecedente=base.antecedente, bonus_proficiencia=base.bonus_proficiencia,
        forca=base.forca, destreza=base.destreza, constituicao=base.constituicao,
        inteligencia=base.inteligencia, sabedoria=base.sabedoria, carisma=base.carisma,
        ca_total=base.ca_total, pv_formula=base.pv_formula, pv_maximo=base.pv_maximo,
        pv_atual=base.pv_atual, pv_temporario=base.pv_temporario,
        dados_vida_total=base.dados_vida_total, dados_vida_usados=base.dados_vida_usados,
        deslocamento_m=base.deslocamento_m, deslocamento_extra=base.deslocamento_extra,
        percepcao_passiva=base.percepcao_passiva, investigacao_passiva=base.investigacao_passiva,
        intuicao_passiva=base.intuicao_passiva, iniciativa_extra=base.iniciativa_extra,
        cd_conjuracao=base.cd_conjuracao, bonus_ataque_magico=base.bonus_ataque_magico,
        carga_maxima=base.carga_maxima,
        moeda_pc=base.moeda_pc, moeda_pp=base.moeda_pp, moeda_pe=base.moeda_pe,
        moeda_po=base.moeda_po, moeda_pl=base.moeda_pl,
    )
    sessao.add(nova)
    sessao.flush()
    for v in base.equipamentos_vinculo:
        sessao.add(banco.FichaEquipamento(
            ficha_id=nova.id, equipamento_id=v.equipamento_id, quantidade=v.quantidade, equipado=v.equipado,
        ))
    for v in base.habilidades_vinculo:
        sessao.add(banco.FichaHabilidade(
            ficha_id=nova.id, habilidade_id=v.habilidade_id, favorito=v.favorito,
            usos_maximo=v.usos_maximo, usos_restantes=v.usos_restantes, tipo_descanso=v.tipo_descanso,
        ))
    for v in base.magias_vinculo:
        sessao.add(banco.FichaMagia(ficha_id=nova.id, magia_id=v.magia_id, favorito=v.favorito))
    for v in base.idiomas_vinculo:
        sessao.add(banco.FichaIdioma(ficha_id=nova.id, idioma_id=v.idioma_id))
    for v in base.sentidos_vinculo:
        sessao.add(banco.FichaSentido(ficha_id=nova.id, sentido_id=v.sentido_id, valor=v.valor))
    for v in base.pericias_vinculo:
        sessao.add(banco.FichaPericia(ficha_id=nova.id, pericia_id=v.pericia_id, bonus=v.bonus))
    for v in base.espacos_magia_vinculo:
        sessao.add(banco.FichaEspacoMagia(
            ficha_id=nova.id, nivel=v.nivel, maximo=v.maximo, usado=v.usado, rotulo=v.rotulo,
        ))
    for v in base.condicoes_vinculo:
        sessao.add(banco.FichaCondicao(ficha_id=nova.id, nome=v.nome))
    for v in base.resistencias_dano_vinculo:
        sessao.add(banco.FichaResistenciaDano(ficha_id=nova.id, nome=v.nome, modo=v.modo))
    for v in base.efeitos_vinculo:
        sessao.add(banco.FichaEfeito(
            ficha_id=nova.id, nome=v.nome, tipo=v.tipo, origem=v.origem, duracao=v.duracao,
        ))
    sessao.commit()
    sessao.refresh(nova)
    return nova


# Mínimo de cada campo numérico editável — nenhum deles faz sentido negativo (ver
# docs/mestre/manutencao-do-canone.md). Atributo mínimo 1 porque 0 não existe no D&D 5e. Campos
# que também aceitam negativo de propósito (iniciativa_extra, perícia/habilidade bônus) ficam
# fora desta lista.
_MINIMOS_NUMERICOS = {
    "bonus_proficiencia": 0, "ca_total": 0, "pv_maximo": 1, "pv_temporario": 0,
    "dados_vida_usados": 0, "deslocamento_m": 0.0, "percepcao_passiva": 0,
    "carga_maxima": 0.0, "nivel": 1, "xp": 0,
    "moeda_pc": 0, "moeda_pp": 0, "moeda_pe": 0, "moeda_po": 0, "moeda_pl": 0,
    **{coluna: 1 for coluna in CAMPO_ATRIBUTO_DB.values()},
}


def atualizar_ficha(sessao: Session, ficha: banco.Ficha, campos: dict) -> banco.Ficha:
    for chave, valor in campos.items():
        if chave not in CAMPOS_FICHA_EDITAVEIS:
            continue
        minimo = _MINIMOS_NUMERICOS.get(chave)
        if minimo is not None and valor not in (None, ""):
            valor = max(minimo, _para_numero(valor, minimo))
        setattr(ficha, chave, valor)
    sessao.commit()
    sessao.refresh(ficha)
    return ficha


def atualizar_personagem(sessao: Session, personagem: banco.Personagem, campos: dict) -> banco.Personagem:
    for chave, valor in campos.items():
        if chave not in CAMPOS_PERSONAGEM_EDITAVEIS:
            continue
        setattr(personagem, chave, (valor or "").strip() or None if isinstance(valor, str) else valor)
    sessao.commit()
    sessao.refresh(personagem)
    return personagem


def excluir_ficha(sessao: Session, ficha: banco.Ficha) -> None:
    if ficha.is_base:
        raise ValueError("A ficha Base não pode ser excluída.")
    sessao.delete(ficha)
    sessao.commit()


def _modelo_catalogo(tipo: str):
    info = _CATALOGOS.get(tipo)
    if info is None:
        raise ValueError(f"Catálogo desconhecido: {tipo}")
    return info


def listar_catalogo(
    sessao: Session, tipo: str, busca: str = "", categoria: str = "", origem_personagem: str = "",
) -> list[dict]:
    modelo, _assoc, _fk = _modelo_catalogo(tipo)
    campos = _CAMPOS_CATALOGO[tipo]
    consulta = sessao.query(modelo)
    if busca:
        consulta = consulta.filter(modelo.nome.ilike(f"%{busca}%"))
    if categoria and hasattr(modelo, "categoria"):
        consulta = consulta.filter(modelo.categoria == categoria)
    if origem_personagem and hasattr(modelo, "origem_personagem_slug"):
        consulta = consulta.filter(modelo.origem_personagem_slug == origem_personagem)
    itens = consulta.order_by(modelo.nome).limit(500).all()
    return [_obj_para_dict(i, campos) for i in itens]


# Mínimo dos campos numéricos de cada catálogo (ver _MINIMOS_NUMERICOS acima, mesma lógica).
_MINIMOS_CATALOGO = {"ca_bonus": 0, "bonus_acerto": 0, "nivel": 0, "peso_kg": 0.0, "capacidade_kg": 0.0}


def criar_item_catalogo(sessao: Session, tipo: str, campos: dict) -> dict:
    modelo, _assoc, _fk = _modelo_catalogo(tipo)
    permitidos = _CAMPOS_CATALOGO[tipo]
    valores = {k: v for k, v in campos.items() if k in permitidos}
    if not (valores.get("nome") or "").strip():
        raise ValueError("Nome é obrigatório.")
    for chave, minimo in _MINIMOS_CATALOGO.items():
        if chave in valores and valores[chave] not in (None, ""):
            valores[chave] = max(minimo, _para_numero(valores[chave], minimo))
    if "e_container" in valores:
        valores["e_container"] = bool(valores["e_container"])
    obj = modelo(**valores)
    sessao.add(obj)
    sessao.commit()
    sessao.refresh(obj)
    return _obj_para_dict(obj, permitidos)


def adicionar_vinculo(sessao: Session, ficha: banco.Ficha, tipo: str, item_id: int, extra: dict | None = None) -> dict:
    modelo, assoc, fk = _modelo_catalogo(tipo)
    item = sessao.get(modelo, item_id)
    if item is None:
        raise ValueError(f"Item de catálogo não encontrado: {tipo}/{item_id}")
    dados = {"ficha_id": ficha.id, fk: item_id}
    extra = extra or {}
    if tipo == "equipamentos":
        dados["quantidade"] = max(1, _para_numero(extra.get("quantidade"), 1))
        dados["equipado"] = bool(extra.get("equipado", True))
    elif tipo == "sentidos":
        dados["valor"] = max(0.0, _para_numero(extra.get("valor"), 0.0)) if extra.get("valor") not in (None, "") else None
    elif tipo == "pericias":
        dados["bonus"] = _para_numero(extra.get("bonus"), 0)
    vinculo = assoc(**dados)
    sessao.add(vinculo)
    sessao.commit()
    sessao.refresh(vinculo)
    return {"vinculo_id": vinculo.id, **_obj_para_dict(item, _CAMPOS_CATALOGO[tipo])}


def atualizar_vinculo_equipamento(sessao: Session, ficha: banco.Ficha, vinculo_id: int, campos: dict) -> dict:
    """Edita quantidade/equipado/guardado_em_vinculo_id de um item já vinculado à ficha —
    adicionar_vinculo só define o valor inicial, isso aqui é a única forma de mudar depois (botão
    "Equipar"/seletor "Guardado em" na aba Inventário). Mover um item pra dentro de um contêiner
    (Equipamento.e_container) avisa, mas não bloqueia, quando passa de Equipamento.capacidade_kg —
    decisão de UX do próprio design: o Mestre decide se ignora o aviso."""
    vinculo = sessao.get(banco.FichaEquipamento, vinculo_id)
    if vinculo is None or vinculo.ficha_id != ficha.id:
        raise ValueError("Vínculo de equipamento não encontrado nesta ficha.")
    if "quantidade" in campos:
        vinculo.quantidade = max(1, _para_numero(campos.get("quantidade"), vinculo.quantidade))
    if "equipado" in campos:
        vinculo.equipado = bool(campos.get("equipado"))
    aviso = None
    if "guardado_em_vinculo_id" in campos:
        destino_id = campos.get("guardado_em_vinculo_id")
        destino_id = int(destino_id) if destino_id not in (None, "") else None
        if destino_id == vinculo.id:
            raise ValueError("Um item não pode guardar a si mesmo.")
        destino = sessao.get(banco.FichaEquipamento, destino_id) if destino_id else None
        if destino_id and (destino is None or destino.ficha_id != ficha.id):
            raise ValueError("Contêiner não encontrado nesta ficha.")
        vinculo.guardado_em_vinculo_id = destino_id
        if destino is not None and destino.equipamento.e_container and destino.equipamento.capacidade_kg is not None:
            peso_atual = sum(
                (v.equipamento.peso_kg or 0.0) * v.quantidade
                for v in ficha.equipamentos_vinculo
                if v.guardado_em_vinculo_id == destino.id and v.id != vinculo.id
            )
            peso_item = (vinculo.equipamento.peso_kg or 0.0) * vinculo.quantidade
            if peso_atual + peso_item > destino.equipamento.capacidade_kg + 1e-9:
                aviso = (
                    f"{vinculo.equipamento.nome} não cabe em {destino.equipamento.nome} "
                    f"(limite de {destino.equipamento.capacidade_kg:g} kg)."
                )
    sessao.commit()
    return {"aviso": aviso}


def atualizar_valor_sentido(sessao: Session, vinculo_id: int, valor) -> None:
    vinculo = sessao.get(banco.FichaSentido, vinculo_id)
    if vinculo is None:
        raise ValueError("Vínculo de sentido não encontrado.")
    vinculo.valor = max(0.0, _para_numero(valor, 0.0)) if valor not in (None, "") else None
    sessao.commit()


def atualizar_bonus_pericia(sessao: Session, vinculo_id: int, bonus) -> None:
    vinculo = sessao.get(banco.FichaPericia, vinculo_id)
    if vinculo is None:
        raise ValueError("Vínculo de perícia não encontrado.")
    vinculo.bonus = _para_numero(bonus, 0)  # pode ser negativo (ex.: criatura com -1 em Força)
    sessao.commit()


_VINCULOS_FAVORITAVEIS = {
    "habilidades": banco.FichaHabilidade, "magias": banco.FichaMagia,
    "equipamentos": banco.FichaEquipamento,
}


def alternar_favorito_vinculo(sessao: Session, tipo: str, vinculo_id: int) -> bool:
    """Favoritar/desfavoritar um Equipamento, Habilidade ou Magia desta ficha (acesso rápido — ver
    serializar_ficha, que ordena favoritos primeiro, e a lista de Favoritos na aba Atributos em
    docs/javascripts/ficha.js). `tipo` é "equipamentos"/"habilidades"/"magias", mesma chave usada
    em adicionar_vinculo."""
    modelo = _VINCULOS_FAVORITAVEIS.get(tipo)
    if modelo is None:
        raise ValueError(f"Vínculo sem favorito: {tipo}")
    vinculo = sessao.get(modelo, vinculo_id)
    if vinculo is None:
        raise ValueError("Vínculo não encontrado.")
    vinculo.favorito = not vinculo.favorito
    sessao.commit()
    return vinculo.favorito


def definir_usos_habilidade(sessao: Session, vinculo_id: int, campos: dict) -> None:
    """Liga/edita o contador de usos por descanso de uma Habilidade nesta ficha (ver
    FichaHabilidade.usos_maximo/usos_restantes/tipo_descanso) — `usos_maximo=None` desliga o
    contador (volta a ser só o texto livre de Habilidade.usos)."""
    vinculo = sessao.get(banco.FichaHabilidade, vinculo_id)
    if vinculo is None:
        raise ValueError("Vínculo de habilidade não encontrado.")
    if "usos_maximo" in campos:
        valor = campos["usos_maximo"]
        vinculo.usos_maximo = max(0, _para_numero(valor, 0)) if valor not in (None, "") else None
        vinculo.usos_restantes = vinculo.usos_maximo
    if "tipo_descanso" in campos:
        tipo_descanso = campos["tipo_descanso"] or None
        if tipo_descanso is not None and tipo_descanso not in banco.TIPOS_DESCANSO:
            raise ValueError(f"Tipo de descanso desconhecido: {tipo_descanso}")
        vinculo.tipo_descanso = tipo_descanso
    sessao.commit()


def consumir_uso_habilidade(sessao: Session, vinculo_id: int) -> int | None:
    """Gasta um uso (botão "usar" na ficha/Combat Tracker) — não deixa passar de 0."""
    vinculo = sessao.get(banco.FichaHabilidade, vinculo_id)
    if vinculo is None:
        raise ValueError("Vínculo de habilidade não encontrado.")
    if vinculo.usos_restantes is not None:
        vinculo.usos_restantes = max(0, vinculo.usos_restantes - 1)
        sessao.commit()
    return vinculo.usos_restantes


def remover_vinculo(sessao: Session, tipo: str, vinculo_id: int) -> None:
    _modelo, assoc, _fk = _modelo_catalogo(tipo)
    vinculo = sessao.get(assoc, vinculo_id)
    if vinculo is not None:
        sessao.delete(vinculo)
        sessao.commit()


# --------------------------------------------------------------------------
# Espaços de magia, Condições, Efeitos — próprios de cada ficha, não catálogos compartilhados.
# --------------------------------------------------------------------------

def criar_espaco_magia(sessao: Session, ficha: banco.Ficha, campos: dict) -> banco.FichaEspacoMagia:
    espaco = banco.FichaEspacoMagia(
        ficha_id=ficha.id,
        nivel=max(1, _para_numero(campos.get("nivel"), 1)),
        maximo=max(0, _para_numero(campos.get("maximo"), 1)),
        usado=max(0, _para_numero(campos.get("usado"), 0)),
        rotulo=(campos.get("rotulo") or "").strip() or None,
    )
    sessao.add(espaco)
    sessao.commit()
    sessao.refresh(espaco)
    return espaco


def atualizar_espaco_magia(sessao: Session, vinculo_id: int, campos: dict) -> None:
    espaco = sessao.get(banco.FichaEspacoMagia, vinculo_id)
    if espaco is None:
        raise ValueError("Pool de espaços de magia não encontrado.")
    if "nivel" in campos:
        espaco.nivel = max(1, _para_numero(campos["nivel"], espaco.nivel))
    if "maximo" in campos:
        espaco.maximo = max(0, _para_numero(campos["maximo"], espaco.maximo))
    if "usado" in campos:
        espaco.usado = max(0, _para_numero(campos["usado"], espaco.usado))
    if "rotulo" in campos:
        espaco.rotulo = (campos["rotulo"] or "").strip() or None
    sessao.commit()


def remover_espaco_magia(sessao: Session, vinculo_id: int) -> None:
    espaco = sessao.get(banco.FichaEspacoMagia, vinculo_id)
    if espaco is not None:
        sessao.delete(espaco)
        sessao.commit()


def adicionar_condicao(sessao: Session, ficha: banco.Ficha, nome: str) -> banco.FichaCondicao:
    if nome not in banco.CONDICOES_D20:
        raise ValueError(f"Condição desconhecida: {nome}")
    condicao = banco.FichaCondicao(ficha_id=ficha.id, nome=nome)
    sessao.add(condicao)
    sessao.commit()
    sessao.refresh(condicao)
    return condicao


def remover_condicao(sessao: Session, vinculo_id: int) -> None:
    condicao = sessao.get(banco.FichaCondicao, vinculo_id)
    if condicao is not None:
        sessao.delete(condicao)
        sessao.commit()


def alternar_resistencia_dano(sessao: Session, ficha: banco.Ficha, nome: str, modo: str) -> list[dict]:
    """Clicar no `modo` já ativo pra este tipo de dano remove; clicar num `modo` diferente troca
    (só um modo ativo por tipo de dano) — mesma ideia de alternar_condicao, mas com 3 estados em
    vez de ligado/desligado."""
    if nome not in banco.TIPOS_DANO:
        raise ValueError(f"Tipo de dano desconhecido: {nome}")
    if modo not in banco.MODOS_RESISTENCIA_DANO:
        raise ValueError(f"Modo de resistência desconhecido: {modo}")
    existente = next((v for v in ficha.resistencias_dano_vinculo if v.nome == nome), None)
    if existente is not None and existente.modo == modo:
        sessao.delete(existente)
    elif existente is not None:
        existente.modo = modo
    else:
        sessao.add(banco.FichaResistenciaDano(ficha_id=ficha.id, nome=nome, modo=modo))
    sessao.commit()
    sessao.refresh(ficha)
    return [{"vinculo_id": v.id, "nome": v.nome, "modo": v.modo} for v in ficha.resistencias_dano_vinculo]


def criar_efeito(sessao: Session, ficha: banco.Ficha, campos: dict) -> banco.FichaEfeito:
    nome = (campos.get("nome") or "").strip()
    if not nome:
        raise ValueError("Nome do efeito é obrigatório.")
    tipo = campos.get("tipo") or banco.TIPOS_EFEITO[0]
    if tipo not in banco.TIPOS_EFEITO:
        raise ValueError(f"Tipo de efeito desconhecido: {tipo}")
    efeito = banco.FichaEfeito(
        ficha_id=ficha.id, nome=nome, tipo=tipo,
        origem=(campos.get("origem") or "").strip() or None,
        duracao=(campos.get("duracao") or "").strip() or None,
    )
    sessao.add(efeito)
    sessao.commit()
    sessao.refresh(efeito)
    return efeito


def atualizar_efeito(sessao: Session, vinculo_id: int, campos: dict) -> None:
    efeito = sessao.get(banco.FichaEfeito, vinculo_id)
    if efeito is None:
        raise ValueError("Efeito não encontrado.")
    if "nome" in campos and (campos["nome"] or "").strip():
        efeito.nome = campos["nome"].strip()
    if "tipo" in campos:
        if campos["tipo"] not in banco.TIPOS_EFEITO:
            raise ValueError(f"Tipo de efeito desconhecido: {campos['tipo']}")
        efeito.tipo = campos["tipo"]
    if "origem" in campos:
        efeito.origem = (campos["origem"] or "").strip() or None
    if "duracao" in campos:
        efeito.duracao = (campos["duracao"] or "").strip() or None
    sessao.commit()


def remover_efeito(sessao: Session, vinculo_id: int) -> None:
    efeito = sessao.get(banco.FichaEfeito, vinculo_id)
    if efeito is not None:
        sessao.delete(efeito)
        sessao.commit()


# --------------------------------------------------------------------------
# Diário — lista de entradas (data/título/texto) do Personagem, não da Ficha.
# --------------------------------------------------------------------------

def criar_entrada_diario(sessao: Session, personagem: banco.Personagem, campos: dict) -> banco.PersonagemDiarioEntrada:
    entrada = banco.PersonagemDiarioEntrada(
        personagem_id=personagem.id,
        data=(campos.get("data") or "").strip() or None,
        titulo=(campos.get("titulo") or "").strip() or None,
        texto=(campos.get("texto") or "").strip() or None,
    )
    sessao.add(entrada)
    sessao.commit()
    sessao.refresh(entrada)
    return entrada


def atualizar_entrada_diario(sessao: Session, vinculo_id: int, campos: dict) -> None:
    entrada = sessao.get(banco.PersonagemDiarioEntrada, vinculo_id)
    if entrada is None:
        raise ValueError("Entrada de diário não encontrada.")
    if "data" in campos:
        entrada.data = (campos["data"] or "").strip() or None
    if "titulo" in campos:
        entrada.titulo = (campos["titulo"] or "").strip() or None
    if "texto" in campos:
        entrada.texto = (campos["texto"] or "").strip() or None
    sessao.commit()


def remover_entrada_diario(sessao: Session, vinculo_id: int) -> None:
    entrada = sessao.get(banco.PersonagemDiarioEntrada, vinculo_id)
    if entrada is not None:
        sessao.delete(entrada)
        sessao.commit()


# --------------------------------------------------------------------------
# Foto — uma por Personagem, compartilhada entre Base e variantes.
# --------------------------------------------------------------------------

def _pasta_fotos_personagens(root: Path) -> Path:
    return root / "docs" / "assets" / "imagens" / "personagens-ficha"


def salvar_foto_personagem(root: Path, sessao: Session, personagem: banco.Personagem, nome_original: str, conteudo: bytes) -> str:
    """Salva a foto em docs/ (fonte, sobrevive a um `mkdocs build`) e também em site/ (pra ficar
    visível na hora, sem esperar o próximo build — mesmo raciocínio de nunca disparar build por
    uma edição de ficha). Sobrescreve qualquer foto anterior do mesmo personagem, mesmo que a
    extensão tenha mudado. O nome do arquivo leva o `tipo` porque slugs não são mais únicos
    globalmente (um NPC e um monstro podem ter o mesmo slug)."""
    from werkzeug.utils import secure_filename

    sufixo = Path(secure_filename(nome_original) or "").suffix.lower()
    if sufixo not in EXTENSOES_FOTO_PERMITIDAS:
        raise ValueError(f"Tipo de arquivo não permitido: {sufixo or '(sem extensão)'}")

    nome_base = f"{personagem.tipo}-{personagem.slug}"
    nome_arquivo = f"{nome_base}{sufixo}"
    for base_dir in (root / "docs", root / "site"):
        pasta = base_dir / "assets" / "imagens" / "personagens-ficha"
        pasta.mkdir(parents=True, exist_ok=True)
        for antigo in pasta.glob(f"{nome_base}.*"):
            antigo.unlink()
        (pasta / nome_arquivo).write_bytes(conteudo)

    personagem.foto = f"/assets/imagens/personagens-ficha/{nome_arquivo}"
    sessao.commit()
    return personagem.foto


def apagar_foto_personagem(root: Path, sessao: Session, personagem: banco.Personagem) -> None:
    nome_base = f"{personagem.tipo}-{personagem.slug}"
    for base_dir in (root / "docs", root / "site"):
        pasta = base_dir / "assets" / "imagens" / "personagens-ficha"
        for antigo in pasta.glob(f"{nome_base}.*"):
            antigo.unlink()
    personagem.foto = None
    sessao.commit()


# --------------------------------------------------------------------------
# Descanso Longo — só pra npc/jogador (monstro no Combat Tracker é sempre uma cópia isolada, não
# precisa "descansar"; ver admin/combate_api.py e o plano "Combat Tracker integrado...").
# --------------------------------------------------------------------------

def descanso_longo(sessao: Session, ficha: banco.Ficha) -> banco.Ficha:
    """PV volta ao máximo, PV temporário zera, todos os espaços de magia zeram o `usado`, os
    dados de vida usados recuperam pela metade (aproximação SRD, arredondando pra baixo —
    simplificação assumida; a regra completa depende de o jogador escolher gastar Dados de Vida),
    e toda Habilidade com contador de uso ("curto" ou "longo") volta ao máximo. Condições NÃO são
    limpas automaticamente — o Mestre remove manualmente as que devem acabar."""
    ficha.pv_atual = ficha.pv_maximo
    ficha.pv_temporario = 0
    for espaco in ficha.espacos_magia_vinculo:
        espaco.usado = 0
    total_dados = _para_numero((ficha.dados_vida_total or "").split("d")[0], 0)
    recuperados = max(1, total_dados // 2) if total_dados else 0
    ficha.dados_vida_usados = max(0, ficha.dados_vida_usados - recuperados)
    for vinculo in ficha.habilidades_vinculo:
        if vinculo.tipo_descanso in banco.TIPOS_DESCANSO:
            vinculo.usos_restantes = vinculo.usos_maximo
    sessao.commit()
    sessao.refresh(ficha)
    return ficha


def descanso_curto(sessao: Session, ficha: banco.Ficha) -> banco.Ficha:
    """Repõe só as Habilidades de descanso "curto" — não toca PV, espaços de magia nem dados de
    vida (isso é só o descanso_longo)."""
    for vinculo in ficha.habilidades_vinculo:
        if vinculo.tipo_descanso == "curto":
            vinculo.usos_restantes = vinculo.usos_maximo
    sessao.commit()
    sessao.refresh(ficha)
    return ficha


# --------------------------------------------------------------------------
# Motor de nível (Classe/Subclasse/ClasseFeature/FichaClasse) — reabre, a pedido explícito do
# autor (2026-11-04), a decisão anterior de "classe/subclasse são só rótulo livre, sem motor de
# regras" (ver .claude/contexto/personagens.md). Cresce sob demanda: o Mestre cria a Classe/
# Subclasse na hora de usar "Subir de nível" pela primeira vez, sem seed de todas as classes do
# PHB — ver docs/javascripts/ficha.js.
# --------------------------------------------------------------------------

def listar_classes(sessao: Session) -> list[dict]:
    classes = sessao.query(banco.Classe).order_by(banco.Classe.nome).all()
    return [
        {
            "id": c.id, "nome": c.nome, "dado_vida": c.dado_vida,
            "atributo_conjuracao": c.atributo_conjuracao, "progressao_conjuracao": c.progressao_conjuracao,
            "subclasses": [{"id": s.id, "nome": s.nome} for s in sorted(c.subclasses_vinculo, key=lambda s: s.nome)],
        }
        for c in classes
    ]


def criar_classe(sessao: Session, campos: dict) -> dict:
    nome = (campos.get("nome") or "").strip()
    if not nome:
        raise ValueError("Informe o nome da classe.")
    dado_vida = int(_para_numero(campos.get("dado_vida"), 8))
    if dado_vida not in (6, 8, 10, 12):
        raise ValueError("Dado de vida precisa ser 6, 8, 10 ou 12.")
    progressao = (campos.get("progressao_conjuracao") or "").strip() or None
    if progressao is not None and progressao not in banco.PROGRESSOES_CONJURACAO:
        raise ValueError(f"Progressão de conjuração desconhecida: {progressao}")
    classe = banco.Classe(
        nome=nome, dado_vida=dado_vida,
        atributo_conjuracao=(campos.get("atributo_conjuracao") or "").strip() or None,
        progressao_conjuracao=progressao,
    )
    sessao.add(classe)
    sessao.commit()
    sessao.refresh(classe)
    return {"id": classe.id, "nome": classe.nome, "dado_vida": classe.dado_vida, "subclasses": []}


def criar_subclasse(sessao: Session, classe_id: int, nome: str) -> dict:
    classe = sessao.get(banco.Classe, classe_id)
    if classe is None:
        raise ValueError("Classe não encontrada.")
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome da subclasse.")
    subclasse = banco.Subclasse(classe_id=classe_id, nome=nome)
    sessao.add(subclasse)
    sessao.commit()
    sessao.refresh(subclasse)
    return {"id": subclasse.id, "nome": subclasse.nome, "classe_id": classe_id}


def recalcular_espacos_magia(sessao: Session, ficha: banco.Ficha) -> None:
    """Recalcula os máximos de FichaEspacoMagia a partir das classes conjuradoras da ficha — nunca
    toca `usado` além de encaixá-lo dentro do novo máximo. Completo conta o nível inteiro, meio
    conta nível÷2, terço conta nível÷3; a soma consulta TABELA_SLOTS_CONJURADOR_COMPLETO (regra de
    multiclasse padrão do 5e). Bruxo (pacto) é um pool à parte, `rotulo="Pacto"`."""
    nivel_conjurador = 0
    nivel_bruxo = 0
    for fc in ficha.classes_vinculo:
        prog = fc.classe.progressao_conjuracao
        if prog == "completo":
            nivel_conjurador += fc.nivel
        elif prog == "meio":
            nivel_conjurador += fc.nivel // 2
        elif prog == "terco":
            nivel_conjurador += fc.nivel // 3
        elif prog == "pacto":
            nivel_bruxo += fc.nivel

    alvo = dict(banco.TABELA_SLOTS_CONJURADOR_COMPLETO.get(min(nivel_conjurador, 20), {})) if nivel_conjurador > 0 else {}
    pools_normais = {e.nivel: e for e in ficha.espacos_magia_vinculo if e.rotulo != "Pacto"}
    for nivel_magia, maximo in alvo.items():
        pool = pools_normais.get(nivel_magia)
        if pool is None:
            sessao.add(banco.FichaEspacoMagia(ficha_id=ficha.id, nivel=nivel_magia, maximo=maximo, usado=0))
        else:
            pool.maximo = maximo
            pool.usado = min(pool.usado, maximo)
    for nivel_magia, pool in pools_normais.items():
        if nivel_magia not in alvo:
            sessao.delete(pool)

    if nivel_bruxo > 0:
        qtd, nivel_slot = banco.TABELA_SLOTS_PACTO_BRUXO.get(min(nivel_bruxo, 20), (0, 0))
        pool_pacto = next((e for e in ficha.espacos_magia_vinculo if e.rotulo == "Pacto"), None)
        if pool_pacto is None:
            sessao.add(banco.FichaEspacoMagia(ficha_id=ficha.id, nivel=nivel_slot, maximo=qtd, usado=0, rotulo="Pacto"))
        else:
            pool_pacto.nivel = nivel_slot
            pool_pacto.maximo = qtd
            pool_pacto.usado = min(pool_pacto.usado, qtd)
    sessao.commit()


def subir_de_nivel(
    sessao: Session, ficha: banco.Ficha, classe_id: int, subclasse_id: int | None = None,
    pv_ganho: int | None = None,
) -> banco.Ficha:
    """Sobe 1 nível numa classe da ficha (cria a linha de FichaClasse se for a primeira vez nessa
    classe — multiclasse). Recalcula nível total/bônus de proficiência/espaços de magia e
    desbloqueia as ClasseFeature daquele nível (get-or-create Habilidade + FichaHabilidade).
    `pv_ganho` default é a média do dado de vida (arredondada pra cima, regra SRD) + mod. de
    Constituição; o Mestre pode informar o valor exato se rolou o dado físico."""
    classe = sessao.get(banco.Classe, classe_id)
    if classe is None:
        raise ValueError("Classe não encontrada.")
    subclasse = sessao.get(banco.Subclasse, subclasse_id) if subclasse_id is not None else None
    if subclasse_id is not None and subclasse is None:
        raise ValueError("Subclasse não encontrada.")

    fc = next((x for x in ficha.classes_vinculo if x.classe_id == classe_id), None)
    if fc is None:
        fc = banco.FichaClasse(classe=classe, subclasse=subclasse, nivel=0)
        ficha.classes_vinculo.append(fc)
    fc.nivel += 1
    if subclasse is not None:
        fc.subclasse = subclasse

    if pv_ganho is None:
        media_dado = classe.dado_vida // 2 + 1
        pv_ganho = media_dado + modificador(ficha.constituicao)
    else:
        pv_ganho = int(_para_numero(pv_ganho, 0))
    ficha.pv_maximo = max(1, ficha.pv_maximo + pv_ganho)
    if pv_ganho > 0:
        ficha.pv_atual = min(ficha.pv_atual + pv_ganho, ficha.pv_maximo)

    nivel_total = sum(x.nivel for x in ficha.classes_vinculo)
    ficha.nivel = nivel_total
    ficha.bonus_proficiencia = banco.bonus_proficiencia_por_nivel(nivel_total)

    recalcular_espacos_magia(sessao, ficha)

    novas_features = [
        feat for feat in classe.features_vinculo
        if feat.nivel == fc.nivel and (feat.subclasse_id is None or feat.subclasse_id == fc.subclasse_id)
    ]
    for feat in novas_features:
        habilidade = (
            sessao.query(banco.Habilidade)
            .filter(banco.Habilidade.nome == feat.nome, banco.Habilidade.origem_tipo == "classe")
            .first()
        )
        if habilidade is None:
            habilidade = banco.Habilidade(
                nome=feat.nome, tipo="traco", descricao=feat.descricao, origem_tipo="classe",
            )
            sessao.add(habilidade)
            sessao.commit()
            sessao.refresh(habilidade)
        ja_tem = any(v.habilidade_id == habilidade.id for v in ficha.habilidades_vinculo)
        if not ja_tem:
            sessao.add(banco.FichaHabilidade(ficha_id=ficha.id, habilidade_id=habilidade.id))

    ordenadas = sorted(ficha.classes_vinculo, key=lambda x: -x.nivel)
    ficha.classe = " / ".join(f"{x.classe.nome} {x.nivel}" for x in ordenadas)
    subclasses_nomes = [x.subclasse.nome for x in ordenadas if x.subclasse_id]
    ficha.subclasse = " / ".join(subclasses_nomes) if subclasses_nomes else None

    sessao.commit()
    sessao.refresh(ficha)
    return ficha


def buscar_personagens(sessao: Session, tipo: str | None = None, busca: str = "") -> list[dict]:
    """Busca por nome, pra alimentar o seletor "+ adicionar participante" do Combat Tracker
    (admin/combate_api.py) — mesmo espírito de listar_catalogo, mas sobre Personagem/Ficha."""
    consulta = sessao.query(banco.Personagem).options(selectinload(banco.Personagem.fichas))
    if tipo:
        consulta = consulta.filter(banco.Personagem.tipo == tipo)
    if busca:
        consulta = consulta.filter(banco.Personagem.nome.ilike(f"%{busca}%"))
    resultado = []
    for p in consulta.order_by(banco.Personagem.nome).limit(50).all():
        fichas = sorted(p.fichas, key=lambda f: (0 if f.is_base else 1, f.id))
        resultado.append({
            "tipo": p.tipo, "slug": p.slug, "nome": p.nome, "foto": p.foto,
            "fichas": [
                {"id": f.id, "rotulo": f.rotulo, "is_base": f.is_base, "ca_total": f.ca_total,
                 "pv_maximo": f.pv_maximo, "cr": f.cr, "nivel": f.nivel}
                for f in fichas
            ],
        })
    return resultado


def listar_personagens_resumo(sessao: Session, tipo: str | None = None) -> dict[str, dict]:
    """Slug -> resumo da ficha Base de cada personagem — usado em hooks/gallancourt.py (build-time)
    pra montar os catálogos/tabelas sem precisar reler nenhum Markdown. `tipo=None` devolve todos;
    passe "monstro"/"npc"/"jogador" pra filtrar."""
    resultado = {}
    consulta = sessao.query(banco.Personagem).options(selectinload(banco.Personagem.fichas))
    if tipo is not None:
        consulta = consulta.filter(banco.Personagem.tipo == tipo)
    for p in consulta.all():
        base = next((f for f in p.fichas if f.is_base), None)
        resultado[p.slug] = {
            "nome": p.nome, "tamanho": p.tamanho, "tipo_criatura": p.tipo_criatura,
            "alinhamento": p.alinhamento,
            "cr": base.cr if base else None,
            "nivel": base.nivel if base else None,
            "classe": base.classe if base else None,
            "ca": base.ca_total if base else None,
            "pv": base.pv_maximo if base else None,
        }
    return resultado
