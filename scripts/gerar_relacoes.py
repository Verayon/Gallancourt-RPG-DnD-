#!/usr/bin/env python3
"""Gera as páginas de relações da wiki e injeta os resumos nas cidades e personagens.

Fonte única dos dados de relações. Para alterar uma relação entre cidades ou uma intriga
entre nobres, edite as listas PARES e INTRIGAS abaixo e rode, a partir da raiz do projeto:

    python3 scripts/gerar_relacoes.py

O script:
  - reescreve docs/mundo/relacoes-entre-cidades.md e docs/mundo/intrigas-da-nobreza.md;
  - atualiza a seção "Relações com outras cidades" de cada página em docs/cidades/;
  - atualiza a seção "Intrigas" de cada página em docs/personagens/.

As seções injetadas ficam entre marcadores <!-- inicio:gerado --> e <!-- fim:gerado -->.
Não edite o conteúdo entre esses marcadores à mão: ele é sobrescrito a cada execução.
Rodar o script várias vezes produz sempre o mesmo resultado.
"""
import re
from pathlib import Path

D = str(Path(__file__).resolve().parent.parent / 'docs')
INICIO, FIM = '<!-- inicio:gerado -->', '<!-- fim:gerado -->'
CID = {'valynesse': 'Valynesse', 'dodixie': 'Dodixie', 'baie-de-l-eclair': "Baie de l'Éclair",
       'saint-armand': 'Saint-Armand', 'nouvelle-montagne': 'Nouvelle-Montagne'}
ESTADOS = [
 ('Aliado', '🟢', 'Relação positiva e dependência assumida.', '#2e7d32'),
 ('Cordial', '🔵', 'Cooperação real, com atritos administráveis.', '#0277bd'),
 ('Neutro', '⚪', 'Contato pragmático, sem afeto nem hostilidade.', '#9e9e9e'),
 ('Tenso', '🟠', 'Negócios em comum sobre ressentimento real.', '#ef6c00'),
 ('Hostil velado', '🟣', 'Medo e vigilância mútua por trás da cooperação formal.', '#6a1b9a'),
 ('Rivalidade aberta', '🔴', 'Disputa declarada por poder.', '#c62828'),
]
ICON = {e[0]: e[1] for e in ESTADOS}; COR = {e[0]: e[3] for e in ESTADOS}

# (a, b, estado, visão de a, visão de b, notas)
PARES = [
 ('valynesse', 'dodixie', 'Rivalidade aberta',
  'Rivalidade política e econômica. Dodixie, a cidade mais rica, deseja influenciar o governo central, e Valynesse resiste a essa interferência.',
  'Rivalidade aberta pelo controle do governo: Dodixie acredita que deveria ser a nova capital devido ao seu poder econômico, e seus aristocratas apoiam em segredo iniciativas para enfraquecer a capital.',
  ['Scyras Corbeau quer vingar o pai, traído por aristocratas da capital, e quebrar a hegemonia da velha nobreza.',
   'Camille Brissac é a face pública da campanha de Dodixie pela capital.',
   'O Leilão de Cristal (Valynesse) e o Leilão Real (Dodixie) mantêm uma rixa especial.']),
 ('valynesse', 'baie-de-l-eclair', 'Cordial',
  'Relação comercial saudável, mas com conflitos pelo controle das taxas marítimas.',
  'Relação comercial importante, mas instável, pelo controle das tarifas de importação e exportação.',
  []),
 ('valynesse', 'saint-armand', 'Hostil velado',
  'A capital teme o poder militar da cidade-fortaleza e mantém uma postura de vigilância constante.',
  'Relação delicada, pois a capital teme uma possível tomada de poder por Saint-Armand.',
  ['`SEGREDO` O medo tem fundamento: Armand Saint-Laurent sonda seus oficiais mais leais para um golpe contra a aristocracia.']),
 ('valynesse', 'nouvelle-montagne', 'Tenso',
  'Nouvelle-Montagne é uma importante fornecedora de alimentos para a capital.',
  'Fornece alimentos à capital, mas sofre com os tributos abusivos impostos pelos aristocratas de Valynesse.',
  []),
 ('dodixie', 'baie-de-l-eclair', 'Tenso',
  'Comércio forte, mas tensão com os piratas e corsários que perturbam as rotas. Dodixie se sente ameaçada pelo poderio naval de Baie, que pode atrapalhar sua expansão comercial marítima.',
  'Cooperação comercial mútua, mas descontentamento com o aumento da pirataria e com a tentativa de Dodixie de roubar parte das rotas comerciais.',
  ['`SEGREDO` Parte dessa pirataria é a frota de Rochefort, paga por Scyras Corbeau, que às vezes ataca navios de Dodixie para manter as aparências.']),
 ('dodixie', 'nouvelle-montagne', 'Neutro',
  'Relações comerciais neutras; os fazendeiros de Nouvelle-Montagne preferem negociar diretamente com Dodixie para evitar as taxas da capital.',
  'Relação comercial relativamente pacífica.',
  ['Dodixie conspira para se aliar a Nouvelle-Montagne, e o Chefe Pierre Montaigne defende um bloco com Dodixie.',
   '`SEGREDO` Élodie Vaucluse troca correspondência secreta com Camille Brissac.']),
 ('dodixie', 'saint-armand', 'Neutro',
  'Respeita a cidade militarizada, mas a considera uma possível ameaça caso decida intervir nas disputas políticas do reino.',
  'Respeito mútuo, mas os comerciantes de Dodixie temem que os militares interfiram na economia.',
  ['Pierre Montaigne quer as duas cidades num bloco com Nouvelle-Montagne.']),
 ('baie-de-l-eclair', 'nouvelle-montagne', 'Tenso',
  'Relação tensa, marcada pela extorsão nos preços de transporte de grãos e animais.',
  'Relação conflituosa: Baie de l\'Éclair impõe altas taxas de transporte e tenta controlar a economia da região.',
  ['`SEGREDO` Lucien de Saint-Pierre financia com a própria fortuna uma frota pirata contra os navios de Baie, para forçá-la a negociar.']),
 ('baie-de-l-eclair', 'saint-armand', 'Cordial',
  'Cooperam militarmente, mas existe tensão entre os almirantes de Baie e os generais de Saint-Armand sobre qual força deveria ser mais proeminente no reino.',
  'Cooperação militar, com uma disputa latente sobre a primazia naval do reino.',
  []),
 ('nouvelle-montagne', 'saint-armand', 'Aliado',
  'Relação positiva: fornece mantimentos aos soldados da cidade-fortaleza.',
  'Relação amigável: Saint-Armand depende dos suprimentos produzidos na região.',
  ['O pacto de alimento em troca de proteção nasceu no Massacre da Aurora Velada; a Intendente-Geral Juliette Clermont mantém a ligação.']),
]

P = {
 'scyras-corbeau': 'Scyras Corbeau', 'alaric-duvant': 'Alaric Duvant', 'alfonse-enry': 'Alfonse Enry',
 'thalin': 'Thalin', 'zepharion': 'Zepharion', 'camille-brissac': 'Camille Brissac',
 'jeanesse-lumiere': 'Jeanesse Lumière', 'elian-lumiere': 'Elian Lumière', 'jean-vigny': 'Jean Vigny',
 'louis-de-montclair': 'Louis de Montclair', 'etienne-rochefort': 'Étienne Rochefort',
 'helga-roche': 'Helga Roche', 'pierre-montaigne': 'Pierre Montaigne', 'elodie-vaucluse': 'Élodie Vaucluse',
 'lucien-de-saint-pierre': 'Lucien de Saint-Pierre', 'armand-saint-laurent': 'Armand Saint-Laurent',
 'juliette-clermont': 'Juliette Clermont', 'thibault-de-la-riviere': 'Thibault de la Rivière',
 'lorenzo-magneter': 'Lorenzo Magnetér', 'amelie-montpensier': 'Amélie Montpensier',
 'philippe-beaumont': 'Philippe Beaumont', 'henri-du-valois': 'Henri du Valois',
 'severin-marceau': 'Severin Marceau',
}
TIPOS = {'Aliança': '🤝', 'Cooperação e rivalidade': '⚖️', 'Rivalidade': '⚔️', 'Hostilidade': '🔥',
 'Conspiração de assassinato': '🗡️', 'Clandestina': '🕯️', 'Vigilância': '👁️', 'Mentor': '📜',
 'Traição': '🐍', 'Dependência': '🔗'}
INTRIGAS = [
 # ---- cânone
 ('scyras-corbeau', '↔', 'alaric-duvant', 'Cooperação e rivalidade', 'CANON', False,
  'Duvant reconhece a liderança de Corbeau, mas tem ambições próprias em Dodixie.'),
 ('scyras-corbeau', '↔', 'etienne-rochefort', 'Clandestina', 'CANON', True,
  'Scyras paga Rochefort com ouro e inteligência; ele ataca os navios de Vigny e, às vezes, os de Dodixie, para manter as aparências.'),
 ('etienne-rochefort', '→', 'jean-vigny', 'Hostilidade', 'CANON', False,
  'Vigny construiu sua frota sobre a ruína da linhagem de Rochefort. O corsário ataca seus navios para derrubá-lo e tomar seu lugar.'),
 ('jean-vigny', '↔', 'louis-de-montclair', 'Rivalidade', 'CANON', False,
  'Simbiose e desprezo: a imprudência de Vigny e os piratas garantem a demanda pelos navios de Louis, que despreza o Comodoro e busca em segredo outro patrono.'),
 ('scyras-corbeau', '↔', 'lorenzo-magneter', 'Rivalidade', 'CANON', False,
  'Dodixie quer ser a capital; Valynesse resiste. Scyras quer quebrar a hegemonia da velha nobreza e vingar o pai, traído por aristocratas da capital.'),
 ('armand-saint-laurent', '↔', 'lorenzo-magneter', 'Hostilidade', 'CANON', False,
  'A capital teme uma tomada de poder; Armand acredita que só um governo militar pode salvar o reino da aristocracia corrupta.'),
 ('juliette-clermont', '→', 'armand-saint-laurent', 'Vigilância', 'CANON', True,
  'Ciente das ambições de Armand, Juliette trabalha sutilmente para frustrar o golpe, temendo uma nova guerra civil.'),
 ('helga-roche', '↔', 'armand-saint-laurent', 'Dependência', 'CANON', False,
  'Alimento em troca de proteção, desde o Massacre da Aurora Velada.'),
 ('juliette-clermont', '↔', 'helga-roche', 'Aliança', 'CANON', False,
  'Juliette mantém a relação vital entre Saint-Armand e Nouvelle-Montagne.'),
 ('lorenzo-magneter', '↔', 'philippe-beaumont', 'Aliança', 'CANON', False,
  'Beaumont usa seus segredos para garantir a primazia de Valynesse; a subordinação formal à Casa Magnetér não é confirmada.'),
 ('alfonse-enry', '→', 'thalin', 'Mentor', 'CANON', False,
  'Alfonse treina e guia Thalin em sua jornada por vingança após o massacre dos Enry.'),
 ('alfonse-enry', '↔', 'scyras-corbeau', 'Aliança', 'CANON', False,
  'A família Enry é próxima da Maison Corbeau; Alfonse usa recursos da casa para ajudar Thalin.'),
 ('thibault-de-la-riviere', '→', 'severin-marceau', 'Traição', 'CANON', True,
  'Capturado em missão, aceitou poder e riqueza num "novo Gallancourt" purificado. Vaza informações, sabota patrulhas e fomenta desconfiança entre as cidades.'),
 ('thibault-de-la-riviere', '→', 'alfonse-enry', 'Traição', 'CANON', True,
  'Entregou a L\'Ordre a localização da mansão do irmão de Alfonse, massacrado com quase toda a família.'),
 ('jeanesse-lumiere', '↔', 'elian-lumiere', 'Rivalidade', 'CANON', False,
  'A aristocracia Lumière contra a autonomia da Torre do Trovão; os dois levam o mesmo nome de família.'),
 ('elodie-vaucluse', '↔', 'camille-brissac', 'Clandestina', 'CANON', True,
  'Correspondência secreta entre a líder radical de Nouvelle-Montagne e a face pública da campanha de Dodixie pela capital.'),
 ('elodie-vaucluse', '↔', 'pierre-montaigne', 'Rivalidade', 'CANON', False,
  'Facção radical contra facção pragmática no conselho de clãs: embargos de grãos contra um bloco com Dodixie e Saint-Armand.'),
 ('lucien-de-saint-pierre', '↔', 'etienne-rochefort', 'Rivalidade', 'CANON', False,
  'A frota pirata que Lucien financia é rival à de Rochefort.'),
 # ---- possibilidades
 ('jean-vigny', '→', 'etienne-rochefort', 'Conspiração de assassinato', 'POSSIBILIDADE', True,
  'O Comodoro, que governa pelo medo, contratou La Voile Noire para matar o corsário, sem saber que ele trabalha para Scyras.'),
 ('severin-marceau', '→', 'scyras-corbeau', 'Conspiração de assassinato', 'POSSIBILIDADE', True,
  'Para L\'Ordre, a frota de Dodixie é o maior poder naval inimigo. Matar a marquesa deixaria a marinha do norte sem cabeça.'),
 ('philippe-beaumont', '→', 'armand-saint-laurent', 'Vigilância', 'POSSIBILIDADE', True,
  'Beaumont, que sabe de quase todas as conspirações, conhece os planos de golpe e guarda a informação como moeda de troca.'),
 ('henri-du-valois', '→', 'armand-saint-laurent', 'Clandestina', 'POSSIBILIDADE', True,
  'Henri, que financia movimentos contra a opressão da elite, vê no golpe de Armand uma forma de derrubar a aristocracia corrupta.'),
 ('zepharion', '↔', 'alaric-duvant', 'Clandestina', 'POSSIBILIDADE', True,
  'Duvant usa La Voile Noire para desgastar os negócios de Corbeau sem sujar as próprias mãos.'),
 ('elodie-vaucluse', '↔', 'juliette-clermont', 'Rivalidade', 'POSSIBILIDADE', False,
  'Élodie ameaça com embargos de grãos; Juliette depende desse grão para alimentar o exército.'),
 ('amelie-montpensier', '↔', 'lorenzo-magneter', 'Aliança', 'POSSIBILIDADE', False,
  'O poder do Doge depende do ouro do cartel de mineração de Amélie; ela sabe disso e cobra caro.'),
 ('elian-lumiere', '↔', 'armand-saint-laurent', 'Hostilidade', 'POSSIBILIDADE', False,
  'Armand quer a Torre como arma; Elian vê a política como uma distração de suas tempestades.'),
 ('jeanesse-lumiere', '↔', 'lorenzo-magneter', 'Rivalidade', 'POSSIBILIDADE', False,
  'A disputa pelas taxas marítimas entre Baie de l\'Éclair e Valynesse passa pelos dois.'),
 ('alfonse-enry', '↔', 'philippe-beaumont', 'Aliança', 'POSSIBILIDADE', False,
  'Dois mestres da informação que podem trocar segredos sobre o massacre dos Enry.'),
]

def link(s, pre): return f'[{P[s]}]({pre}{s}.md)'
def clink(s, pre): return f'[{CID[s]}]({pre}{s}.md)'
def marca(m, s): return f'`{m}`' + (' `SEGREDO`' if s else '')

# ---------------- relações entre cidades
out = ['---', 'tags:', '  - Mundo', '  - Política', '  - Cidades', '---', '',
 '# Relações entre cidades', '',
 'Cada cidade tem um motivo para precisar e um motivo para desconfiar das outras. Esta página',
 'mostra como as cinco grandes cidades de Gallancourt se relacionam quando a campanha começa, com',
 'a **visão de cada lado**.', '',
 '!!! info "Fontes"',
 '    As visões de cada cidade vêm do documento *História de Gallancourt* (`CANON`). O estado de cada',
 '    par é um resumo dessas visões. Notas marcadas `SEGREDO` descrevem o que as cidades não sabem.', '',
 '## Escala de relação', '', '| Estado | Significado |', '|---|---|']
out += [f'| {i} **{n}** | {d} |' for n, i, d, _ in ESTADOS]
out += ['', '## Mapa de relações', '', '```mermaid', 'graph LR']
ids = {'valynesse': 'VAL', 'dodixie': 'DOD', 'baie-de-l-eclair': 'BAI', 'saint-armand': 'SAR', 'nouvelle-montagne': 'NMO'}
out += [f'    {i}["{CID[s]}"]' for s, i in ids.items()]
out += [f'    {ids[a]} ---|{e}| {ids[b]}' for a, b, e, *_ in PARES]
out += [f'    linkStyle {k} stroke:{COR[e]},stroke-width:3px' for k, (a, b, e, *_) in enumerate(PARES)]
out += ['```', '', '## Matriz', '']
est = {}
for a, b, e, *_ in PARES: est[(a, b)] = est[(b, a)] = e
ordem = list(CID)
out.append('| | ' + ' | '.join(CID[c] for c in ordem) + ' |')
out.append('|---' * (len(ordem) + 1) + '|')
for r in ordem:
    out.append(f'| **{clink(r, "../cidades/")}** | ' + ' | '.join('—' if r == c else f'{ICON[est[(r, c)]]} {est[(r, c)]}' for c in ordem) + ' |')
out += ['', '## Os dez pares', '']
for a, b, e, va, vb, notas in PARES:
    out += [f'### {CID[a]} × {CID[b]}', '', f'**Estado:** {ICON[e]} {e}', '', '| | |', '|---|---|',
            f'| **Visão de {CID[a]}** | {va} |', f'| **Visão de {CID[b]}** | {vb} |', '']
    out += [f'- {n}' for n in notas]
    if notas: out.append('')
out += ['## Relações com L\'Ordre de Célestien', '',
 'Todas as cidades de Gallancourt tratam L\'Ordre como inimigo. O que varia é a forma do contato:', '',
 '| Lado de Gallancourt | Contato com L\'Ordre |', '|---|---|',
 '| Saint-Armand | Principal linha de defesa; a Patrulha da Fronteira vigia a Cicatriz — sob o comando de um traidor `SEGREDO` |',
 '| Valynesse | O Santuário do Sol Velado guarda a velha fé, que pode ajudar contra L\'Ordre; as redes de Beaumont vigiam o leste |',
 '| Dodixie | L\'Ordre já agiu nos arredores da cidade: o massacre da família Enry `SEGREDO` |',
 '| Baie de l\'Éclair | A Magocracia e a diversidade cosmopolita da cidade são tudo o que a doutrina da pureza rejeita |',
 '| Nouvelle-Montagne | O celeiro foi o primeiro grande alvo da Coroa durante a guerra |',
 '', 'Ver também: [Intrigas da nobreza](intrigas-da-nobreza.md) · [Teia política](teia-politica.md) ·',
 '[Economia política](economia.md).', '']
open(f'{D}/mundo/relacoes-entre-cidades.md', 'w', encoding='utf-8').write('\n'.join(out))

# ---------------- intrigas da nobreza
out = ['---', 'tags:', '  - Mundo', '  - Política', '  - Personagens', '---', '',
 '# Intrigas da nobreza', '',
 'Quem é aliado de quem, quem vigia quem e quem quer quem morto. Relações `CANON` vêm das fontes',
 '(dossiê e *História de Gallancourt*); relações `POSSIBILIDADE` são propostas para o autor aprovar',
 'ou descartar. `SEGREDO` indica o que os personagens do mundo, em geral, não sabem.', '',
 '## Legenda', '', '| Tipo | Ícone |', '|---|---|']
out += [f'| {t} | {i} |' for t, i in TIPOS.items()]
out += ['', '## Mapa de intrigas', '', '!!! tip "Leitura do diagrama"',
        '    Linhas cheias são cânone; linhas tracejadas são possibilidades. Setas indicam relações de mão',
        '    única. Linhas vermelhas são conspirações de assassinato.', '', '```mermaid', 'graph LR']
nid = {s: f'P{k}' for k, s in enumerate(P)}
usados = {x for i in INTRIGAS for x in (i[0], i[2])}
grupos = [
 ('Valynesse', ['lorenzo-magneter', 'amelie-montpensier', 'philippe-beaumont', 'henri-du-valois']),
 ('Dodixie', ['scyras-corbeau', 'alaric-duvant', 'alfonse-enry', 'thalin', 'zepharion', 'camille-brissac']),
 ("Baie de l'Éclair", ['jeanesse-lumiere', 'elian-lumiere', 'jean-vigny', 'louis-de-montclair', 'etienne-rochefort']),
 ('Saint-Armand', ['armand-saint-laurent', 'juliette-clermont', 'thibault-de-la-riviere']),
 ('Nouvelle-Montagne', ['helga-roche', 'pierre-montaigne', 'elodie-vaucluse', 'lucien-de-saint-pierre']),
 ("L'Ordre", ['severin-marceau']),
]
for k, (g, ms) in enumerate(grupos):
    out.append(f'    subgraph G{k}["{g}"]')
    out += [f'        {nid[m]}["{P[m]}"]' for m in ms if m in usados]
    out.append('    end')
for a, d, b, t, m, s, _ in INTRIGAS:
    arrow = ('-->' if d == '→' else '---') if m == 'CANON' else ('-.->' if d == '→' else '-.-')
    out.append(f'    {nid[a]} {arrow}|{TIPOS[t]}| {nid[b]}')
for k, i in enumerate(INTRIGAS):
    if i[3] == 'Conspiração de assassinato':
        out.append(f'    linkStyle {k} stroke:#c62828,stroke-width:3px')
out += ['```', '', '## Segredos em jogo', '']
for a, d, b, t, m, s, desc in INTRIGAS:
    if s:
        out.append(f'- {TIPOS[t]} **{link(a, "../personagens/")} {d} {link(b, "../personagens/")}** {marca(m, s)}: {desc}')
out += ['', '## Todas as relações', '', '| De | | Para | Tipo | Marca | Descrição |', '|---|---|---|---|---|---|']
for a, d, b, t, m, s, desc in INTRIGAS:
    out.append(f'| {link(a, "../personagens/")} | {d} | {link(b, "../personagens/")} | {TIPOS[t]} {t} | {marca(m, s)} | {desc} |')
out += ['', '## Relações entre as casas', '',
 'Tom geral entre as famílias, derivado das relações entre as cidades.', '',
 '| | Magnetér | Corbeau | Lumière | Saint-Laurent | Roche | Duvant |', '|---|---|---|---|---|---|---|',
 '| **[Magnetér](../faccoes/casa-magneter.md)** | — | 🔴 Rivalidade aberta | 🔵 Cordial | 🟣 Hostil velado | 🟠 Tenso | ⚪ Neutro |',
 '| **[Corbeau](../faccoes/casa-corbeau.md)** | 🔴 Rivalidade aberta | — | 🟠 Tenso | ⚪ Neutro | ⚪ Neutro, em aproximação | ⚖️ Cooperação e rivalidade |',
 '| **[Lumière](../faccoes/casa-lumiere.md)** | 🔵 Cordial | 🟠 Tenso | — | 🔵 Cordial | 🟠 Tenso | ⚪ Neutro |',
 '| **[Saint-Laurent](../faccoes/casa-saint-laurent.md)** | 🟣 Hostil velado | ⚪ Neutro | 🔵 Cordial | — | 🟢 Aliado | ⚪ Neutro |',
 '| **[Roche](../faccoes/casa-roche.md)** | 🟠 Tenso | ⚪ Neutro, em aproximação | 🟠 Tenso | 🟢 Aliado | — | ⚪ Neutro |',
 '| **[Duvant](../faccoes/casa-duvant.md)** | ⚪ Neutro | ⚖️ Cooperação e rivalidade | ⚪ Neutro | ⚪ Neutro | ⚪ Neutro | — |',
 '', '!!! question "Em aberto"',
 '    Cada `POSSIBILIDADE` acima é uma escolha do autor. Ao confirmar uma delas, troque a marca por',
 '    `CANON` aqui e na página do personagem.', '']
open(f'{D}/mundo/intrigas-da-nobreza.md', 'w', encoding='utf-8').write('\n'.join(out))

# ---------------- injeção
def inserir(path, bloco):
    """Substitui o bloco gerado anterior ou o insere antes do último "Em aberto"."""
    s = open(path, encoding='utf-8').read()
    bloco = f'{INICIO}\n{bloco.rstrip()}\n{FIM}\n'
    if INICIO in s:
        s = re.sub(re.escape(INICIO) + r'.*?' + re.escape(FIM) + r'\n', lambda m: bloco, s, flags=re.S)
    else:
        i = s.rfind('\n!!! question "Em aberto"')
        s = s[:i] + '\n' + bloco + s[i:] if i != -1 else s.rstrip('\n') + '\n\n' + bloco
    open(path, 'w', encoding='utf-8').write(s)

for c in CID:
    L = ['## Relações com outras cidades', '', '| Cidade | Estado | Como esta cidade a vê | Como ela vê esta cidade |', '|---|---|---|---|']
    for a, b, e, va, vb, n in PARES:
        if c in (a, b):
            o, minha, dela = (b, va, vb) if c == a else (a, vb, va)
            L.append(f'| {clink(o, "")} | {ICON[e]} {e} | {minha} | {dela} |')
    L += ['', 'Notas e segredos de cada par em [Relações entre cidades](../mundo/relacoes-entre-cidades.md).', '']
    inserir(f'{D}/cidades/{c}.md', '\n'.join(L))

for slug in P:
    rel = [i for i in INTRIGAS if slug in (i[0], i[2])]
    if not rel: continue
    L = ['## Intrigas', '', '| Com | Tipo | Marca | Descrição |', '|---|---|---|---|']
    for a, d, b, t, m, s, desc in rel:
        outro = b if a == slug else a
        seta = '↔ ' if d == '↔' else ('→ ' if a == slug else '← ')
        L.append(f'| {seta}{link(outro, "")} | {TIPOS[t]} {t} | {marca(m, s)} | {desc} |')
    L += ['', '→ este personagem age sobre o outro; ← o outro age sobre este personagem.', '',
          'Ver o mapa completo em [Intrigas da nobreza](../mundo/intrigas-da-nobreza.md).', '']
    inserir(f'{D}/personagens/{slug}.md', '\n'.join(L))
print('Relações geradas.')
