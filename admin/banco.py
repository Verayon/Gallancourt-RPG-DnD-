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
    __tablename__ = "fontes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    abreviacao: Mapped[str] = mapped_column(String(20))
    edicao: Mapped[str] = mapped_column(String(10))  # "2014" ou "2024"


# Tipos válidos de Personagem — monstro (docs/monstros/), npc nomeado (docs/personagens/, fora de
# genericos/) e jogador (docs/mestre/jogadores/). NPCs genéricos, figurantes de sessão sem página
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
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug_origem: Mapped[str | None] = mapped_column(String(200), nullable=True)
    origem_tipo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    origem_personagem_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)


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
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug_origem: Mapped[str | None] = mapped_column(String(200), nullable=True)


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
    slug_origem: Mapped[str | None] = mapped_column(String(200), nullable=True)


class FichaEquipamento(Base):
    """Vínculo N:N entre ficha e Equipamento — com quantidade/equipado, por isso é uma tabela
    própria em vez de uma `secondary=` simples."""
    __tablename__ = "ficha_equipamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    ficha_id: Mapped[int] = mapped_column(ForeignKey("fichas.id"))
    equipamento_id: Mapped[int] = mapped_column(ForeignKey("equipamentos.id"))
    quantidade: Mapped[int] = mapped_column(default=1)
    equipado: Mapped[bool] = mapped_column(default=True)

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


class CombateParticipanteCondicao(Base):
    """Condição ativa num participante do combate — nome validado contra CONDICOES_D20, igual a
    FichaCondicao. Para npc/jogador, admin/combate_api.py espelha a mesma condição como
    FichaCondicao de verdade (aparece na aba Efeitos); para monstro, fica só aqui, isolada."""
    __tablename__ = "combate_participante_condicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    participante_id: Mapped[int] = mapped_column(ForeignKey("combate_participantes.id"))
    nome: Mapped[str] = mapped_column(String(30))

    participante: Mapped["CombateParticipante"] = relationship(back_populates="condicoes_vinculo")


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
