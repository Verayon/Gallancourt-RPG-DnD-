"""Testes da ficha de personagem no banco (admin/personagens_api.py) — ver
.claude/contexto/personagens.md. Mesmo padrão de test_banco.py: cada teste usa um SQLite
temporário próprio (`tmp_path`).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "admin"))

import banco  # noqa: E402
import personagens_api as pa  # noqa: E402


def _sessao_de_teste(tmp_path):
    engine = banco.criar_engine(tmp_path)
    banco.Base.metadata.create_all(engine)
    return banco.fabrica_sessao(engine)()


def _goblin_base(sessao):
    personagem = pa.criar_personagem(sessao, "monstro", "goblin", "Goblin", "Pequeno", "Humanoide (goblinoide)", "Neutro e maligno")
    ficha = banco.Ficha(
        personagem_id=personagem.id, rotulo="Base", is_base=True, cr="1/4",
        forca=8, destreza=14, constituicao=10, inteligencia=10, sabedoria=8, carisma=8,
        ca_total=15, pv_formula="2d6", pv_maximo=7, pv_atual=7, deslocamento_m=9.0,
    )
    sessao.add(ficha)
    sessao.commit()
    sessao.refresh(ficha)
    return personagem, ficha


def _jogador_base(sessao):
    personagem = pa.criar_personagem(sessao, "jogador", "aldric", "Aldric Thorne", "Médio", "Humano")
    ficha = banco.Ficha(
        personagem_id=personagem.id, rotulo="Base", is_base=True, nivel=3, classe="Guerreiro",
        forca=14, destreza=13, constituicao=15, inteligencia=10, sabedoria=12, carisma=8,
        ca_total=17, pv_formula="3d10", pv_maximo=28, pv_atual=28, deslocamento_m=9.0,
    )
    sessao.add(ficha)
    sessao.commit()
    sessao.refresh(ficha)
    return personagem, ficha


def test_modificador_segue_a_regra_padrao_de_d20():
    assert pa.modificador(20) == 5
    assert pa.modificador(10) == 0
    assert pa.modificador(9) == -1
    assert pa.modificador(8) == -1


def test_serializar_ficha_inclui_modificador_calculado(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, ficha = _goblin_base(sessao)

        dados = pa.serializar_ficha(ficha)

        assert dados["atributos"]["des"] == {"valor": 14, "modificador": "+2"}
        assert dados["atributos"]["for"] == {"valor": 8, "modificador": "-1"}


def test_criar_variante_copia_atributos_e_vinculos(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        personagem, base = _goblin_base(sessao)
        escudo = pa.criar_item_catalogo(sessao, "equipamentos", {"nome": "Escudo", "ca_bonus": 2})
        pa.adicionar_vinculo(sessao, base, "equipamentos", escudo["id"])

        variante = pa.criar_variante(sessao, personagem, "Arqueiro")

        assert variante.forca == base.forca
        assert variante.id != base.id
        assert [v.equipamento.nome for v in variante.equipamentos_vinculo] == ["Escudo"]


def test_editar_variante_nao_afeta_a_base(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        personagem, base = _goblin_base(sessao)
        variante = pa.criar_variante(sessao, personagem, "Arqueiro")

        pa.atualizar_ficha(sessao, variante, {"ca_total": 13, "forca": 9})

        assert variante.ca_total == 13
        assert base.ca_total == 15  # a base não muda


def test_base_nao_pode_ser_excluida(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)

        try:
            pa.excluir_ficha(sessao, base)
            assert False, "deveria ter recusado excluir a ficha Base"
        except ValueError:
            pass


def test_excluir_variante_funciona(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        personagem, _base = _goblin_base(sessao)
        variante = pa.criar_variante(sessao, personagem, "Arqueiro")

        pa.excluir_ficha(sessao, variante)

        recarregado = pa.obter_personagem(sessao, "monstro", "goblin")
        assert [f.rotulo for f in recarregado.fichas] == ["Base"]


def test_listar_catalogo_filtra_por_busca(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        pa.criar_item_catalogo(sessao, "equipamentos", {"nome": "Escudo"})
        pa.criar_item_catalogo(sessao, "equipamentos", {"nome": "Cimitarra"})

        resultado = pa.listar_catalogo(sessao, "equipamentos", busca="escu")

        assert [i["nome"] for i in resultado] == ["Escudo"]


def test_atributo_e_ca_nao_aceitam_negativo_nem_zero_onde_nao_faz_sentido(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)

        pa.atualizar_ficha(sessao, base, {"forca": -5, "ca_total": -3, "pv_maximo": 0, "deslocamento_m": -1})

        assert base.forca == 1  # mínimo de atributo
        assert base.ca_total == 0  # CA não pode ser negativa, mas pode ser 0
        assert base.pv_maximo == 1  # nunca menos que 1
        assert base.deslocamento_m == 0.0


def test_sentido_guarda_valor_numerico_proprio_por_ficha(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)
        visao = pa.criar_item_catalogo(sessao, "sentidos", {"nome": "Visão no escuro"})

        vinculo = pa.adicionar_vinculo(sessao, base, "sentidos", visao["id"], {"valor": "9"})
        pa.atualizar_valor_sentido(sessao, vinculo["vinculo_id"], "18")

        ficha = pa.serializar_ficha(pa.obter_ficha(sessao, base.id))
        sentido = next(s for s in ficha["sentidos"] if s["vinculo_id"] == vinculo["vinculo_id"])
        assert sentido == {"vinculo_id": vinculo["vinculo_id"], "valor": 18.0, "nome": "Visão no escuro", "id": visao["id"]}


def test_sentido_nao_aceita_valor_negativo(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)
        visao = pa.criar_item_catalogo(sessao, "sentidos", {"nome": "Visão no escuro"})
        vinculo = pa.adicionar_vinculo(sessao, base, "sentidos", visao["id"], {"valor": "-5"})
        pa.atualizar_valor_sentido(sessao, vinculo["vinculo_id"], "-1")

        ficha = pa.serializar_ficha(pa.obter_ficha(sessao, base.id))
        assert ficha["sentidos"][0]["valor"] == 0.0


def test_percepcao_passiva_e_coluna_propria_da_ficha(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)
        assert pa.serializar_ficha(base)["percepcao_passiva"] == 10  # padrão

        pa.atualizar_ficha(sessao, base, {"percepcao_passiva": 13})

        assert pa.serializar_ficha(base)["percepcao_passiva"] == 13


def test_pericia_guarda_bonus_proprio_e_aceita_negativo(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)
        furtividade = pa.criar_item_catalogo(sessao, "pericias", {"nome": "Furtividade", "atributo": "Destreza"})

        vinculo = pa.adicionar_vinculo(sessao, base, "pericias", furtividade["id"], {"bonus": "6"})
        pa.atualizar_bonus_pericia(sessao, vinculo["vinculo_id"], "-1")  # bônus pode ser negativo

        ficha = pa.serializar_ficha(pa.obter_ficha(sessao, base.id))
        assert ficha["pericias"] == [
            {"vinculo_id": vinculo["vinculo_id"], "bonus": -1, "nome": "Furtividade", "atributo": "Destreza",
             "fonte": None, "slug_origem": None, "id": furtividade["id"]}
        ]


def test_criar_variante_copia_pericias_e_percepcao_passiva(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        personagem, base = _goblin_base(sessao)
        pa.atualizar_ficha(sessao, base, {"percepcao_passiva": 9})
        furtividade = pa.criar_item_catalogo(sessao, "pericias", {"nome": "Furtividade"})
        pa.adicionar_vinculo(sessao, base, "pericias", furtividade["id"], {"bonus": "6"})

        variante = pa.criar_variante(sessao, personagem, "Arqueiro")

        assert variante.percepcao_passiva == 9
        assert [v.bonus for v in variante.pericias_vinculo] == [6]


def test_remover_vinculo(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)
        item = pa.criar_item_catalogo(sessao, "equipamentos", {"nome": "Escudo", "ca_bonus": 2})
        vinculo = pa.adicionar_vinculo(sessao, base, "equipamentos", item["id"])

        pa.remover_vinculo(sessao, "equipamentos", vinculo["vinculo_id"])

        ficha_recarregada = pa.obter_ficha(sessao, base.id)
        assert ficha_recarregada.equipamentos_vinculo == []


# --------------------------------------------------------------------------
# Tipos de ator (monstro/npc/jogador) e campos exclusivos de npc/jogador
# --------------------------------------------------------------------------

def test_tipo_invalido_e_recusado(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        try:
            pa.criar_personagem(sessao, "vilao", "alguem", "Alguém")
            assert False, "deveria ter recusado um tipo desconhecido"
        except ValueError:
            pass


def test_mesmo_slug_em_tipos_diferentes_nao_colide(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        pa.criar_personagem(sessao, "monstro", "thalin", "Thalin (monstro de teste)")
        pa.criar_personagem(sessao, "npc", "thalin", "Thalin")

        assert pa.obter_personagem(sessao, "monstro", "thalin") is not None
        assert pa.obter_personagem(sessao, "npc", "thalin") is not None


def test_jogador_usa_nivel_classe_em_vez_de_cr(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _jogador_base(sessao)

        dados = pa.serializar_ficha(base)

        assert dados["nivel"] == 3
        assert dados["classe"] == "Guerreiro"
        assert dados["cr"] is None


# --------------------------------------------------------------------------
# Biografia e Diário — ficam no Personagem, não na Ficha
# --------------------------------------------------------------------------

def test_biografia_fica_no_personagem_nao_na_ficha(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        personagem, _base = _jogador_base(sessao)

        pa.atualizar_personagem(sessao, personagem, {"personalidade": "Fala pouco antes de agir.", "idade": "29"})

        dados = pa.serializar_personagem(personagem)
        assert dados["personalidade"] == "Fala pouco antes de agir."
        assert dados["idade"] == "29"


def test_entrada_de_diario_pode_ser_criada_e_removida(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        personagem, _base = _jogador_base(sessao)

        entrada = pa.criar_entrada_diario(sessao, personagem, {"data": "28/10", "titulo": "Sessão 0", "texto": "Chegamos sob chuva."})
        dados = pa.serializar_personagem(personagem)
        assert dados["diario"] == [{"id": entrada.id, "data": "28/10", "titulo": "Sessão 0", "texto": "Chegamos sob chuva."}]

        pa.remover_entrada_diario(sessao, entrada.id)
        dados = pa.serializar_personagem(personagem)
        assert dados["diario"] == []


# --------------------------------------------------------------------------
# Espaços de magia, Condições, Efeitos — próprios da ficha, não catálogos
# --------------------------------------------------------------------------

def test_espaco_de_magia_guarda_pools_por_nivel_e_rotulo(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _jogador_base(sessao)

        pa.criar_espaco_magia(sessao, base, {"nivel": 2, "maximo": 4, "usado": 2, "rotulo": "Magia de Pacto"})
        pa.atualizar_espaco_magia(sessao, base.espacos_magia_vinculo[0].id, {"usado": 3})

        dados = pa.serializar_ficha(base)
        assert dados["espacos_magia"][0]["usado"] == 3
        assert dados["espacos_magia"][0]["rotulo"] == "Magia de Pacto"


def test_condicao_desconhecida_e_recusada(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)
        try:
            pa.adicionar_condicao(sessao, base, "Transformado em sapo")
            assert False, "deveria ter recusado uma condição fora da lista fixa"
        except ValueError:
            pass


def test_condicao_pode_ser_ligada_e_desligada(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)

        condicao = pa.adicionar_condicao(sessao, base, "Envenenado")
        assert pa.serializar_ficha(base)["condicoes"] == [{"vinculo_id": condicao.id, "nome": "Envenenado"}]

        pa.remover_condicao(sessao, condicao.id)
        assert pa.serializar_ficha(base)["condicoes"] == []


def test_efeito_tipo_invalido_e_recusado(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)
        try:
            pa.criar_efeito(sessao, base, {"nome": "Abençoado", "tipo": "Eterno"})
            assert False, "deveria ter recusado um tipo de efeito fora de TIPOS_EFEITO"
        except ValueError:
            pass


def test_efeito_guarda_origem_e_duracao(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)

        efeito = pa.criar_efeito(sessao, base, {"nome": "Abençoado", "tipo": "Temporário", "origem": "Bênção", "duracao": "1 min."})
        pa.atualizar_efeito(sessao, efeito.id, {"duracao": "expirado"})

        dados = pa.serializar_ficha(base)
        assert dados["efeitos"] == [{"vinculo_id": efeito.id, "nome": "Abençoado", "tipo": "Temporário", "origem": "Bênção", "duracao": "expirado"}]


def test_resistencia_dano_tipo_desconhecido_e_recusado(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)
        try:
            pa.alternar_resistencia_dano(sessao, base, "Dano de verdade", "imune")
            assert False, "deveria ter recusado um tipo de dano fora de TIPOS_DANO"
        except ValueError:
            pass


def test_resistencia_dano_alterna_entre_modos_e_remove(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)

        pa.alternar_resistencia_dano(sessao, base, "Fogo", "resistente")
        assert [r["modo"] for r in pa.serializar_ficha(base)["resistencias_dano"] if r["nome"] == "Fogo"] == ["resistente"]

        # clicar num modo diferente troca, não duplica
        pa.alternar_resistencia_dano(sessao, base, "Fogo", "imune")
        resistencias = pa.serializar_ficha(base)["resistencias_dano"]
        assert [r["modo"] for r in resistencias if r["nome"] == "Fogo"] == ["imune"]
        assert len(resistencias) == 1

        # clicar no mesmo modo de novo remove
        pa.alternar_resistencia_dano(sessao, base, "Fogo", "imune")
        assert pa.serializar_ficha(base)["resistencias_dano"] == []


def test_favoritar_habilidade_e_magia_ordena_primeiro(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)
        mordida = pa.criar_item_catalogo(sessao, "habilidades", {"nome": "Mordida", "tipo": "acao"})
        garra = pa.criar_item_catalogo(sessao, "habilidades", {"nome": "Garra", "tipo": "acao"})
        v_mordida = pa.adicionar_vinculo(sessao, base, "habilidades", mordida["id"])
        v_garra = pa.adicionar_vinculo(sessao, base, "habilidades", garra["id"])

        pa.alternar_favorito_vinculo(sessao, "habilidades", v_garra["vinculo_id"])

        nomes = [h["nome"] for h in pa.serializar_ficha(base)["habilidades"]]
        assert nomes == ["Garra", "Mordida"]  # favorito primeiro

        favorito = pa.alternar_favorito_vinculo(sessao, "habilidades", v_garra["vinculo_id"])
        assert favorito is False  # alternar de novo desfavorita
        assert v_mordida  # sanity: o outro vínculo não foi tocado


def test_consumir_uso_habilidade_ate_zerar(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _goblin_base(sessao)
        sopro = pa.criar_item_catalogo(sessao, "habilidades", {"nome": "Sopro de fogo", "tipo": "acao"})
        vinculo = pa.adicionar_vinculo(sessao, base, "habilidades", sopro["id"])

        pa.definir_usos_habilidade(sessao, vinculo["vinculo_id"], {"usos_maximo": 2, "tipo_descanso": "curto"})
        assert pa.consumir_uso_habilidade(sessao, vinculo["vinculo_id"]) == 1
        assert pa.consumir_uso_habilidade(sessao, vinculo["vinculo_id"]) == 0
        assert pa.consumir_uso_habilidade(sessao, vinculo["vinculo_id"]) == 0  # não passa de 0


def test_descanso_curto_so_reseta_contadores_curto(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _jogador_base(sessao)
        acao_curta = pa.criar_item_catalogo(sessao, "habilidades", {"nome": "Segundo Fôlego", "tipo": "acao"})
        acao_longa = pa.criar_item_catalogo(sessao, "habilidades", {"nome": "Ação Surto", "tipo": "acao"})
        v_curta = pa.adicionar_vinculo(sessao, base, "habilidades", acao_curta["id"])
        v_longa = pa.adicionar_vinculo(sessao, base, "habilidades", acao_longa["id"])
        pa.definir_usos_habilidade(sessao, v_curta["vinculo_id"], {"usos_maximo": 1, "tipo_descanso": "curto"})
        pa.definir_usos_habilidade(sessao, v_longa["vinculo_id"], {"usos_maximo": 1, "tipo_descanso": "longo"})
        pa.consumir_uso_habilidade(sessao, v_curta["vinculo_id"])
        pa.consumir_uso_habilidade(sessao, v_longa["vinculo_id"])

        pa.descanso_curto(sessao, base)

        habilidades = {h["nome"]: h["usos_restantes"] for h in pa.serializar_ficha(base)["habilidades"]}
        assert habilidades["Segundo Fôlego"] == 1  # curto repôs
        assert habilidades["Ação Surto"] == 0  # longo não repõe num descanso curto


def test_descanso_longo_reseta_contadores_curto_e_longo_junto_com_pv_e_slots(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _personagem, base = _jogador_base(sessao)
        habilidade = pa.criar_item_catalogo(sessao, "habilidades", {"nome": "Ação Surto", "tipo": "acao"})
        vinculo = pa.adicionar_vinculo(sessao, base, "habilidades", habilidade["id"])
        pa.definir_usos_habilidade(sessao, vinculo["vinculo_id"], {"usos_maximo": 1, "tipo_descanso": "longo"})
        pa.consumir_uso_habilidade(sessao, vinculo["vinculo_id"])
        pa.criar_espaco_magia(sessao, base, {"nivel": 1, "maximo": 2, "usado": 2})
        base.pv_atual = 1  # pv_atual fica fora de CAMPOS_FICHA_EDITAVEIS de propósito
        sessao.commit()

        pa.descanso_longo(sessao, base)

        dados = pa.serializar_ficha(base)
        assert dados["pv_atual"] == base.pv_maximo
        assert dados["espacos_magia"][0]["usado"] == 0
        assert dados["habilidades"][0]["usos_restantes"] == 1
