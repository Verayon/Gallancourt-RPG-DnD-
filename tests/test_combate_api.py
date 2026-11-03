"""Testes do Combat Tracker (admin/combate_api.py) — ver o plano "Combat Tracker integrado..."
e .claude/contexto/combate.md. Mesmo padrão de test_banco.py/test_personagens_api.py: cada teste
usa um SQLite temporário próprio (`tmp_path`).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "admin"))

import banco  # noqa: E402
import personagens_api as pa  # noqa: E402
import combate_api as ca  # noqa: E402


def _sessao_de_teste(tmp_path):
    engine = banco.criar_engine(tmp_path)
    banco.Base.metadata.create_all(engine)
    return banco.fabrica_sessao(engine)()


def _ficha_monstro(sessao, slug="goblin", nome="Goblin", pv_maximo=7, ca_total=15, cr="1/4"):
    personagem = pa.criar_personagem(sessao, "monstro", slug, nome)
    ficha = banco.Ficha(
        personagem_id=personagem.id, rotulo="Base", is_base=True, cr=cr,
        pv_maximo=pv_maximo, pv_atual=pv_maximo, ca_total=ca_total,
    )
    sessao.add(ficha)
    sessao.commit()
    sessao.refresh(ficha)
    return personagem, ficha


def _ficha_jogador(sessao, slug="astra", nome="Astraelle", pv_maximo=20, ca_total=16):
    personagem = pa.criar_personagem(sessao, "jogador", slug, nome)
    ficha = banco.Ficha(
        personagem_id=personagem.id, rotulo="Base", is_base=True, xp=0,
        pv_maximo=pv_maximo, pv_atual=pv_maximo, ca_total=ca_total,
    )
    sessao.add(ficha)
    sessao.commit()
    sessao.refresh(ficha)
    return personagem, ficha


def test_monstro_e_copia_isolada_pv_e_condicao_nao_tocam_ficha_real(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _p, ficha = _ficha_monstro(sessao, pv_maximo=7)
        combate = ca.iniciar_combate(sessao, "teste.md")
        participante = ca.adicionar_participante(sessao, combate, ficha.id, "Goblin 1", 10)

        ca.ajustar_pv(sessao, participante.id, 5, cura=False)
        ca.alternar_condicao(sessao, participante.id, "Envenenado")
        sessao.refresh(ficha)

        carregado = ca._carregar_participante(sessao, participante.id)
        assert ca.pv_atual(carregado) == 2
        assert ficha.pv_atual == 7  # nunca escreveu na Ficha real do catálogo
        assert ficha.condicoes_vinculo == []
        assert "Envenenado" in ca.condicoes_ativas(carregado)


def test_duas_copias_do_mesmo_monstro_tem_pv_independente(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _p, ficha = _ficha_monstro(sessao, pv_maximo=7)
        combate = ca.iniciar_combate(sessao, "teste.md")
        p1 = ca.adicionar_participante(sessao, combate, ficha.id, "Goblin 1", 10)
        p2 = ca.adicionar_participante(sessao, combate, ficha.id, "Goblin 2", 8)

        ca.ajustar_pv(sessao, p1.id, 7, cura=False)

        assert ca.pv_atual(ca._carregar_participante(sessao, p1.id)) == 0
        assert ca.pv_atual(ca._carregar_participante(sessao, p2.id)) == 7


def test_npc_e_jogador_leem_e_escrevem_direto_na_ficha_real(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _p, ficha = _ficha_jogador(sessao, pv_maximo=20)
        combate = ca.iniciar_combate(sessao, "teste.md")
        participante = ca.adicionar_participante(sessao, combate, ficha.id, None, 15)

        ca.ajustar_pv(sessao, participante.id, 6, cura=False)
        ca.alternar_condicao(sessao, participante.id, "Envenenado")
        sessao.refresh(ficha)

        assert ficha.pv_atual == 14
        assert [c.nome for c in ficha.condicoes_vinculo] == ["Envenenado"]

        ca.alternar_condicao(sessao, participante.id, "Envenenado")
        sessao.refresh(ficha)
        assert ficha.condicoes_vinculo == []


def test_dano_consome_pv_temporario_primeiro(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _p, ficha = _ficha_jogador(sessao, pv_maximo=20)
        combate = ca.iniciar_combate(sessao, "teste.md")
        participante = ca.adicionar_participante(sessao, combate, ficha.id, None, 10)
        ca.definir_pv_temporario(sessao, participante.id, 5)

        resultado = ca.ajustar_pv(sessao, participante.id, 8, cura=False)

        assert resultado == {"pv_atual": 17, "pv_temporario": 0}


def test_cura_respeita_pv_maximo(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _p, ficha = _ficha_jogador(sessao, pv_maximo=20)
        ficha.pv_atual = 18
        sessao.commit()
        combate = ca.iniciar_combate(sessao, "teste.md")
        participante = ca.adicionar_participante(sessao, combate, ficha.id, None, 10)

        resultado = ca.ajustar_pv(sessao, participante.id, 10, cura=True)

        assert resultado["pv_atual"] == 20


def test_pv_zero_aplica_caido_e_voltar_remove(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _p, ficha = _ficha_jogador(sessao, pv_maximo=10)
        combate = ca.iniciar_combate(sessao, "teste.md")
        participante = ca.adicionar_participante(sessao, combate, ficha.id, None, 10)

        ca.ajustar_pv(sessao, participante.id, 10, cura=False)
        carregado = ca._carregar_participante(sessao, participante.id)
        assert "Caído" in ca.condicoes_ativas(carregado)

        ca.ajustar_pv(sessao, participante.id, 10, cura=True)
        carregado = ca._carregar_participante(sessao, participante.id)
        assert "Caído" not in ca.condicoes_ativas(carregado)


def test_ordenacao_por_iniciativa_e_desempate(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _pm, fm = _ficha_monstro(sessao)
        _pj, fj = _ficha_jogador(sessao)
        combate = ca.iniciar_combate(sessao, "teste.md")
        p_monstro = ca.adicionar_participante(sessao, combate, fm.id, None, 10)
        p_jogador = ca.adicionar_participante(sessao, combate, fj.id, None, 10)
        ca.atualizar_iniciativa(sessao, p_monstro.id, desempate=5)

        combate = ca.obter_combate(sessao, combate.id)
        estado = ca.serializar_combate(combate)
        nomes = [p["nome"] for p in estado["participantes"]]

        assert nomes[0] == "Goblin"  # mesma iniciativa base, mas desempate maior vem primeiro
        assert nomes[1] == "Astraelle"
        _ = p_jogador


def test_proximo_turno_avanca_rodada_e_reseta_economia_de_acao(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _pm, fm = _ficha_monstro(sessao)
        _pj, fj = _ficha_jogador(sessao)
        combate = ca.iniciar_combate(sessao, "teste.md")
        p1 = ca.adicionar_participante(sessao, combate, fj.id, None, 20)
        p2 = ca.adicionar_participante(sessao, combate, fm.id, None, 5)

        ca.alternar_economia_acao(sessao, p1.id, "acao_usada")
        ca.proximo_turno(sessao, combate)  # None -> p1 (maior iniciativa)
        combate = ca.obter_combate(sessao, combate.id)
        assert combate.turno_participante_id == p1.id
        assert combate.rodada == 1

        ca.proximo_turno(sessao, combate)  # p1 -> p2
        combate = ca.obter_combate(sessao, combate.id)
        assert combate.turno_participante_id == p2.id
        assert combate.rodada == 1

        ca.proximo_turno(sessao, combate)  # p2 -> volta pra p1, nova rodada
        combate = ca.obter_combate(sessao, combate.id)
        assert combate.turno_participante_id == p1.id
        assert combate.rodada == 2
        p1_recarregado = ca._carregar_participante(sessao, p1.id)
        assert p1_recarregado.acao_usada is False  # resetou ao chegar o turno dele de novo


def test_concentracao_falha_remove_o_rotulo(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _p, ficha = _ficha_jogador(sessao)
        combate = ca.iniciar_combate(sessao, "teste.md")
        participante = ca.adicionar_participante(sessao, combate, ficha.id, None, 10)
        ca.definir_concentracao(sessao, participante.id, "Enfeitiçar Pessoas")

        resultado = ca.checar_concentracao(sessao, participante.id, d20_bruto=5, bonus=0, dano_sofrido=20)

        assert resultado == {"cd": 10, "total": 5, "sucesso": False}
        atualizado = sessao.get(banco.CombateParticipante, participante.id)
        assert atualizado.concentrando_em is None


def test_teste_de_morte_nat1_nat20_e_tres_falhas(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _p, ficha = _ficha_jogador(sessao, pv_maximo=10)
        combate = ca.iniciar_combate(sessao, "teste.md")
        participante = ca.adicionar_participante(sessao, combate, ficha.id, None, 10)
        ca.ajustar_pv(sessao, participante.id, 10, cura=False)  # cai a 0

        r1 = ca.rolar_teste_morte(sessao, participante.id, 1)
        assert r1["efeito"] == "duas_falhas"
        atualizado = sessao.get(banco.CombateParticipante, participante.id)
        assert atualizado.death_save_falhas == 2

        r2 = ca.rolar_teste_morte(sessao, participante.id, 9)
        assert r2["efeito"] == "falha"
        assert r2["morto"] is True

        r3 = ca.rolar_teste_morte(sessao, participante.id, 20)
        sessao.refresh(ficha)
        assert r3["efeito"] == "levanta_com_1_pv"
        assert ficha.pv_atual == 1


def test_xp_so_soma_monstros_mortos_e_divide_por_jogadores_vivos(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _pm, fm = _ficha_monstro(sessao, pv_maximo=7, cr="1/4")  # 50 XP
        _pj1, fj1 = _ficha_jogador(sessao, slug="astra")
        _pj2, fj2 = _ficha_jogador(sessao, slug="rowan")
        combate = ca.iniciar_combate(sessao, "teste.md")
        p_monstro = ca.adicionar_participante(sessao, combate, fm.id, None, 5)
        ca.adicionar_participante(sessao, combate, fj1.id, None, 20)
        ca.adicionar_participante(sessao, combate, fj2.id, None, 15)
        ca.ajustar_pv(sessao, p_monstro.id, 100, cura=False)

        combate = ca.obter_combate(sessao, combate.id)
        resumo = ca.calcular_resumo_xp(combate)

        assert resumo["xp_total"] == 50
        assert resumo["xp_por_jogador"] == 25

        ca.distribuir_xp(sessao, combate, resumo["xp_por_jogador"])
        sessao.refresh(fj1)
        sessao.refresh(fj2)
        assert fj1.xp == 25
        assert fj2.xp == 25


def test_loot_dividido_e_individual(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _pm, fm = _ficha_monstro(sessao)
        fm.moeda_pc = 5
        equipamento = banco.Equipamento(nome="Cimitarra")
        sessao.add(equipamento)
        sessao.flush()
        sessao.add(banco.FichaEquipamento(ficha_id=fm.id, equipamento_id=equipamento.id, quantidade=1))
        sessao.commit()

        _pj1, fj1 = _ficha_jogador(sessao, slug="astra")
        _pj2, fj2 = _ficha_jogador(sessao, slug="rowan")
        combate = ca.iniciar_combate(sessao, "teste.md")
        p_monstro = ca.adicionar_participante(sessao, combate, fm.id, None, 5)
        ca.adicionar_participante(sessao, combate, fj1.id, None, 20)
        ca.adicionar_participante(sessao, combate, fj2.id, None, 15)
        ca.ajustar_pv(sessao, p_monstro.id, 100, cura=False)

        combate = ca.obter_combate(sessao, combate.id)
        loot = ca.compilar_loot(combate)
        assert loot["moedas"]["moeda_pc"] == 5
        assert loot["itens"] == [{"nome": "Cimitarra", "quantidade": 1, "equipamento_id": equipamento.id}]

        ca.aplicar_loot(sessao, combate, [
            {"tipo": "moeda", "campo_moeda": "moeda_pc", "quantidade": 5, "modo": "dividir"},
            {"tipo": "item", "equipamento_id": equipamento.id, "quantidade": 1, "modo": "individual", "ficha_id": fj1.id},
        ])
        sessao.refresh(fj1)
        sessao.refresh(fj2)
        assert fj1.moeda_pc == 3  # resto da divisão fica com o primeiro
        assert fj2.moeda_pc == 2
        assert [v.equipamento.nome for v in fj1.equipamentos_vinculo] == ["Cimitarra"]
        assert fj2.equipamentos_vinculo == []


def test_descanso_longo_restaura_pv_e_espacos_de_magia(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _p, ficha = _ficha_jogador(sessao, pv_maximo=20)
        ficha.pv_atual = 3
        ficha.pv_temporario = 4
        ficha.dados_vida_total = "3d10"
        ficha.dados_vida_usados = 3
        sessao.add(banco.FichaEspacoMagia(ficha_id=ficha.id, nivel=1, maximo=4, usado=3))
        sessao.commit()

        pa.descanso_longo(sessao, ficha)
        sessao.refresh(ficha)

        assert ficha.pv_atual == 20
        assert ficha.pv_temporario == 0
        assert ficha.espacos_magia_vinculo[0].usado == 0
        assert ficha.dados_vida_usados == 2  # recupera metade de 3 (arredondado pra baixo), mínimo 1


def test_iniciativa_desempate_automatico_pelo_modificador_de_destreza(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _pm, fm = _ficha_monstro(sessao)
        fm.destreza = 16  # mod. +3
        sessao.commit()
        combate = ca.iniciar_combate(sessao, "teste.md")

        participante = ca.adicionar_participante(sessao, combate, fm.id, None, 10)

        assert participante.iniciativa_desempate == 3


def test_evasao_zera_dano_na_resistencia_em_area(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _pj, fj = _ficha_jogador(sessao, pv_maximo=20)
        evasao = pa.criar_item_catalogo(sessao, "habilidades", {"nome": "Evasão", "tipo": "traco"})
        pa.adicionar_vinculo(sessao, fj, "habilidades", evasao["id"])
        combate = ca.iniciar_combate(sessao, "teste.md")
        participante = ca.adicionar_participante(sessao, combate, fj.id, None, 10)

        resultados = ca.resolver_resistencia(
            sessao, cd=15, meio_no_sucesso=True, condicao_no_erro=None,
            alvos=[{"participante_id": participante.id, "d20_bruto": 18, "dano": 20}],
        )

        assert resultados[0]["sucesso"] is True
        assert resultados[0]["dano_aplicado"] == 0  # Evasão zera, não só reduz à metade
        sessao.refresh(fj)
        assert fj.pv_atual == 20


def test_compilar_loot_inclui_moeda_extra_automatica_por_cr_medio(tmp_path):
    with _sessao_de_teste(tmp_path) as sessao:
        _pm, fm = _ficha_monstro(sessao, cr="1/4")  # cai na faixa de CR médio <= 4
        combate = ca.iniciar_combate(sessao, "teste.md")
        p_monstro = ca.adicionar_participante(sessao, combate, fm.id, None, 5)
        ca.ajustar_pv(sessao, p_monstro.id, 100, cura=False)

        combate = ca.obter_combate(sessao, combate.id)
        loot = ca.compilar_loot(combate)

        # faixa de CR <= 4 (ver _rolar_moeda_por_cr_medio): pp entre 5 e 15, po entre 0 e 10
        assert 5 <= loot["moedas"]["moeda_pp"] <= 15
        assert 0 <= loot["moedas"]["moeda_po"] <= 10
