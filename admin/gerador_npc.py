"""Gerador de NPCs genéricos: cria um NPC com ficha de combate completa a partir de filtros
(raça, papel, nível de poder) e/ou um prompt em texto livre.

Sem chamada a nenhuma IA ou API externa — só tabelas aleatórias locais (nomes, papéis,
equipamento, estatísticas por nível de poder), ao estilo das tabelas de NPC genérico do DMG.
O prompt não entende linguagem livre: ele só procura, no texto, palavras que batam com uma raça,
um papel ou um nível de potência conhecidos, e usa isso para preencher os filtros deixados em
"Aleatório". É um gerador por tabelas, não um gerador por IA.
"""
from __future__ import annotations

import random
import re
import unicodedata

ALEATORIO = "Aleatório"

RACAS = [
    "Humano", "Elfo", "Anão", "Halfling", "Draconato", "Gnomo", "Meio-Elfo", "Meio-Orc",
    "Tiflin", "Aasimar", "Goliath", "Órc", "Meio-Gigante",
]

NIVEIS_POTENCIA = ["Fraco", "Médio", "Forte"]

# Forma feminina do nome da raça, só para a descrição em prosa ler bem em português (o campo
# `raca` da ficha continua com o nome "oficial", sempre no masculino, como já é o padrão da
# wiki — ver docs/racas/index.md).
RACA_FEMININO = {
    "Humano": "humana", "Elfo": "elfa", "Anão": "anã", "Halfling": "halfling",
    "Draconato": "draconata", "Gnomo": "gnoma", "Meio-Elfo": "meio-elfa", "Meio-Orc": "meio-orc",
    "Tiflin": "tiflin", "Aasimar": "aasimar", "Goliath": "goliath", "Órc": "orca",
    "Meio-Gigante": "meio-gigante",
}

# Nomes de família de Gallancourt (reaproveita as casas e sobrenomes já cadastrados na wiki,
# para os NPCs gerados parecerem nativos da ambientação) + sobrenomes comuns do povo.
SOBRENOMES = [
    "Duvant", "Marceau", "Corbeau", "Lumière", "Roche", "Montaigne", "Vaucluse", "Saint-Pierre",
    "Saint-Laurent", "Clermont", "de la Rivière", "Magnetér", "Montpensier", "Beaumont",
    "du Valois", "Brissac", "Vigny", "Montclair", "Rochefort", "d'Aubren", "Petit", "Lenoir",
    "Dubois", "Fontaine", "Rousseau", "Lefèvre", "Carvalho", "Ferreira",
]

NOMES_POR_RACA = {
    "Humano": ["Pierre", "Jeanne", "Louis", "Camille", "Henri", "Margot", "Étienne", "Odile"],
    "Elfo": ["Faelar", "Sylvaine", "Theriel", "Luinor", "Elowen", "Caelith", "Myrril", "Sariel"],
    "Anão": ["Borin", "Hilda", "Durgan", "Nala", "Thrain", "Vera", "Oskar", "Brunna"],
    "Halfling": ["Pippin", "Rosie", "Milo", "Daisy", "Tobin", "Mara", "Perry", "Lily"],
    "Draconato": ["Arjhan", "Kava", "Rhogar", "Sora", "Balasar", "Nala", "Medrash", "Thava"],
    "Gnomo": ["Fonkin", "Bimpnottin", "Zook", "Ditha", "Wrenn", "Nissa", "Glim", "Pog"],
    "Meio-Elfo": ["Aramil", "Luisa", "Berris", "Nadine", "Vallus", "Elena", "Caelar", "Ninsa"],
    "Meio-Orc": ["Grosh", "Vera", "Thokk", "Nira", "Morg", "Olga", "Krusk", "Baggi"],
    "Tiflin": ["Akmenos", "Lerissa", "Damaia", "Rieta", "Kairon", "Nemeia", "Mordai", "Soneis"],
    "Aasimar": ["Zariel", "Seraphina", "Amaros", "Lumiel", "Thael", "Nuriel", "Caelan", "Ophira"],
    "Goliath": ["Keothi", "Vimak", "Lo-Kag", "Thotham", "Nalla", "Uthak", "Ilikan", "Manneo"],
    "Órc": ["Garn", "Yevelda", "Krag", "Ogolai", "Thurv", "Mhurren", "Shautha", "Vola"],
    "Meio-Gigante": ["Hroth", "Ymara", "Durnak", "Freya", "Orvik", "Signe", "Baldrik", "Thyra"],
}

# Papel/arquétipo: título sugerido, afiliação sugerida, resumo e traço de personalidade.
PAPEIS: dict[str, dict] = {
    "Guarda": {
        "titulo": "Guarda",
        "resumo": "Patrulha as ruas ou protege um portão, mais cumpridor de ordens do que corajoso.",
        "tracos": "Segue ordens sem questionar, mas detesta brutalidade sem necessidade.",
        "equipamento": "Lança, escudo, cota de malha reforçada, apito de sinalização",
    },
    "Bandido": {
        "titulo": "Bandido",
        "resumo": "Vive de assaltos em estradas isoladas, longe da vigilância de qualquer nobre.",
        "tracos": "Acredita que ninguém vai ajudá-lo além de si mesmo.",
        "equipamento": "Cimitarra, besta leve, roupas de couro surradas",
    },
    "Mercador": {
        "titulo": "Mercador",
        "resumo": "Negocia mercadorias entre cidades, sempre calculando o próximo bom negócio.",
        "tracos": "Fala rápido e sorri fácil, mas guarda bem seus reais interesses.",
        "equipamento": "Adaga, balança de pesos, livro de contas, carroça de mercadorias",
    },
    "Nobre": {
        "titulo": "Nobre",
        "resumo": "Membro de uma família aristocrática, acostumado a ser obedecido.",
        "tracos": "Trata gente comum com uma educação que soa condescendente.",
        "equipamento": "Rapieira cerimonial, anel de família, roupas finas",
    },
    "Sacerdote": {
        "titulo": "Sacerdote",
        "resumo": "Serve um templo ou uma capela, cuidando da fé e dos aflitos da região.",
        "tracos": "Oferece conselhos espirituais mesmo quando ninguém pediu.",
        "equipamento": "Clava, símbolo sagrado, vestes de cerimônia, kit de curandeiro",
    },
    "Erudito": {
        "titulo": "Erudito",
        "resumo": "Passa os dias entre pergaminhos e livros, buscando respostas que mais ninguém procura.",
        "tracos": "Corrige os outros sem perceber que isso incomoda.",
        "equipamento": "Bordão, livro, tinteiro e pena, lupa",
    },
    "Marujo": {
        "titulo": "Marujo",
        "resumo": "Passou a vida em navios, conhece as correntes e os portos da costa como poucos.",
        "tracos": "Tem uma história (provavelmente exagerada) para cada cicatriz que carrega.",
        "equipamento": "Cimitarra, corda, gancho de escalada",
    },
    "Taverneiro": {
        "titulo": "Taverneiro",
        "resumo": "Administra uma taverna, ouvindo mais segredos do que gostaria de admitir.",
        "tracos": "Sabe fingir que não ouviu nada, mesmo escutando tudo.",
        "equipamento": "Clava grande (debaixo do balcão), aventais, chaves da adega",
    },
    "Batedor": {
        "titulo": "Batedor",
        "resumo": "Explora território desconhecido a serviço de alguém, confiando mais no instinto do que em mapas.",
        "tracos": "Prefere o silêncio da trilha à conversa de taverna.",
        "equipamento": "Arco curto, adaga, capa de viagem, corda de 15 m",
    },
    "Cavaleiro": {
        "titulo": "Cavaleiro",
        "resumo": "Jurou lealdade a uma casa ou ordem, e honra esse juramento acima de quase tudo.",
        "tracos": "Mede cada decisão pelo código de honra que seguiu a vida toda.",
        "equipamento": "Espada longa, escudo, cota de malha, cavalo de guerra",
    },
    "Artesão": {
        "titulo": "Artesão",
        "resumo": "Domina um ofício manual — ferraria, carpintaria ou tecelagem — e tem orgulho disso.",
        "tracos": "Julga qualquer trabalho malfeito com um olhar reprovador.",
        "equipamento": "Martelo, ferramentas de artesão, roupas de trabalho",
    },
    "Criminoso": {
        "titulo": "Criminoso",
        "resumo": "Vive nas sombras da cidade, entre contrabando, roubo e favores obscuros.",
        "tracos": "Confia em poucos, e mesmo esses só até certo ponto.",
        "equipamento": "Duas adagas, kit de ladrão, disfarce simples",
    },
}

# Estatísticas de combate por nível de potência — baseline simples (não é um monstro oficial;
# serve de referência rápida de mesa, ajuste à vontade na Ficha de combate depois de gerado).
TIERS: dict[str, dict] = {
    "Fraco": {
        "ca": "12", "pv": "9 (2d8)", "deslocamento": "9 m", "cr": "1/8 (25 PE)",
        "for": "11", "des": "12", "con": "11", "int": "10", "sab": "10", "car": "10",
        "acao": "Ataque com arma: +3 para acertar, alcance 1,5 m ou à distância, um alvo. Acerto: 4 (1d6+1) de dano.",
    },
    "Médio": {
        "ca": "14", "pv": "16 (3d8+3)", "deslocamento": "9 m", "cr": "1/2 (100 PE)",
        "for": "13", "des": "13", "con": "12", "int": "10", "sab": "11", "car": "11",
        "acao": "Ataque com arma: +4 para acertar, alcance 1,5 m ou à distância, um alvo. Acerto: 6 (1d8+2) de dano.",
    },
    "Forte": {
        "ca": "16", "pv": "30 (5d10+10)", "deslocamento": "9 m", "cr": "2 (450 PE)",
        "for": "15", "des": "14", "con": "14", "int": "11", "sab": "12", "car": "12",
        "acao": "Ataque com arma: +5 para acertar, alcance 1,5 m ou à distância, um alvo. Acerto: 8 (1d10+3) de dano.",
    },
}


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii").lower()


def _achar_na_lista(texto: str, opcoes: list[str]) -> str | None:
    alvo = _sem_acento(texto)
    for opcao in opcoes:
        chave = _sem_acento(opcao).rstrip("o").rstrip("a")  # casa "órc"/"orc", "guarda"/"guardas"...
        if chave and chave in alvo:
            return opcao
    return None


def sugerir_filtros_do_prompt(prompt: str) -> dict[str, str]:
    """Procura, no texto livre, palavras que batam com uma raça/papel/nível conhecidos."""
    if not prompt:
        return {}
    sugestoes = {}
    raca = _achar_na_lista(prompt, RACAS)
    if raca:
        sugestoes["raca"] = raca
    papel = _achar_na_lista(prompt, list(PAPEIS.keys()))
    if papel:
        sugestoes["papel"] = papel
    nivel = _achar_na_lista(prompt, NIVEIS_POTENCIA)
    if nivel:
        sugestoes["nivel_potencia"] = nivel
    return sugestoes


def gerar_npc(raca: str, papel: str, nivel_potencia: str, prompt: str = "") -> dict:
    """Monta os dados de um NPC genérico: campos para criar_npc() + um dict pronto para
    renderizar_statblock(). Qualquer filtro "Aleatório" (ou vazio) é sorteado — a não ser que o
    prompt sugira um valor para ele, caso em que a sugestão do prompt é usada."""
    sugestoes = sugerir_filtros_do_prompt(prompt)

    def _resolver(valor: str, chave_sugestao: str, opcoes: list[str]) -> str:
        if valor and valor != ALEATORIO:
            return valor
        return sugestoes.get(chave_sugestao) or random.choice(opcoes)

    raca = _resolver(raca, "raca", RACAS)
    papel = _resolver(papel, "papel", list(PAPEIS.keys()))
    nivel_potencia = _resolver(nivel_potencia, "nivel_potencia", NIVEIS_POTENCIA)

    dados_papel = PAPEIS[papel]
    tier = TIERS[nivel_potencia]

    primeiro_nome = random.choice(NOMES_POR_RACA.get(raca, NOMES_POR_RACA["Humano"]))
    sobrenome = random.choice(SOBRENOMES)
    nome = f"{primeiro_nome} {sobrenome}"

    valores_npc = {
        "nome": nome,
        "titulo": dados_papel["titulo"],
        "raca": raca,
        "cidade": "",
        "afiliacao": "",
        "resumo": dados_papel["resumo"],
        "descricao": (
            f"{nome} é {_artigo_e_raca(raca, primeiro_nome)} "
            f"que atua como {dados_papel['titulo'].lower()}. {dados_papel['tracos']}"
        ),
    }

    statblock = {
        "nome": nome,
        "subtitulo": f"{raca}, {dados_papel['titulo'].lower()} ({nivel_potencia.lower()})",
        "cr": tier["cr"],
        "ca": tier["ca"],
        "pv": tier["pv"],
        "deslocamento": tier["deslocamento"],
        "for": tier["for"], "des": tier["des"], "con": tier["con"],
        "int": tier["int"], "sab": tier["sab"], "car": tier["car"],
        "equipamento": dados_papel["equipamento"],
        "tracos": f"Traço de personalidade: {dados_papel['tracos']}",
        "acoes": f"Ataque: {tier['acao']}",
    }

    return {"npc": valores_npc, "statblock": statblock, "filtros_usados": {
        "raca": raca, "papel": papel, "nivel_potencia": nivel_potencia,
    }}


def _eh_masculino(primeiro_nome: str) -> bool:
    """Palpite simples (nada garantido) só para a descrição gerada ler bem em português;
    não afeta nenhum dado mecânico do NPC."""
    return not _sem_acento(primeiro_nome).endswith(("a", "ia", "ina", "ela", "issa"))


def _artigo_e_raca(raca: str, primeiro_nome: str) -> str:
    """'um anão'/'uma anã' — concorda o artigo e o nome da raça com o palpite de gênero do
    primeiro nome sorteado, só para a prosa da descrição ler bem."""
    if _eh_masculino(primeiro_nome):
        return f"um {raca.lower()}"
    return f"uma {RACA_FEMININO.get(raca, raca.lower())}"
