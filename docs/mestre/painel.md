---
tags:
  - Mestre
  - Diário
---

# Painel do Mestre

Uma ferramenta local, separada do site, para registrar sessões e editar páginas **sem mexer em
arquivo nenhum à mão**. Ela roda no seu computador, ao lado do site (que continua em
`http://127.0.0.1:8000`), e escreve diretamente nos arquivos de `docs/`. Como o `mkdocs serve` fica
de olho nessa pasta, assim que o painel salva alguma coisa, o site se atualiza sozinho.

!!! warning "Ferramenta só sua"
    O painel não tem senha nem login — quem tiver acesso ao seu computador e souber o endereço
    consegue editar o site por ele. Ele só escuta `127.0.0.1` (não aparece para outros aparelhos da
    rede), então isso é seguro enquanto for só você usando, na sua própria máquina.

## Como abrir

Dentro da pasta do projeto:

```bash
.venv\Scripts\python admin\app.py
```

Ou, no Windows, dê duplo clique em `admin/iniciar-painel.bat`. Depois, abra
**http://127.0.0.1:5001/** no navegador. Deixe essa janela do terminal aberta enquanto usa o
painel — fechá-la desliga a ferramenta (o site em si continua no ar, servido pelo `mkdocs serve`).

## Adicionar um NPC

Na página [NPCs](../personagens/index.md), o botão **Adicionar NPC** abre esta aba (ou acesse
`http://127.0.0.1:5001/npc/novo`). Preencha o que já souber — só o nome é obrigatório: título,
raça, cidade, afiliação, um resumo de uma linha, a descrição e, se quiser, o retrato. Ao clicar em
**Criar NPC**, o painel:

1. cria `docs/personagens/<nome>.md` no padrão das outras páginas de NPC (caixa com retrato e
   dados rápidos, abas abaixo);
2. coloca o NPC no menu, em **Wiki → NPCs**, dentro do grupo da cidade (ou em **Outros**, se a
   cidade não tiver grupo);
3. confere o site com `mkdocs build --strict`.

O NPC aparece sozinho na tabela de NPCs. Para trocar ou adicionar o retrato de um NPC que já
existe, use **Trocar o retrato de um NPC existente** (`/npc/retrato`).

## Criar uma sessão nova

Em [Mestre → Sessões](sessoes/index.md), o botão **Nova sessão** abre esta aba (ou acesse
`http://127.0.0.1:5001/sessoes/nova`). Informe o número e o título — o resto é opcional: resumo
rápido, jogadores, nível, duração, tom, local, missão e recompensa. O painel cria a página de
preparação com o mesmo layout da Sessão 0 (ficha no topo e as abas Resumo, NPCs, Cenas,
Loot & Pistas, Lugares e Segredo do Mestre), adiciona-a ao menu em **Mestre → Sessões** e confere o
site. A sessão aparece sozinha na lista de sessões.

Essa é a página de **preparação**. Depois de jogar, registre o que aconteceu em
**Registrar sessão** (abaixo), que alimenta o [Diário de Sessões](../diario/index.md).

## Registrar uma sessão

Na aba inicial:

1. Marque os **NPCs** e as **cidades** (ou outros lugares) que participaram da sessão.
2. Ao lado de cada um, um campo opcional deixa anotar algo específico que aconteceu com aquele
   personagem ou lugar — por exemplo, ao lado de "Scyras Corbeau": *"revelou seu acordo secreto com
   Rochefort a um dos jogadores"*. Se deixar em branco, entra um texto genérico.
3. Preencha a data real, a data na campanha, um título curto e o resumo da sessão.
4. Clique em **Aplicar**.

O painel então:

- cria `docs/diario/sessao-NN.md` com a ficha, o resumo e a lista de atualizações;
- liga a sessão anterior a essa, no rodapé de cada uma ("Anterior" / "Próxima");
- adiciona uma linha em [Sessões registradas](../diario/index.md#sessoes-registradas) e um marco na
  linha do tempo;
- cria um acontecimento na [Linha do tempo](linha-do-tempo.md) com o resumo da sessão e a nota de
  cada NPC e lugar marcado — ele aparece na aba **Linha do tempo** de cada um, em ordem cronológica;
- registra a página nova no menu do site (`mkdocs.yml`);
- roda `mkdocs build --strict` para conferir que nada quebrou, e mostra o resultado na tela.

Na tela de resultado, o botão **Registrar mudanças desta sessão** abre esse acontecimento na aba
Linha do tempo, para você marcar quem morreu, quem mudou de cidade etc. (veja abaixo).

Se alguma coisa der errado (por exemplo, o build falhar), o painel mostra o erro em vez de deixar o
site quebrado em silêncio — nesse caso, nada é revertido automaticamente, então corrija o problema
apontado (ou peça para o Claude Code corrigir) antes de rodar o `mkdocs build --strict` de novo.

## Ficha de personagem do NPC (D&D 5e)

Na aba **Ficha de NPC** (ou marcando **Criar também a ficha de personagem** ao adicionar um NPC),
preencha a ficha completa no modelo da ficha oficial de D&D 5e:

| Bloco | Campos |
|---|---|
| Identidade | Classe (e subclasse), nível, raça, antecedente, alinhamento, experiência, inspiração |
| Atributos | Força, Destreza, Constituição, Inteligência, Sabedoria e Carisma, e em quais testes de resistência o NPC é proficiente |
| Perícias | As 18 perícias, cada uma sem proficiência, proficiente ou com especialização |
| Combate | CA (e de onde vem), bônus de iniciativa, deslocamento, PV máximos/atuais/temporários, dados de vida, testes contra a morte e ataques (um por linha: nome, bônus, dano e tipo e notas, separados por barras verticais) |
| Proficiências | Armaduras, armas, ferramentas e idiomas |
| Equipamento | Itens (um por linha) e moedas (PC, PP, PE, PO, PL) |
| Magias | Classe conjuradora, atributo de conjuração, truques, espaços e espaços usados por nível e as magias de cada nível |
| Personagem | Traços de personalidade, ideais, vínculos, defeitos, idade, altura, peso, olhos, pele, cabelo, aparência, história, aliados e organizações, tesouro e anotações do Mestre |

Só os valores digitados são guardados (no bloco `ficha5e:` do topo da página do NPC). O site
calcula sozinho os **modificadores**, o **bônus de proficiência** pelo nível (+2 nos níveis 1–4, +3
nos 5–8, +4 nos 9–12, +5 nos 13–16, +6 nos 17–20), os **testes de resistência**, as **perícias**
(especialização dobra a proficiência), a **percepção passiva** (10 + Percepção), a **iniciativa**, a
**CD de magia** (8 + proficiência + modificador) e o **ataque mágico** (proficiência + modificador).
O formulário mostra esses números enquanto você digita.

A ficha aparece na aba **Ficha de personagem** da página do NPC, e o nível passa a aparecer na
tabela de NPCs. Para acompanhar o NPC ao longo da campanha — PV atuais, espaços de magia gastos,
itens ganhos ou perdidos —, é só voltar à aba e salvar de novo.

## Linha do tempo: o que mudou com cada NPC, cidade e facção

Na aba **Linha do tempo**, registre um acontecimento: data na campanha (no formato
`3 de março de 1453`), número da sessão (opcional), título, descrição, quem está envolvido e,
opcionalmente, **mudanças de estado**:

| Mudança | Vale para | Efeito no site |
|---|---|---|
| Situação (ex.: *Morto*, *Desaparecido*, *Preso*; para cidades, *Sob cerco*) | NPCs, cidades, facções | NPC: linha "Situação atual" na caixa do topo e coluna Situação da tabela. Cidade/facção: caixa "Situação atual" no topo da página |
| Localização (ex.: *Valynesse*) | NPCs | Linha "Localização atual" na caixa do topo; coluna Cidade da tabela |
| Afiliação | NPCs | Linha "Afiliação atual"; coluna Afiliação da tabela |
| Título | NPCs | Linha "Título atual"; coluna Título da tabela |

Cada acontecimento aparece na aba (ou seção) **Linha do tempo** de cada página envolvida e na página
[Mestre → Linha do tempo](linha-do-tempo.md), sempre em **ordem cronológica pela data na
campanha** — não pela ordem em que você registrou. Sem data, vale o número da sessão. Quando um
campo muda mais de uma vez, vale a mudança mais recente na cronologia.

Na lista abaixo do formulário dá para **editar** ou **apagar** qualquer acontecimento. Os dados
ficam em `dados/linha-do-tempo.yml`.

## Preencher a ficha de uma cidade

Na aba **Ficha de cidade**, escolha a cidade e preencha os campos. Ao salvar, o painel cria (ou
substitui) a seção **Ficha da cidade** no rodapé da página.

| Campo | O que colocar |
|---|---|
| População | Uma estimativa, mesmo que aproximada |
| Defesas e guarnição | Muralhas, guarda, frota, o que protege o lugar |

!!! warning "Salvar substitui a seção inteira"
    Cada vez que você salva a ficha de uma cidade, o painel **reescreve a seção inteira** com os
    valores atuais dos campos. Se você tiver escrito algo à mão nessa seção pelo editor genérico,
    fora desses campos, aquele texto some na próxima vez que salvar a ficha por aqui — para
    conteúdo que não se encaixa nos campos, coloque em outra seção da página.

## Criar ou editar uma ficha de combate

Na aba **Ficha de combate**, escolha a página onde o NPC deve aparecer (qualquer página da wiki,
não precisa ser uma de personagem — a Sessão 0, por exemplo, guarda as dela na própria página do
roteiro) e, se já existir uma ficha ali, escolha-a no segundo menu para editar; deixe em "— nova
ficha —" para criar uma.

Preencha:

| Grupo | Campos |
|---|---|
| Identidade | Nome, tipo/papel, CA, PV, deslocamento, perícias, sentidos, idiomas, equipamento |
| Atributos | FOR, DES, CON, INT, SAB, CAR — só o valor; o modificador é calculado sozinho |
| Traços, ações e magias | Uma caixa de texto para cada, um traço/ação por linha no formato `Nome: descrição` |

Ao salvar, o painel insere (ou atualiza) o cartão visual na página, com os atributos já com
modificador, e roda `mkdocs build --strict` para confirmar que nada quebrou. Se você mudar o nome
de uma ficha existente, o cartão é atualizado no lugar — não duplica.

!!! warning "Salvar substitui o cartão inteiro"
    Assim como a ficha de personagem, cada vez que você salva pelo painel, o cartão inteiro é
    reescrito a partir dos campos do formulário. Não edite o texto do cartão à mão pelo editor
    genérico — na próxima vez que salvar por aqui, qualquer ajuste manual se perde.

Para uma ficha **nova**, um campo opcional "Inserir depois deste trecho" deixa escolher onde ela
entra na página (por exemplo, `## Aliados`, copiando o texto exato de um cabeçalho já existente).
Deixe em branco para simplesmente adicionar no final do texto e mover depois pelo editor genérico.

## Editar qualquer página

Na aba **Editar**, escolha uma página numa lista (com o título de cada uma, para não precisar saber
o nome do arquivo), edite o texto Markdown na caixa e clique em **Salvar**. É a mesma sintaxe usada
em toda a wiki: `#` para títulos, `[texto](link.md)` para links, `**negrito**`, tabelas, e as caixas
`!!! aviso "Título"` para os avisos coloridos. Mudar um título é só editar a linha que começa com
`#` dentro do texto.

!!! question "Em aberto"
    O painel ainda não valida a sintaxe antes de salvar. Depois de editar uma página por aqui, dê
    uma olhada nela no site (`http://127.0.0.1:8000`) para confirmar que ficou como você queria.

### Adicionar uma imagem

Com uma página aberta para edição, clique em **Adicionar uma imagem** para abrir o formulário de
envio. Escolha o arquivo (PNG, JPG, GIF, WEBP ou SVG) e a pasta de destino dentro de
`docs/assets/imagens/` (cidades, personagens, facções, eventos, geografia, mapas ou mundo) e clique
em **Enviar imagem**.

O painel salva o arquivo na pasta escolhida — criando um nome novo automaticamente se já existir um
arquivo com o mesmo nome, para nunca sobrescrever por engano — e insere sozinho o trecho
`![legenda](caminho/da/imagem.png)` no fim do texto, já com o caminho relativo certo a partir da
página que você está editando. Depois é só mover esse trecho para onde quiser dentro do texto e
salvar.
