"""Ficha de personagem de D&D 5e: definições, cálculos e exibição.

Usado em dois lugares, para que os cálculos sejam sempre os mesmos:

- `hooks/gallancourt.py` (geração do site) monta a aba "Ficha de personagem" do NPC;
- `admin/wiki_data.py` (Painel do Mestre) lê e grava o formulário da ficha.

Os dados ficam no front matter da página do NPC, no bloco `ficha5e:`. Só os valores digitados são
guardados; modificadores, bônus de proficiência, testes de resistência, perícias, percepção
passiva, CD e ataque de magia são calculados na hora de exibir.

Estrutura baseada na ficha oficial de D&D 5e (página principal, detalhes e magias), com os termos
do Livro do Jogador em português.
"""
from __future__ import annotations

import html

ATRIBUTOS = [
    ("for", "Força"),
    ("des", "Destreza"),
    ("con", "Constituição"),
    ("int", "Inteligência"),
    ("sab", "Sabedoria"),
    ("car", "Carisma"),
]
SIGLAS = {"for": "FOR", "des": "DES", "con": "CON", "int": "INT", "sab": "SAB", "car": "CAR"}

# (chave, nome, atributo)
PERICIAS = [
    ("acrobacia", "Acrobacia", "des"),
    ("adestrar_animais", "Adestrar Animais", "sab"),
    ("arcanismo", "Arcanismo", "int"),
    ("atletismo", "Atletismo", "for"),
    ("atuacao", "Atuação", "car"),
    ("enganacao", "Enganação", "car"),
    ("furtividade", "Furtividade", "des"),
    ("historia", "História", "int"),
    ("intimidacao", "Intimidação", "car"),
    ("intuicao", "Intuição", "sab"),
    ("investigacao", "Investigação", "int"),
    ("medicina", "Medicina", "sab"),
    ("natureza", "Natureza", "int"),
    ("percepcao", "Percepção", "sab"),
    ("persuasao", "Persuasão", "car"),
    ("prestidigitacao", "Prestidigitação", "des"),
    ("religiao", "Religião", "int"),
    ("sobrevivencia", "Sobrevivência", "sab"),
]

# Campos de texto simples do cabeçalho e do combate: (chave, rótulo)
CAMPOS_IDENTIDADE = [
    ("classe", "Classe (e subclasse)"),
    ("nivel", "Nível"),
    ("raca", "Raça"),
    ("antecedente", "Antecedente"),
    ("alinhamento", "Alinhamento"),
    ("xp", "Pontos de experiência"),
]
CAMPOS_COMBATE = [
    ("ca", "Classe de Armadura"),
    ("ca_detalhe", "Origem da CA (ex.: cota de malha + escudo)"),
    ("iniciativa_bonus", "Bônus extra de iniciativa"),
    ("deslocamento", "Deslocamento (ex.: 9 m)"),
    ("pv_max", "PV máximos"),
    ("pv_atual", "PV atuais"),
    ("pv_temp", "PV temporários"),
    ("dados_de_vida", "Dados de vida (ex.: 5d8)"),
    ("dados_de_vida_gastos", "Dados de vida gastos"),
    ("morte_sucessos", "Testes contra a morte — sucessos (0–3)"),
    ("morte_falhas", "Testes contra a morte — falhas (0–3)"),
]
CAMPOS_PROFICIENCIAS = [
    ("armaduras", "Armaduras"),
    ("armas", "Armas"),
    ("ferramentas", "Ferramentas"),
    ("idiomas", "Idiomas"),
]
MOEDAS = [("pc", "PC"), ("pp", "PP"), ("pe", "PE"), ("po", "PO"), ("pl", "PL")]
CAMPOS_PERSONALIDADE = [
    ("tracos", "Traços de personalidade"),
    ("ideais", "Ideais"),
    ("vinculos", "Vínculos"),
    ("defeitos", "Defeitos"),
]
CAMPOS_DETALHES_CURTOS = [
    ("idade", "Idade"),
    ("altura", "Altura"),
    ("peso", "Peso"),
    ("olhos", "Olhos"),
    ("pele", "Pele"),
    ("cabelo", "Cabelo"),
]
CAMPOS_TEXTOS_LONGOS = [
    ("caracteristicas", "Características e traços"),
    ("aparencia", "Aparência"),
    ("historia", "História do personagem"),
    ("aliados", "Aliados e organizações"),
    ("tesouro", "Tesouro"),
    ("notas", "Anotações do Mestre"),
]
NIVEIS_MAGIA = list(range(1, 10))


# --------------------------------------------------------------------------
# Cálculos
# --------------------------------------------------------------------------

def _int(valor, padrao=None):
    try:
        return int(str(valor).strip().replace("+", ""))
    except (TypeError, ValueError):
        return padrao


def modificador(valor) -> int | None:
    v = _int(valor)
    return None if v is None else (v - 10) // 2


def com_sinal(n: int | None) -> str:
    return "—" if n is None else (f"+{n}" if n >= 0 else f"−{abs(n)}")


def bonus_proficiencia(nivel) -> int:
    """+2 nos níveis 1–4, +3 nos 5–8, +4 nos 9–12, +5 nos 13–16, +6 nos 17–20."""
    n = max(1, min(20, _int(nivel, 1)))
    return 2 + (n - 1) // 4


def calcular(ficha: dict) -> dict:
    """Valores derivados da ficha."""
    atributos = ficha.get("atributos") or {}
    mods = {a: modificador(atributos.get(a)) for a, _ in ATRIBUTOS}
    prof = bonus_proficiencia(ficha.get("nivel"))
    resist_prof = set(ficha.get("resistencias") or [])
    pericias_nivel = ficha.get("pericias") or {}

    resistencias = {
        a: (None if mods[a] is None else mods[a] + (prof if a in resist_prof else 0)) for a, _ in ATRIBUTOS
    }
    pericias = {}
    for chave, _, atr in PERICIAS:
        nivel_prof = _int(pericias_nivel.get(chave), 0)
        pericias[chave] = None if mods[atr] is None else mods[atr] + prof * nivel_prof

    percepcao = pericias.get("percepcao")
    iniciativa = None if mods["des"] is None else mods["des"] + _int(ficha.get("iniciativa_bonus"), 0)

    magia = ficha.get("magia") or {}
    atr_magia = magia.get("atributo")
    cd = ataque = None
    if atr_magia in mods and mods[atr_magia] is not None:
        cd = 8 + prof + mods[atr_magia]
        ataque = prof + mods[atr_magia]

    return {
        "mods": mods,
        "prof": prof,
        "resistencias": resistencias,
        "pericias": pericias,
        "percepcao_passiva": None if percepcao is None else 10 + percepcao,
        "iniciativa": iniciativa,
        "cd_magia": cd,
        "ataque_magia": ataque,
    }


# --------------------------------------------------------------------------
# Formulário do Painel <-> dados
# --------------------------------------------------------------------------

def _linhas(texto: str) -> list[str]:
    return [l.strip() for l in (texto or "").splitlines() if l.strip()]


def de_formulario(pegar) -> dict:
    """Monta a ficha a partir de um formulário. `pegar(nome)` devolve o valor do campo (ou "")."""
    def campo(nome):
        return (pegar(f"f5e_{nome}") or "").strip()

    ficha: dict = {}
    for chave, _ in CAMPOS_IDENTIDADE + CAMPOS_COMBATE:
        if campo(chave):
            ficha[chave] = campo(chave)
    for chave in ("nivel", "xp", "ca", "pv_max", "pv_atual", "pv_temp", "iniciativa_bonus",
                  "dados_de_vida_gastos", "morte_sucessos", "morte_falhas"):
        if chave in ficha and _int(ficha[chave]) is not None:
            ficha[chave] = _int(ficha[chave])
    if campo("inspiracao"):
        ficha["inspiracao"] = True

    atributos = {a: _int(campo(f"atr_{a}")) for a, _ in ATRIBUTOS}
    if any(v is not None for v in atributos.values()):
        ficha["atributos"] = {a: v for a, v in atributos.items() if v is not None}
    resistencias = [a for a, _ in ATRIBUTOS if campo(f"res_{a}")]
    if resistencias:
        ficha["resistencias"] = resistencias
    pericias = {chave: _int(campo(f"per_{chave}"), 0) for chave, _, _ in PERICIAS}
    pericias = {k: v for k, v in pericias.items() if v}
    if pericias:
        ficha["pericias"] = pericias

    proficiencias = {chave: campo(f"prof_{chave}") for chave, _ in CAMPOS_PROFICIENCIAS if campo(f"prof_{chave}")}
    if proficiencias:
        ficha["proficiencias"] = proficiencias

    ataques = []
    for linha in _linhas(pegar("f5e_ataques")):
        partes = [p.strip() for p in linha.split("|")]
        partes += [""] * (4 - len(partes))
        ataques.append({"nome": partes[0], "bonus": partes[1], "dano": partes[2], "notas": " | ".join(partes[3:]).strip(" |")})
    if ataques:
        ficha["ataques"] = ataques

    equipamento = _linhas(pegar("f5e_equipamento"))
    if equipamento:
        ficha["equipamento"] = equipamento
    moedas = {m: _int(campo(f"moeda_{m}")) for m, _ in MOEDAS}
    moedas = {m: v for m, v in moedas.items() if v}
    if moedas:
        ficha["moedas"] = moedas

    magia: dict = {}
    for chave in ("classe", "atributo"):
        if campo(f"magia_{chave}"):
            magia[chave] = campo(f"magia_{chave}")
    truques = _linhas(pegar("f5e_magia_truques"))
    if truques:
        magia["truques"] = truques
    niveis = {}
    for n in NIVEIS_MAGIA:
        espacos = _int(campo(f"magia_espacos_{n}"))
        usados = _int(campo(f"magia_usados_{n}"))
        lista = _linhas(pegar(f"f5e_magia_lista_{n}"))
        if espacos or usados or lista:
            item = {}
            if espacos:
                item["espacos"] = espacos
            if usados:
                item["usados"] = usados
            if lista:
                item["magias"] = lista
            niveis[n] = item
    if niveis:
        magia["niveis"] = niveis
    if magia:
        ficha["magia"] = magia

    for chave, _ in CAMPOS_PERSONALIDADE + CAMPOS_DETALHES_CURTOS + CAMPOS_TEXTOS_LONGOS:
        valor = (pegar(f"f5e_{chave}") or "").strip()
        if valor:
            ficha[chave] = valor
    return ficha


def para_formulario(ficha: dict | None) -> dict:
    """Valores planos (nome do campo -> texto) para preencher o formulário do Painel."""
    ficha = ficha or {}
    v: dict = {}
    for chave, _ in CAMPOS_IDENTIDADE + CAMPOS_COMBATE:
        if ficha.get(chave) not in (None, ""):
            v[f"f5e_{chave}"] = str(ficha[chave])
    if ficha.get("inspiracao"):
        v["f5e_inspiracao"] = "1"
    for a, valor in (ficha.get("atributos") or {}).items():
        v[f"f5e_atr_{a}"] = str(valor)
    for a in ficha.get("resistencias") or []:
        v[f"f5e_res_{a}"] = "1"
    for chave, nivel in (ficha.get("pericias") or {}).items():
        v[f"f5e_per_{chave}"] = str(nivel)
    for chave, valor in (ficha.get("proficiencias") or {}).items():
        v[f"f5e_prof_{chave}"] = valor
    v["f5e_ataques"] = "\n".join(
        " | ".join(x for x in (a.get("nome", ""), a.get("bonus", ""), a.get("dano", ""), a.get("notas", "")))
        .rstrip(" |") for a in ficha.get("ataques") or []
    )
    v["f5e_equipamento"] = "\n".join(ficha.get("equipamento") or [])
    for m, valor in (ficha.get("moedas") or {}).items():
        v[f"f5e_moeda_{m}"] = str(valor)
    magia = ficha.get("magia") or {}
    for chave in ("classe", "atributo"):
        if magia.get(chave):
            v[f"f5e_magia_{chave}"] = magia[chave]
    v["f5e_magia_truques"] = "\n".join(magia.get("truques") or [])
    for n, item in (magia.get("niveis") or {}).items():
        if item.get("espacos"):
            v[f"f5e_magia_espacos_{n}"] = str(item["espacos"])
        if item.get("usados"):
            v[f"f5e_magia_usados_{n}"] = str(item["usados"])
        v[f"f5e_magia_lista_{n}"] = "\n".join(item.get("magias") or [])
    for chave, _ in CAMPOS_PERSONALIDADE + CAMPOS_DETALHES_CURTOS + CAMPOS_TEXTOS_LONGOS:
        if ficha.get(chave):
            v[f"f5e_{chave}"] = ficha[chave]
    return v


# --------------------------------------------------------------------------
# Exibição no site (seção "## Ficha de personagem" da página do NPC)
# --------------------------------------------------------------------------

def _e(texto) -> str:
    return html.escape(str(texto))


def _caixa(rotulo: str, valor, classe: str = "") -> str:
    return (f'<div class="f5e-caixa {classe}"><span class="f5e-valor">{_e(valor)}</span>'
            f'<span class="f5e-rotulo">{_e(rotulo)}</span></div>')


def _marcador(nivel: int) -> str:
    return {0: "○", 1: "●", 2: "◆"}.get(nivel, "●")


def _bloco_texto(titulo: str, texto: str) -> list[str]:
    return ["", f"### {titulo}", "", texto.strip(), ""]


def renderizar(ficha: dict) -> str:
    """Markdown (com HTML) da seção da ficha. Seções vazias são omitidas."""
    c = calcular(ficha)
    atributos = ficha.get("atributos") or {}
    partes = ["## Ficha de personagem", ""]

    # Identidade e combate
    nivel = ficha.get("nivel")
    classe = ficha.get("classe", "")
    classe_nivel = " ".join(x for x in (str(classe), f"nível {nivel}" if nivel else "") if x) or "—"
    topo = [
        _caixa("Classe e nível", classe_nivel, "f5e-larga"),
        _caixa("Raça", ficha.get("raca") or "—"),
        _caixa("Antecedente", ficha.get("antecedente") or "—"),
        _caixa("Alinhamento", ficha.get("alinhamento") or "—"),
        _caixa("Experiência", ficha.get("xp") if ficha.get("xp") not in (None, "") else "—"),
        _caixa("Bônus de proficiência", com_sinal(c["prof"])),
        _caixa("Inspiração", "Sim" if ficha.get("inspiracao") else "Não"),
    ]
    pv = ficha.get("pv_max")
    pv_texto = "—" if pv in (None, "") else f"{ficha.get('pv_atual', pv)} / {pv}"
    if ficha.get("pv_temp"):
        pv_texto += f" (+{ficha['pv_temp']} temp.)"
    dados = ficha.get("dados_de_vida") or "—"
    if ficha.get("dados_de_vida_gastos"):
        dados += f" ({ficha['dados_de_vida_gastos']} gastos)"
    morte = (f"✓ {_int(ficha.get('morte_sucessos'), 0)}/3 · ✗ {_int(ficha.get('morte_falhas'), 0)}/3")
    ca = ficha.get("ca") if ficha.get("ca") not in (None, "") else "—"
    combate = [
        _caixa("Classe de Armadura", ca, "f5e-destaque"),
        _caixa("Iniciativa", com_sinal(c["iniciativa"]), "f5e-destaque"),
        _caixa("Deslocamento", ficha.get("deslocamento") or "—", "f5e-destaque"),
        _caixa("Pontos de vida", pv_texto, "f5e-destaque f5e-larga"),
        _caixa("Dados de vida", dados),
        _caixa("Testes contra a morte", morte),
        _caixa("Percepção passiva", c["percepcao_passiva"] if c["percepcao_passiva"] is not None else "—"),
    ]
    html_partes = [
        '<div class="f5e">',
        '<div class="f5e-grade f5e-topo">' + "".join(topo) + "</div>",
        '<div class="f5e-grade f5e-combate">' + "".join(combate) + "</div>",
    ]
    if ficha.get("ca_detalhe"):
        html_partes.append(f'<p class="f5e-nota">CA: {_e(ficha["ca_detalhe"])}</p>')

    # Atributos
    caixas_atr = []
    for a, nome in ATRIBUTOS:
        valor = atributos.get(a)
        caixas_atr.append(
            f'<div class="f5e-atributo"><span class="f5e-rotulo">{_e(nome)}</span>'
            f'<span class="f5e-mod">{com_sinal(c["mods"][a])}</span>'
            f'<span class="f5e-pontos">{_e(valor if valor is not None else "—")}</span></div>'
        )
    html_partes.append('<div class="f5e-atributos">' + "".join(caixas_atr) + "</div>")

    # Testes de resistência e perícias
    resist_prof = set(ficha.get("resistencias") or [])
    linhas_res = "".join(
        f'<li><span class="f5e-marca">{_marcador(1 if a in resist_prof else 0)}</span>'
        f'<span class="f5e-bonus">{com_sinal(c["resistencias"][a])}</span>{_e(nome)}</li>'
        for a, nome in ATRIBUTOS
    )
    pericias_nivel = ficha.get("pericias") or {}
    linhas_per = "".join(
        f'<li><span class="f5e-marca">{_marcador(_int(pericias_nivel.get(chave), 0))}</span>'
        f'<span class="f5e-bonus">{com_sinal(c["pericias"][chave])}</span>{_e(nome)} '
        f'<span class="f5e-sigla">({SIGLAS[atr]})</span></li>'
        for chave, nome, atr in PERICIAS
    )
    html_partes.append(
        '<div class="f5e-colunas">'
        f'<div class="f5e-lista"><h4>Testes de resistência</h4><ul>{linhas_res}</ul></div>'
        f'<div class="f5e-lista"><h4>Perícias</h4><ul>{linhas_per}</ul>'
        '<p class="f5e-nota">○ sem proficiência · ● proficiente · ◆ especialização</p></div>'
        "</div>"
    )
    html_partes.append("</div>")
    partes += ["\n".join(html_partes), ""]

    # Proficiências e idiomas
    profs = ficha.get("proficiencias") or {}
    if profs:
        partes += ["", "### Outras proficiências e idiomas", ""]
        partes += [f"- **{rotulo}:** {profs[chave]}" for chave, rotulo in CAMPOS_PROFICIENCIAS if profs.get(chave)]
        partes.append("")

    # Ataques
    ataques = ficha.get("ataques") or []
    if ataques:
        partes += ["", "### Ataques", "", "| Ataque | Bônus | Dano / tipo | Notas |", "|---|---|---|---|"]
        for a in ataques:
            celulas = [str(a.get(k) or "—").replace("|", "\\|") for k in ("nome", "bonus", "dano", "notas")]
            partes.append("| " + " | ".join(celulas) + " |")
        partes.append("")

    # Magias
    magia = ficha.get("magia") or {}
    if magia:
        atr = magia.get("atributo")
        cab = [
            f"**Classe conjuradora:** {magia.get('classe') or '—'}",
            f"**Atributo:** {dict(ATRIBUTOS).get(atr, '—')}",
            f"**CD de resistência:** {c['cd_magia'] if c['cd_magia'] is not None else '—'}",
            f"**Ataque mágico:** {com_sinal(c['ataque_magia'])}",
        ]
        partes += ["", "### Magias", "", " · ".join(cab), ""]
        if magia.get("truques"):
            partes += ["**Truques:** " + ", ".join(magia["truques"]), ""]
        for n, item in sorted((magia.get("niveis") or {}).items(), key=lambda x: int(x[0])):
            espacos = item.get("espacos")
            usados = item.get("usados", 0)
            info = f" — espaços: {espacos - usados} de {espacos} disponíveis" if espacos else ""
            lista = ", ".join(item.get("magias") or []) or "—"
            partes += [f"**{n}º nível{info}:** {lista}", ""]

    # Equipamento
    equipamento = ficha.get("equipamento") or []
    moedas = ficha.get("moedas") or {}
    if equipamento or moedas:
        partes += ["", "### Equipamento", ""]
        partes += [f"- {item}" for item in equipamento]
        if moedas:
            partes += ["", "**Moedas:** " + " · ".join(f"{moedas[m]} {s}" for m, s in MOEDAS if moedas.get(m))]
        partes.append("")

    # Personalidade
    pers = [(r, ficha[c_]) for c_, r in CAMPOS_PERSONALIDADE if ficha.get(c_)]
    if pers:
        partes += ["", "### Personalidade", ""]
        partes += [f"- **{r}:** {t}" for r, t in pers]
        partes.append("")

    detalhes = [(r, ficha[c_]) for c_, r in CAMPOS_DETALHES_CURTOS if ficha.get(c_)]
    if detalhes:
        partes += ["", "### Detalhes", "", " · ".join(f"**{r}:** {t}" for r, t in detalhes), ""]

    for chave, rotulo in CAMPOS_TEXTOS_LONGOS:
        if ficha.get(chave):
            partes += _bloco_texto(rotulo, ficha[chave])

    return "\n".join(partes) + "\n"


def tem_ficha(ficha) -> bool:
    return isinstance(ficha, dict) and bool(ficha)


def resumo_nivel(ficha) -> str:
    """Texto curto para a coluna "Nível" da tabela de NPCs."""
    if not tem_ficha(ficha) or not ficha.get("nivel"):
        return "—"
    return str(ficha["nivel"])

