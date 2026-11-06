"""Banco de dados relacional (SQLite) — fundação para dados operacionais que precisam de consulta
de verdade, ao contrário do Markdown/YAML (que continuam sendo a fonte do lore e dos registros já
em produção: linha do tempo, Changelog, Roadmap — ver ARQUITETURA.md). Desde 2026-10-31, é também
a fonte única da ficha de combate de monstros, NPCs nomeados e jogadores (ver `Personagem`/`Ficha`
abaixo) — NPCs genéricos, figurantes de sessão e a ficha de cidade continuam em Markdown de
propósito, ver `.claude/contexto/personagens.md`.

Isolado do Flask de propósito, como wiki_data.py/sessao_viva.py: toda função que precisa do banco
recebe uma `Session` já aberta (não abre/fecha conexão sozinha), e `criar_engine` recebe `root`
para permitir apontar para uma cópia de teste em vez do banco real do autor.
"""
from __future__ import annotations

import datetime
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


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
    """Também serve de registro de quais livros já alimentaram os catálogos (ver scripts/
    importar_*.py, 2026-11-05): `importado_em`/`arquivo_origem` ficam `None` até um importador
    rodar com sucesso sobre o `.md` convertido dessa fonte — ex. Guia de Xanathar fica assim de
    propósito, por ora, até o markdown convertido dele (corrompido pelo OCR) ser limpo."""
    __tablename__ = "fontes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    abreviacao: Mapped[str] = mapped_column(String(20))
    edicao: Mapped[str] = mapped_column(String(10))  # "2014" ou "2024"
    importado_em: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    arquivo_origem: Mapped[str | None] = mapped_column(String(300), nullable=True)


# Tipos válidos de Personagem — monstro (docs/monstros/), npc nomeado (docs/personagens/, fora de
# genericos/) e jogador (docs/wiki/jogadores/). NPCs genéricos, figurantes de sessão sem página
# própria e a ficha de cidade ficam de fora de propósito — ver .claude/contexto/personagens.md.
TIPOS_ATOR = ("monstro", "npc", "jogador")

CONDICOES_D20 = (
    "Agarrado", "Apavorado", "Atordoado", "Caído", "Cego", "Enfeitiçado", "Envenenado",
    "Exausto", "Incapacitado", "Inconsciente", "Invisível", "Paralisado", "Petrificado",
    "Restringido", "Surdo",
)
TIPOS_EFEITO = ("Temporário", "Passivo", "Inativo")

# Os 13 tipos de dano do 5e, pra grade de Imunidades/Resistências/Vulnerabilidades (ver
# FichaResistenciaDano) — mesma ideia de CONDICOES_D20: lista fixa validada em Python, não um
# catálogo que cresce.
TIPOS_DANO = (
    "Ácido", "Contundente", "Cortante", "Elétrico", "Fogo", "Força", "Frio", "Necrótico",
    "Perfurante", "Psíquico", "Radiante", "Sônico", "Veneno",
)
MODOS_RESISTENCIA_DANO = ("imune", "resistente", "vulneravel")

# Descanso que reseta os contadores de uso de Habilidade (ver FichaHabilidade.tipo_descanso) — um
# "curto" reseta só os de descanso curto; um "longo" (personagens_api.descanso_longo) reseta os
# dois, junto com PV e espaços de magia.
TIPOS_DESCANSO = ("curto", "longo")

# Tipo de ação gasta pra usar o item — alimenta o filtro da lista de Favoritos na aba Atributos da
# ficha (docs/javascripts/ficha.js). Existe em paralelo a Habilidade.tipo (traço/ação/reação, que é
# a categoria do catálogo): aqui é especificamente "quanto custa pra usar", por isso Equipamento e
# Magia também ganham o campo, não só Habilidade.
TIPOS_ACAO = ("acao", "acao_bonus", "reacao", "nenhuma")

# Categoria de uma Interacao (Master's Shield) — o que aconteceu, não quem/onde/quando (isso são
# colunas próprias). "xp"/"loot" são escritos automaticamente por combate_api.distribuir_xp/
# aplicar_loot (ver sessao_viva_api.registrar_interacao), o resto é lançado manualmente pelo Mestre.
TIPOS_INTERACAO = (
    "teste_habilidade", "ataque", "dano", "cura", "dialogo", "xp", "loot", "evento_livre",
)
PAPEIS_INTERACAO_PARTICIPANTE = ("ator", "alvo", "testemunha")


class Personagem(Base):
    """Um ator jogável no sistema (a família de fichas) — monstro, NPC nomeado ou jogador,
    distinguidos por `tipo`. Espelha o bloco `monstro:`/`npc:`/`jogador:` do front matter da
    página correspondente; a ficha de combate em si (`## Ficha de combate` na página) fica
    reduzida a um marcador (ver hooks/gallancourt.py), lido/escrito por aqui. Biografia e Diário
    moram aqui (não em `Ficha`) porque pertencem ao personagem, não a uma variante de combate
    específica — a aparência de um Goblin não muda entre a ficha Base e a variante Arqueiro."""
    __tablename__ = "personagens"
    __table_args__ = (UniqueConstraint("tipo", "slug", name="uq_personagens_tipo_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(10), index=True)  # ver TIPOS_ATOR
    slug: Mapped[str] = mapped_column(String(100), index=True)
    nome: Mapped[str] = mapped_column(String(200))
    tamanho: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "Humanoide (goblinoide)" pra monstro, "Humano" pra NPC/jogador — mesmo campo, usos distintos
    # por tipo; renomeado de `tipo` (que agora é o discriminador monstro/npc/jogador acima).
    tipo_criatura: Mapped[str | None] = mapped_column(String(100), nullable=True)
    alinhamento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Caminho público (ex.: /assets/imagens/monstros/goblin.png) — ver
    # admin/personagens_api.py::salvar_foto_personagem. Uma foto por personagem (compartilhada
    # entre Base e variantes), não por ficha.
    foto: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Biografia (ver docs/javascripts/ficha.js, aba Biografia) — texto livre, preenchido só pelo
    # Mestre; nada aqui é calculado nem obrigatório.
    genero: Mapped[str | None] = mapped_column(String(50), nullable=True)
    idade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    altura: Mapped[str | None] = mapped_column(String(50), nullable=True)
    peso_corporal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    olhos: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cabelo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pele: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fe: Mapped[str | None] = mapped_column(String(100), nullable=True)
    aparencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    personalidade: Mapped[str | None] = mapped_column(Text, nullable=True)
    traco: Mapped[str | None] = mapped_column(Text, nullable=True)
    ideal: Mapped[str | None] = mapped_column(Text, nullable=True)
    vinculo: Mapped[str | None] = mapped_column(Text, nullable=True)
    defeito: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Texto livre por ora (não um link real pra página de NPC/lugar) — decisão do autor, consistente
    # com o resto do projeto não relacionar/calcular automaticamente antes da hora.
    pessoas_interesse: Mapped[str | None] = mapped_column(Text, nullable=True)
    lugares_interesse: Mapped[str | None] = mapped_column(Text, nullable=True)

    fichas: Mapped[list["Ficha"]] = relationship(
        back_populates="personagem", cascade="all, delete-orphan", order_by="Ficha.id",
    )
    diario_vinculo: Mapped[list["PersonagemDiarioEntrada"]] = relationship(
        back_populates="personagem", cascade="all, delete-orphan",
        order_by="PersonagemDiarioEntrada.id",
    )


class PersonagemDiarioEntrada(Base):
    """Uma entrada da aba Diário — lista separada (data/título/texto), não um texto único, a
    pedido do autor: cada sessão ou acontecimento vira sua própria entrada, com botão de
    adicionar no widget, em vez de uma caixa de texto corrida."""
    __tablename__ = "personagem_diario_entradas"

    id: Mapped[int] = mapped_column(primary_key=True)
    personagem_id: Mapped[int] = mapped_column(ForeignKey("personagens.id"))
    data: Mapped[str | None] = mapped_column(String(50), nullable=True)
    titulo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    texto: Mapped[str | None] = mapped_column(Text, nullable=True)

    personagem: Mapped["Personagem"] = relationship(back_populates="diario_vinculo")


class Ficha(Base):
    """Uma ficha de combate dentro de um Personagem — a primeira criada é sempre `is_base=True`
    ("Base", nunca removível); as demais são variantes (ex.: "Arqueiro"), cópias independentes
    totalmente editáveis. Atributos em inteiro (não texto) para o modificador poder ser calculado
    ao vivo, igual a jogadores/NPCs (ver admin/wiki_data.py::modificador)."""
    __tablename__ = "fichas"

    id: Mapped[int] = mapped_column(primary_key=True)
    personagem_id: Mapped[int] = mapped_column(ForeignKey("personagens.id"))
    rotulo: Mapped[str] = mapped_column(String(100), default="Base")
    is_base: Mapped[bool] = mapped_column(default=False)
    # Monstro usa `cr` (valor SRD, ex. "1/4" — XP vem de CR_PARA_XP, não armazenado). NPC/jogador
    # usam `nivel`/`xp` em vez disso — escalas diferentes, por isso campos separados, não
    # reaproveitados.
    cr: Mapped[str | None] = mapped_column(String(10), nullable=True)
    nivel: Mapped[int | None] = mapped_column(nullable=True)
    xp: Mapped[int | None] = mapped_column(nullable=True)
    # Rótulos livres de cabeçalho (ex.: "Guerreiro 5", "Soldado") — não multiclasse estruturado;
    # o "motor de regras" que precisaria disso de verdade ainda não existe (ver ARQUITETURA.md).
    classe: Mapped[str | None] = mapped_column(String(150), nullable=True)
    subclasse: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # Raça estruturada (ver Raca/RacaTraco, 2026-11-05) — aditivo, igual a FichaClasse: nenhum
    # código que já lê a ficha precisa mudar, só quem for aplicar traços raciais automaticamente.
    raca_id: Mapped[int | None] = mapped_column(ForeignKey("racas.id"), nullable=True)
    antecedente: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bonus_proficiencia: Mapped[int] = mapped_column(default=2)
    forca: Mapped[int] = mapped_column(default=10)
    destreza: Mapped[int] = mapped_column(default=10)
    constituicao: Mapped[int] = mapped_column(default=10)
    inteligencia: Mapped[int] = mapped_column(default=10)
    sabedoria: Mapped[int] = mapped_column(default=10)
    carisma: Mapped[int] = mapped_column(default=10)
    # CA é um número editado pelo Mestre — trocar o equipamento na ficha não recalcula sozinho
    # ainda (isso é o motor de cálculo, propositalmente fora de escopo por agora).
    ca_total: Mapped[int] = mapped_column(default=10)
    pv_formula: Mapped[str | None] = mapped_column(String(50), nullable=True)  # ex.: "2d6"
    pv_maximo: Mapped[int] = mapped_column(default=1)
    pv_atual: Mapped[int] = mapped_column(default=1)
    pv_temporario: Mapped[int] = mapped_column(default=0)
    dados_vida_total: Mapped[str | None] = mapped_column(String(50), nullable=True)  # ex.: "3d8"
    dados_vida_usados: Mapped[int] = mapped_column(default=0)
    # Deslocamento principal (a pé), em metros — número pra dar pra usar seta +/- de 1,5 m no
    # editor. Deslocamentos extras (voo, escavar, nadar...) ficam em texto livre à parte, já que
    # variam demais em quantidade/tipo pra virar campo numérico próprio.
    deslocamento_m: Mapped[float] = mapped_column(default=9.0)
    deslocamento_extra: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # Número puro (10 + perícia de Percepção, mas guardado direto — não recalculado sozinho, como
    # ca_total). Toda criatura tem um, por isso é coluna própria, não um Sentido do catálogo (que
    # só guarda sentidos especiais de alcance: Visão no escuro, Visão cega, Tremorsentido...).
    percepcao_passiva: Mapped[int] = mapped_column(default=10)
    # Mesma ideia de percepcao_passiva — número pronto, não recalculado a partir de perícia.
    investigacao_passiva: Mapped[int] = mapped_column(default=10)
    intuicao_passiva: Mapped[int] = mapped_column(default=10)
    # Somado ao modificador de Destreza na exibição (não um total já pronto) — cobre casos como o
    # dote Alerta, sem precisar guardar o total calculado.
    iniciativa_extra: Mapped[int] = mapped_column(default=0)
    # Nulos até o Mestre preencher (nem toda ficha conjura) — número pronto, igual a ca_total, não
    # calculado a partir de classe/nível/atributo.
    cd_conjuracao: Mapped[int | None] = mapped_column(nullable=True)
    bonus_ataque_magico: Mapped[int | None] = mapped_column(nullable=True)
    # Nulo = o widget usa o padrão SRD (2x Força em kg) sem guardar nada; preenchido só quando o
    # Mestre quer um valor diferente do padrão.
    carga_maxima: Mapped[float | None] = mapped_column(nullable=True)
    moeda_pc: Mapped[int] = mapped_column(default=0)
    moeda_pp: Mapped[int] = mapped_column(default=0)
    moeda_pe: Mapped[int] = mapped_column(default=0)
    moeda_po: Mapped[int] = mapped_column(default=0)
    moeda_pl: Mapped[int] = mapped_column(default=0)

    personagem: Mapped["Personagem"] = relationship(back_populates="fichas")
    equipamentos_vinculo: Mapped[list["FichaEquipamento"]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan",
    )
    habilidades_vinculo: Mapped[list["FichaHabilidade"]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan",
    )
    magias_vinculo: Mapped[list["FichaMagia"]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan",
    )
    idiomas_vinculo: Mapped[list["FichaIdioma"]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan",
    )
    sentidos_vinculo: Mapped[list["FichaSentido"]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan",
    )
    pericias_vinculo: Mapped[list["FichaPericia"]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan",
    )
    espacos_magia_vinculo: Mapped[list["FichaEspacoMagia"]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan",
    )
    condicoes_vinculo: Mapped[list["FichaCondicao"]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan",
    )
    efeitos_vinculo: Mapped[list["FichaEfeito"]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan",
    )
    resistencias_dano_vinculo: Mapped[list["FichaResistenciaDano"]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan",
    )
    classes_vinculo: Mapped[list["FichaClasse"]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan",
    )
    raca: Mapped["Raca"] = relationship()


class Equipamento(Base):
    """Catálogo compartilhado de equipamento, reutilizável entre fichas — espelha
    `docs/itens/*.md` (campo `slug_origem` aponta pra página de origem, quando vier de lá) mais
    peças exclusivas de um personagem (`origem_personagem_slug` preenchido, sem página própria)."""
    __tablename__ = "equipamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), index=True)
    categoria: Mapped[str | None] = mapped_column(String(100), nullable=True)
    custo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Número de verdade (kg), não texto — todo valor real já seguia o padrão "<número> kg", então
    # a conversão foi mecânica (ver migração). Alimenta `Ficha.carga_maxima` no futuro.
    peso_kg: Mapped[float | None] = mapped_column(nullable=True)
    dano_formula: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dano_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    propriedades: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # ca_bonus: só quando a CA do item é um número fixo somado (ex.: escudo "+2"). Armaduras
    # normais têm fórmula (ex.: "12 + mod. de Destreza") — fica em ca_formula, texto livre; nenhum
    # dos dois tenta resolver o cálculo sozinho, é o "motor de cálculo" futuro que faria isso.
    ca_bonus: Mapped[int | None] = mapped_column(nullable=True)
    ca_formula: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raridade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fonte: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fonte_id: Mapped[int | None] = mapped_column(ForeignKey("fontes.id"), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug_origem: Mapped[str | None] = mapped_column(String(200), nullable=True)
    origem_tipo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    origem_personagem_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tipo_acao: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ver TIPOS_ACAO
    # Definição estática de item com carga (ex.: Varinha de Mísseis Mágicos = 7) — None = item sem
    # cargas, continua usando FichaEquipamento.quantidade como consumível de uso único (poção etc.).
    # A quantidade restante de cada instância fica em FichaEquipamento.cargas_atual, não aqui.
    cargas_maximo: Mapped[int | None] = mapped_column(nullable=True)
    # Marca o item como cantêiner (Mochila, Bolsa de Componentes...) — cresce pelo mesmo picker
    # "criar no catálogo" que já existe, sem rota nova. capacidade_kg só importa quando e_container.
    e_container: Mapped[bool] = mapped_column(default=False)
    capacidade_kg: Mapped[float | None] = mapped_column(nullable=True)


class Magia(Base):
    """Catálogo compartilhado de magias — espelha `docs/magias/*.md`."""
    __tablename__ = "magias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), index=True)
    nivel: Mapped[int | None] = mapped_column(nullable=True)
    escola: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tempo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    alcance: Mapped[str | None] = mapped_column(String(100), nullable=True)
    componentes: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duracao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    classes: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dano_formula: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dano_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resistencia: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fonte: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fonte_id: Mapped[int | None] = mapped_column(ForeignKey("fontes.id"), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug_origem: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tipo_acao: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ver TIPOS_ACAO


class Habilidade(Base):
    """Catálogo compartilhado de traços/ações/reações — `origem_tipo`/`origem_personagem_slug`
    marcam o que nasceu exclusivo de um personagem, pra poder filtrar/ordenar por origem no
    seletor "+ adicionar"."""
    __tablename__ = "habilidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), index=True)
    tipo: Mapped[str] = mapped_column(String(20))  # "traco" | "acao" | "reacao"
    bonus_acerto: Mapped[int | None] = mapped_column(nullable=True)
    dano_formula: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dano_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    alcance: Mapped[str | None] = mapped_column(String(100), nullable=True)
    usos: Mapped[str | None] = mapped_column(String(50), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    origem_tipo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    origem_personagem_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tipo_acao: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ver TIPOS_ACAO
    fonte_id: Mapped[int | None] = mapped_column(ForeignKey("fontes.id"), nullable=True)


class Idioma(Base):
    """Catálogo compartilhado de idiomas (Comum, Goblin, Abissal…) — só o nome; "conhecer um
    idioma" não tem valor próprio, ao contrário de um sentido (ver Sentido)."""
    __tablename__ = "idiomas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, index=True)


class Sentido(Base):
    """Catálogo compartilhado de sentidos especiais de alcance (Visão no escuro, Visão cega,
    Tremorsentido, Visão verdadeira…) — sempre um alcance em metros. O valor (ex.: 18.0) fica no
    vínculo (FichaSentido), não aqui, já que o mesmo sentido tem alcances diferentes em cada
    personagem. Percepção passiva NÃO mora aqui: é `Ficha.percepcao_passiva`, porque todo
    personagem tem uma (não é uma "escolha" de catálogo) e não é uma distância."""
    __tablename__ = "sentidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, index=True)


class Pericia(Base):
    """Catálogo compartilhado das 18 perícias do D&D 5e — espelha `docs/pericias/*.md`."""
    __tablename__ = "pericias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    atributo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fonte: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fonte_id: Mapped[int | None] = mapped_column(ForeignKey("fontes.id"), nullable=True)
    slug_origem: Mapped[str | None] = mapped_column(String(200), nullable=True)


class FichaEquipamento(Base):
    """Vínculo N:N entre ficha e Equipamento — com quantidade/equipado, por isso é uma tabela
    própria em vez de uma `secondary=` simples. `favorito` é por ficha, mesma lógica de
    FichaHabilidade.favorito/FichaMagia.favorito."""
    __tablename__ = "ficha_equipamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    equipamento_id: Mapped[int] = mapped_column(ForeignKey("equipamentos.id"))
    quantidade: Mapped[int] = mapped_column(default=1)
    equipado: Mapped[bool] = mapped_column(default=True)
    favorito: Mapped[bool] = mapped_column(default=False)
    # Cargas restantes desta instância — só relevante quando Equipamento.cargas_maximo não é nulo;
    # None enquanto o catálogo não define cargas pra esse item (consumível normal via quantidade).
    cargas_atual: Mapped[int | None] = mapped_column(nullable=True)
    # Autorreferencial: aponta pro FichaEquipamento (da mesma ficha) que é o cantêiner guardando este
    # item. None = solto. Só itens cujo Equipamento.e_container é True fazem sentido como destino.
    guardado_em_vinculo_id: Mapped[int | None] = mapped_column(
        ForeignKey("ficha_equipamentos.id"), nullable=True
    )

    ficha: Mapped["Ficha"] = relationship(back_populates="equipamentos_vinculo")
    equipamento: Mapped["Equipamento"] = relationship()


class FichaHabilidade(Base):
    """Vínculo N:N entre ficha e Habilidade — `favorito`/`usos_*` são por ficha (a mesma Habilidade
    do catálogo pode ser favoritada numa ficha e não na outra, ou ter usos restantes diferentes),
    por isso moram aqui, não em Habilidade."""
    __tablename__ = "ficha_habilidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    habilidade_id: Mapped[int] = mapped_column(ForeignKey("habilidades.id"))
    favorito: Mapped[bool] = mapped_column(default=False)
    # Nulos = sem contador (usos ilimitados ou não rastreados) — só preenchidos quando o Mestre
    # quer acompanhar "usos por descanso" de verdade, em vez do texto livre em Habilidade.usos.
    usos_maximo: Mapped[int | None] = mapped_column(nullable=True)
    usos_restantes: Mapped[int | None] = mapped_column(nullable=True)
    tipo_descanso: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ver TIPOS_DESCANSO

    ficha: Mapped["Ficha"] = relationship(back_populates="habilidades_vinculo")
    habilidade: Mapped["Habilidade"] = relationship()


class FichaMagia(Base):
    """Vínculo N:N entre ficha e Magia — `favorito` é por ficha, mesma lógica de
    FichaHabilidade.favorito."""
    __tablename__ = "ficha_magias"

    id: Mapped[int] = mapped_column(primary_key=True)
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    magia_id: Mapped[int] = mapped_column(ForeignKey("magias.id"))
    favorito: Mapped[bool] = mapped_column(default=False)

    ficha: Mapped["Ficha"] = relationship(back_populates="magias_vinculo")
    magia: Mapped["Magia"] = relationship()


class FichaIdioma(Base):
    """Vínculo N:N entre ficha e Idioma — sem campo extra, só "conhece ou não"."""
    __tablename__ = "ficha_idiomas"

    id: Mapped[int] = mapped_column(primary_key=True)
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    idioma_id: Mapped[int] = mapped_column(ForeignKey("idiomas.id"))

    ficha: Mapped["Ficha"] = relationship(back_populates="idiomas_vinculo")
    idioma: Mapped["Idioma"] = relationship()


class FichaSentido(Base):
    """Vínculo N:N entre ficha e Sentido, com o alcance específico desta ficha, em metros (ex.:
    18.0) — número de verdade, não texto, pra dar pra comparar/usar num motor de combate futuro."""
    __tablename__ = "ficha_sentidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    sentido_id: Mapped[int] = mapped_column(ForeignKey("sentidos.id"))
    valor: Mapped[float | None] = mapped_column(nullable=True)

    ficha: Mapped["Ficha"] = relationship(back_populates="sentidos_vinculo")
    sentido: Mapped["Sentido"] = relationship()


class FichaPericia(Base):
    """Vínculo N:N entre ficha e Pericia, com o bônus total já pronto pra rolar (ex.: +6) — não é
    calculado de atributo+proficiência: é o número final editado pelo Mestre, igual a ca_total."""
    __tablename__ = "ficha_pericias"

    id: Mapped[int] = mapped_column(primary_key=True)
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    pericia_id: Mapped[int] = mapped_column(ForeignKey("pericias.id"))
    bonus: Mapped[int] = mapped_column(default=0)

    ficha: Mapped["Ficha"] = relationship(back_populates="pericias_vinculo")
    pericia: Mapped["Pericia"] = relationship()


class FichaEspacoMagia(Base):
    """Um pool de espaços de magia da ficha (ex.: Nível 2 Normal: 3 máx./1 usado; Nível 2 Magia de
    Pacto: 2 máx./0 usados) — `rotulo` permite dois pools no mesmo `nivel` (caso do Bruxo),
    distinto do nível em si. Só a contagem; nada calcula espaço a partir de classe/nível."""
    __tablename__ = "fichas_espacos_magia"

    id: Mapped[int] = mapped_column(primary_key=True)
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    nivel: Mapped[int] = mapped_column(default=1)
    maximo: Mapped[int] = mapped_column(default=1)
    usado: Mapped[int] = mapped_column(default=0)
    rotulo: Mapped[str | None] = mapped_column(String(50), nullable=True)

    ficha: Mapped["Ficha"] = relationship(back_populates="espacos_magia_vinculo")


class FichaCondicao(Base):
    """Presença de uma condição ativa na ficha — `nome` validado em Python contra a lista fixa
    `CONDICOES_D20` (as 15 condições do 5e), não um catálogo no banco: é um conjunto fechado de
    regras, não conteúdo que cresce como Equipamento/Magia."""
    __tablename__ = "fichas_condicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    nome: Mapped[str] = mapped_column(String(30))

    ficha: Mapped["Ficha"] = relationship(back_populates="condicoes_vinculo")


class FichaResistenciaDano(Base):
    """Imunidade/Resistência/Vulnerabilidade a um tipo de dano — `nome` validado contra
    `TIPOS_DANO`, `modo` contra `MODOS_RESISTENCIA_DANO`. Só um `modo` ativo por tipo de dano por
    ficha (ver personagens_api.alternar_resistencia_dano); informativo na ficha, não entra na
    matemática de dano do Combat Tracker (ver .claude/contexto/combate.md)."""
    __tablename__ = "ficha_resistencias_dano"

    id: Mapped[int] = mapped_column(primary_key=True)
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    nome: Mapped[str] = mapped_column(String(30))
    modo: Mapped[str] = mapped_column(String(15))

    ficha: Mapped["Ficha"] = relationship(back_populates="resistencias_dano_vinculo")


class FichaEfeito(Base):
    """Um efeito aplicado (temporário/passivo/inativo) — específico desta ficha, não um catálogo
    compartilhado: um "Abençoado por 1 minuto" não tem valor de reuso entre personagens, ao
    contrário de um item de Equipamento ou uma Magia do grimório."""
    __tablename__ = "fichas_efeitos"

    id: Mapped[int] = mapped_column(primary_key=True)
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    nome: Mapped[str] = mapped_column(String(200))
    tipo: Mapped[str] = mapped_column(String(20))  # ver TIPOS_EFEITO
    origem: Mapped[str | None] = mapped_column(String(200), nullable=True)
    duracao: Mapped[str | None] = mapped_column(String(100), nullable=True)

    ficha: Mapped["Ficha"] = relationship(back_populates="efeitos_vinculo")


class Combate(Base):
    """Uma luta/encontro rodado no Combat Tracker de uma página de sessão
    (docs/mestre/sessoes/sessao-N-*.md) — substitui o antigo admin/sessao_viva.py (estado em JSON
    fora do banco, só acessível com o Painel local rodando). Uma página pode ter vários Combates
    ao longo do tempo (um por encontro); só um fica `ativo` por vez nela."""
    __tablename__ = "combates"

    id: Mapped[int] = mapped_column(primary_key=True)
    pagina_rel_docs: Mapped[str] = mapped_column(String(300), index=True)
    rodada: Mapped[int] = mapped_column(default=1)
    # Sem ForeignKey de propósito (evita referência circular com combate_participantes.combate_id
    # dentro da mesma migração) — é só um ponteiro pra posição atual na ordem, não precisa de
    # integridade referencial forte; admin/combate_api.py sempre confere se o id ainda existe.
    turno_participante_id: Mapped[int | None] = mapped_column(nullable=True)
    ativo: Mapped[bool] = mapped_column(default=True)
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.UTC)
    )
    finalizado_em: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    participantes: Mapped[list["CombateParticipante"]] = relationship(
        back_populates="combate", cascade="all, delete-orphan",
        order_by="CombateParticipante.id",
    )
    log_vinculo: Mapped[list["CombateLogEntrada"]] = relationship(
        back_populates="combate", cascade="all, delete-orphan", order_by="CombateLogEntrada.id",
    )


class CombateParticipante(Base):
    """Um token dentro de um Combate — aponta pra uma Ficha real (`ficha_id`), mas o que é cópia
    isolada e o que é vínculo ao vivo depende do tipo do Personagem dono da Ficha (ver
    `Personagem.tipo`, consultado via `ficha.personagem.tipo`):
    - monstro: `copia_pv_atual`/`copia_pv_temporario` e `CombateParticipanteCondicao` guardam o
      estado deste participante isolado — nada aqui toca a Ficha real do catálogo (a mesma Ficha
      de "Goblin" pode estar em vários CombateParticipante ao mesmo tempo, cada um com seu PV).
    - npc/jogador: PV/PV temporário são lidos/escritos direto em `Ficha.pv_atual`/`pv_temporario`
      (`copia_pv_atual`/`copia_pv_temporario` ficam `None`); as condições também viram
      `FichaCondicao` de verdade, visíveis na aba Efeitos da própria ficha — só "resetam" com um
      Descanso Longo (ver admin/personagens_api.py)."""
    __tablename__ = "combate_participantes"

    id: Mapped[int] = mapped_column(primary_key=True)
    combate_id: Mapped[int] = mapped_column(ForeignKey("combates.id"))
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    nome_exibicao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    iniciativa_base: Mapped[int] = mapped_column(default=0)
    iniciativa_desempate: Mapped[int] = mapped_column(default=0)
    acao_usada: Mapped[bool] = mapped_column(default=False)
    acao_bonus_usada: Mapped[bool] = mapped_column(default=False)
    reacao_usada: Mapped[bool] = mapped_column(default=False)
    movimento_usado: Mapped[bool] = mapped_column(default=False)
    concentrando_em: Mapped[str | None] = mapped_column(String(200), nullable=True)
    death_save_sucessos: Mapped[int] = mapped_column(default=0)
    death_save_falhas: Mapped[int] = mapped_column(default=0)
    copia_pv_atual: Mapped[int | None] = mapped_column(nullable=True)
    copia_pv_temporario: Mapped[int | None] = mapped_column(nullable=True)

    combate: Mapped["Combate"] = relationship(back_populates="participantes")
    ficha: Mapped["Ficha"] = relationship()
    condicoes_vinculo: Mapped[list["CombateParticipanteCondicao"]] = relationship(
        back_populates="participante", cascade="all, delete-orphan",
    )
    recursos_copia_vinculo: Mapped[list["CombateParticipanteRecursoCopia"]] = relationship(
        back_populates="participante", cascade="all, delete-orphan",
    )


class CombateParticipanteCondicao(Base):
    """Condição ativa num participante do combate — nome validado contra CONDICOES_D20, igual a
    FichaCondicao. Para npc/jogador, admin/combate_api.py espelha a mesma condição como
    FichaCondicao de verdade (aparece na aba Efeitos); para monstro, fica só aqui, isolada."""
    __tablename__ = "combate_participante_condicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    participante_id: Mapped[int] = mapped_column(ForeignKey("combate_participantes.id"))
    nome: Mapped[str] = mapped_column(String(30))

    participante: Mapped["CombateParticipante"] = relationship(back_populates="condicoes_vinculo")


class CombateParticipanteRecursoCopia(Base):
    """Pool de recurso consumível (slot de magia ou carga de item) isolado de um participante
    **monstro** — mesmo princípio de `copia_pv_atual`: a mesma Ficha de "Goblin Xamã" pode estar em
    várias cópias simultâneas no combate, cada uma gastando seus próprios slots/cargas, sem tocar
    a Ficha real do catálogo. Semeado a partir dos pools da Ficha em
    `combate_api.adicionar_participante`. Para npc/jogador, o Combat Tracker lê/escreve direto em
    `FichaEspacoMagia`/`FichaEquipamento.cargas_atual` (não usa esta tabela — ver
    combate_api._e_copia)."""
    __tablename__ = "combate_participante_recursos_copia"

    id: Mapped[int] = mapped_column(primary_key=True)
    participante_id: Mapped[int] = mapped_column(ForeignKey("combate_participantes.id"))
    tipo: Mapped[str] = mapped_column(String(20))  # "slot_magia" | "carga_item"
    # slot_magia: nível do espaço (1-9). carga_item: id de FichaEquipamento (vínculo na Ficha base).
    referencia: Mapped[int] = mapped_column()
    maximo: Mapped[int] = mapped_column(default=0)
    usado: Mapped[int] = mapped_column(default=0)

    participante: Mapped["CombateParticipante"] = relationship(back_populates="recursos_copia_vinculo")


class CombateLogEntrada(Base):
    """Uma linha do log de combate (módulo 5.2 do pedido) — texto pronto pra exibir e exportar em
    JSON/TXT, não recalculado a partir de outra coisa."""
    __tablename__ = "combate_log_entradas"

    id: Mapped[int] = mapped_column(primary_key=True)
    combate_id: Mapped[int] = mapped_column(ForeignKey("combates.id"))
    rodada: Mapped[int] = mapped_column(default=1)
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.UTC)
    )
    texto: Mapped[str] = mapped_column(Text)
    tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)

    combate: Mapped["Combate"] = relationship(back_populates="log_vinculo")


class EncontroPlanejado(Base):
    """Um rascunho de encontro preparado antes da sessão, numa página de sessão
    (docs/mestre/sessoes/sessao-N-*.md) — uma página pode ter vários (ex. "Emboscada na ponte",
    "Boss final"). Ao iniciar o Combat Tracker a partir dele, os participantes planejados viram
    CombateParticipante de verdade (ver admin/encontro_api.py::carregar_no_combate); o rascunho em
    si nunca participa do combate, só serve de molde."""
    __tablename__ = "encontros_planejados"

    id: Mapped[int] = mapped_column(primary_key=True)
    pagina_rel_docs: Mapped[str] = mapped_column(String(300), index=True)
    nome: Mapped[str] = mapped_column(String(200))
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.UTC)
    )

    participantes_vinculo: Mapped[list["EncontroParticipantePlanejado"]] = relationship(
        back_populates="encontro", cascade="all, delete-orphan",
        order_by="EncontroParticipantePlanejado.ordem",
    )


class EncontroParticipantePlanejado(Base):
    """Um participante dentro de um EncontroPlanejado — mesmo formato de CombateParticipante
    (ficha_id + nome_exibicao), só que antes do Combate existir; `ordem` define a posição na lista
    (não é iniciativa, que só é sorteada/digitada quando o combate de fato começa)."""
    __tablename__ = "encontro_participantes_planejados"

    id: Mapped[int] = mapped_column(primary_key=True)
    encontro_id: Mapped[int] = mapped_column(ForeignKey("encontros_planejados.id"))
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    nome_exibicao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ordem: Mapped[int] = mapped_column(default=0)

    encontro: Mapped["EncontroPlanejado"] = relationship(back_populates="participantes_vinculo")
    ficha: Mapped["Ficha"] = relationship()


PROGRESSOES_CONJURACAO = ("completo", "meio", "terco", "pacto")


def bonus_proficiencia_por_nivel(nivel: int) -> int:
    """Tabela universal do 5e (igual pra qualquer classe) — 2 no nível 1-4, +1 a cada 4 níveis."""
    return 2 + (max(1, nivel) - 1) // 4


# Slots de magia por nível de conjurador "completo" combinado (Mago/Clérigo/Druida/Bardo/
# Feiticeiro contam o nível inteiro; meio-conjurador como Paladino/Patrulheiro conta nível÷2;
# terço-conjurador conta nível÷3 — soma tudo e consulta esta mesma tabela, regra padrão de
# multiclasse do 5e SRD). Índice = nível de conjurador combinado (1-20); valor = {nível da magia:
# quantidade de espaços}.
TABELA_SLOTS_CONJURADOR_COMPLETO = {
    1: {1: 2},
    2: {1: 3},
    3: {1: 4, 2: 2},
    4: {1: 4, 2: 3},
    5: {1: 4, 2: 3, 3: 2},
    6: {1: 4, 2: 3, 3: 3},
    7: {1: 4, 2: 3, 3: 3, 4: 1},
    8: {1: 4, 2: 3, 3: 3, 4: 2},
    9: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
    11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    12: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    14: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    16: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
    18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1},
    19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1},
    20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
}

# Magia de Pacto do Bruxo (pool separado, rotulo="Pacto" em FichaEspacoMagia) — nível do Bruxo ->
# (quantidade de espaços, nível de cada espaço). Não combina com a tabela acima.
TABELA_SLOTS_PACTO_BRUXO = {
    1: (1, 1), 2: (2, 1), 3: (2, 2), 4: (2, 2), 5: (2, 3), 6: (2, 3), 7: (2, 4), 8: (2, 4),
    9: (2, 5), 10: (2, 5), 11: (3, 5), 12: (3, 5), 13: (3, 5), 14: (3, 5), 15: (3, 5), 16: (3, 5),
    17: (4, 5), 18: (4, 5), 19: (4, 5), 20: (4, 5),
}


class Classe(Base):
    """Catálogo de classes (Guerreiro, Mago, ...) — reabre, a pedido explícito do autor
    (2026-11-04), a decisão anterior de não ter multiclasse estruturada (ver
    .claude/contexto/personagens.md). Até 2026-11-05 crescia só sob demanda, criada pelo próprio
    Mestre ao usar "Subir de nível" numa classe nova; desde então as classes base do Livro do
    Jogador vêm semeadas por `scripts/importar_classes_livro.py` — continua podendo crescer sob
    demanda pra classes homebrew."""
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    dado_vida: Mapped[int] = mapped_column()  # 6, 8, 10 ou 12
    atributo_conjuracao: Mapped[str | None] = mapped_column(String(20), nullable=True)  # for/des/con/int/sab/car
    progressao_conjuracao: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ver PROGRESSOES_CONJURACAO
    fonte_id: Mapped[int | None] = mapped_column(ForeignKey("fontes.id"), nullable=True)
    pagina_rel_docs: Mapped[str | None] = mapped_column(String(300), nullable=True)

    subclasses_vinculo: Mapped[list["Subclasse"]] = relationship(
        back_populates="classe", cascade="all, delete-orphan",
    )
    features_vinculo: Mapped[list["ClasseFeature"]] = relationship(
        back_populates="classe", cascade="all, delete-orphan",
    )


class Subclasse(Base):
    __tablename__ = "subclasses"

    id: Mapped[int] = mapped_column(primary_key=True)
    classe_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    nome: Mapped[str] = mapped_column(String(150))

    classe: Mapped["Classe"] = relationship(back_populates="subclasses_vinculo")


class ClasseFeature(Base):
    """O que uma classe (ou subclasse, se `subclasse_id` preenchido) concede num nível — ao subir
    de nível, cada feature do nível vira (get-or-create) uma `Habilidade` de catálogo +
    `FichaHabilidade` vinculada (ver personagens_api.subir_de_nivel). Opcional: uma classe sem
    nenhuma feature cadastrada ainda funciona normalmente pra PV/bônus de proficiência/slots, só
    não desbloqueia nada sozinha."""
    __tablename__ = "classe_features"

    id: Mapped[int] = mapped_column(primary_key=True)
    classe_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    subclasse_id: Mapped[int | None] = mapped_column(ForeignKey("subclasses.id"), nullable=True)
    nivel: Mapped[int] = mapped_column()
    nome: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    classe: Mapped["Classe"] = relationship(back_populates="features_vinculo")
    subclasse: Mapped["Subclasse"] = relationship()


class FichaClasse(Base):
    """Nível de uma Ficha numa Classe — uma ficha pode ter várias linhas (multiclasse). Substitui
    `Ficha.classe`/`subclasse`/`nivel` como fonte de verdade quando preenchida; esses três campos
    continuam existindo só como texto derivado (recalculado a cada subida de nível, ver
    personagens_api.subir_de_nivel), pra não quebrar nada que já lê esses campos direto."""
    __tablename__ = "ficha_classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    classe_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    subclasse_id: Mapped[int | None] = mapped_column(ForeignKey("subclasses.id"), nullable=True)
    nivel: Mapped[int] = mapped_column(default=1)

    ficha: Mapped["Ficha"] = relationship(back_populates="classes_vinculo")
    classe: Mapped["Classe"] = relationship()
    subclasse: Mapped["Subclasse"] = relationship()


class Raca(Base):
    """Catálogo de raças/linhagens (Elfo, Humano, ...) — semeado por
    scripts/importar_racas_livro.py (2026-11-05) a partir do Livro do Jogador convertido.
    Sub-raça/linhagem é a mesma tabela, com `raca_pai_id` apontando pra raça base (ex.: "Elfo das
    Florestas" → pai "Elfo") — sem tabela separada de sub-raça, mesma ideia de `Lugar.lugar_pai_id`.
    `pagina_rel_docs` casa com a página já existente em docs/racas/*.md (hand-written, não gerada
    por aqui — esta tabela só alimenta a ficha/mecânica, não o texto da wiki)."""
    __tablename__ = "racas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), index=True)
    raca_pai_id: Mapped[int | None] = mapped_column(ForeignKey("racas.id"), nullable=True)
    fonte_id: Mapped[int | None] = mapped_column(ForeignKey("fontes.id"), nullable=True)
    pagina_rel_docs: Mapped[str | None] = mapped_column(String(300), nullable=True)
    tamanho: Mapped[str | None] = mapped_column(String(50), nullable=True)
    deslocamento: Mapped[int | None] = mapped_column(nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    raca_pai: Mapped["Raca"] = relationship(remote_side="Raca.id")
    tracos_vinculo: Mapped[list["RacaTraco"]] = relationship(
        back_populates="raca", cascade="all, delete-orphan",
    )


class RacaTraco(Base):
    """Um traço racial (Visão no Escuro, Ancestral Feérico...) — mesmo princípio de
    `ClasseFeature`, uma linha por traço em vez de um texto corrido."""
    __tablename__ = "raca_tracos"

    id: Mapped[int] = mapped_column(primary_key=True)
    raca_id: Mapped[int] = mapped_column(ForeignKey("racas.id"))
    nome: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    raca: Mapped["Raca"] = relationship(back_populates="tracos_vinculo")


class Lugar(Base):
    """Um local, dentro ou fora da wiki — Master's Shield (2026-11-05). `canonico=True` +
    `pagina_rel_docs` preenchido = já existe página própria em docs/lugares/ (ver
    scripts/importar_lugares.py, que semeia essas linhas a partir das páginas já existentes).
    `canonico=False` = local provisório criado ao vivo durante a sessão (ex.: "Loja do
    Alquimista" dentro de "Dodixie", via `lugar_pai_id`) — fica provisório até o Mestre revisar
    depois da sessão e decidir se cria a página de verdade (não há automação pra isso ainda)."""
    __tablename__ = "lugares"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    pagina_rel_docs: Mapped[str | None] = mapped_column(String(300), nullable=True)
    lugar_pai_id: Mapped[int | None] = mapped_column(ForeignKey("lugares.id"), nullable=True)
    canonico: Mapped[bool] = mapped_column(default=True)
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.UTC)
    )

    lugar_pai: Mapped["Lugar"] = relationship(remote_side="Lugar.id")


class SessaoAoVivo(Base):
    """Estado "ao vivo" do Master's Shield numa página de sessão — nome temporário (a renomear
    depois, ver .claude/contexto/combate.md). Uma linha por `pagina_rel_docs`, criada sob demanda
    na primeira vez que o painel carrega (mesmo padrão de `Combate`). Guarda só o momento atual
    (ano/mes/dia/hora/minuto — texto livre pro mês, já que docs/mundo/calendario.md deixa a
    duração dos meses em aberto) e a localidade atual; o histórico mora em `Interacao`, não aqui."""
    __tablename__ = "sessoes_ao_vivo"

    id: Mapped[int] = mapped_column(primary_key=True)
    pagina_rel_docs: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    ano: Mapped[int | None] = mapped_column(nullable=True)
    mes: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dia: Mapped[int | None] = mapped_column(nullable=True)
    hora: Mapped[int | None] = mapped_column(nullable=True)
    minuto: Mapped[int | None] = mapped_column(nullable=True)
    lugar_atual_id: Mapped[int | None] = mapped_column(ForeignKey("lugares.id"), nullable=True)
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.UTC)
    )

    lugar_atual: Mapped["Lugar"] = relationship()


class Interacao(Base):
    """Uma linha do log de interações do Master's Shield — o "o que aconteceu", relacional (ver
    `InteracaoParticipante`/`Rolagem`), não texto livre. `tipo` "xp"/"loot" são gravados por
    dentro de combate_api.distribuir_xp/aplicar_loot (antes ficavam fora de qualquer log).
    Momento/local copiados de SessaoAoVivo no instante do registro — não há tabela de calendário
    separada, cada Interacao já carrega seu próprio "quando"."""
    __tablename__ = "interacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    pagina_rel_docs: Mapped[str] = mapped_column(String(300), index=True)
    combate_id: Mapped[int | None] = mapped_column(ForeignKey("combates.id"), nullable=True)
    lugar_id: Mapped[int | None] = mapped_column(ForeignKey("lugares.id"), nullable=True)
    ano: Mapped[int | None] = mapped_column(nullable=True)
    mes: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dia: Mapped[int | None] = mapped_column(nullable=True)
    hora: Mapped[int | None] = mapped_column(nullable=True)
    minuto: Mapped[int | None] = mapped_column(nullable=True)
    tipo: Mapped[str] = mapped_column(String(20))  # ver TIPOS_INTERACAO
    pericia_ou_atributo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cd: Mapped[int | None] = mapped_column(nullable=True)
    sucesso: Mapped[bool | None] = mapped_column(nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.UTC)
    )

    lugar: Mapped["Lugar"] = relationship()
    participantes_vinculo: Mapped[list["InteracaoParticipante"]] = relationship(
        back_populates="interacao", cascade="all, delete-orphan",
    )
    rolagens_vinculo: Mapped[list["Rolagem"]] = relationship(
        back_populates="interacao", cascade="all, delete-orphan",
    )


class InteracaoParticipante(Base):
    """Liga uma Interacao a uma Ficha (sempre Ficha, nunca Personagem direto — mesmo padrão de
    CombateParticipante/EncontroParticipantePlanejado), com um papel (ver
    PAPEIS_INTERACAO_PARTICIPANTE) — é o "quais tokens interagiram"."""
    __tablename__ = "interacao_participantes"

    id: Mapped[int] = mapped_column(primary_key=True)
    interacao_id: Mapped[int] = mapped_column(ForeignKey("interacoes.id"))
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    papel: Mapped[str] = mapped_column(String(20))

    interacao: Mapped["Interacao"] = relationship(back_populates="participantes_vinculo")
    ficha: Mapped["Ficha"] = relationship()


class Rolagem(Base):
    """Uma rolagem de dado presa a uma Interacao (uma interação pode ter mais de uma — ex.:
    ataque + dano). `online=False` = resultado de um dado físico, digitado pelo Mestre/jogador;
    `online=True` = rolado pelo próprio sistema (sessao_viva_api.rolar_online)."""
    __tablename__ = "rolagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    interacao_id: Mapped[int] = mapped_column(ForeignKey("interacoes.id"))
    dado: Mapped[str] = mapped_column(String(30))  # ex.: "1d20+5"
    vantagem: Mapped[str | None] = mapped_column(String(15), nullable=True)
    resultado_bruto: Mapped[int | None] = mapped_column(nullable=True)
    resultado_total: Mapped[int | None] = mapped_column(nullable=True)
    online: Mapped[bool] = mapped_column(default=False)

    interacao: Mapped["Interacao"] = relationship(back_populates="rolagens_vinculo")


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


def marcar_fonte_importada(sessao: Session, abreviacao: str, arquivo_origem: str) -> Fonte | None:
    """Registra que um importador (ver scripts/importar_*.py) alimentou os catálogos a partir
    desta fonte — `importado_em` vira "já processada alguma vez"; `arquivo_origem` guarda só o
    último arquivo/processo que a tocou (várias rodadas podem marcar a mesma Fonte de novo, não
    há lista acumulada). Devolve `None` sem erro se a abreviação não existir em `Fonte` ainda."""
    fonte = sessao.query(Fonte).filter(Fonte.abreviacao == abreviacao).first()
    if fonte is None:
        return None
    fonte.importado_em = datetime.datetime.now(datetime.UTC)
    fonte.arquivo_origem = arquivo_origem
    sessao.commit()
    return fonte


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
