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

## Acessar de outro aparelho (celular, outro PC) pela Tailscale

Por padrão o painel só escuta `127.0.0.1` — nem outro aparelho na mesma rede alcança ele. Para
abrir o painel do seu celular ou notebook enquanto o computador com o projeto fica ligado em casa,
sem pagar por servidor nenhum:

1. Instale o [Tailscale](https://tailscale.com/download) neste computador e no aparelho de onde
   você quer acessar, entrando com a mesma conta nos dois.
2. Neste computador, em vez do `.bat` normal, dê duplo clique em
   `admin/iniciar-painel-tailscale.bat` (ou rode `set PAINEL_HOST=0.0.0.0` antes do comando usual).
3. No outro aparelho, abra `http://<nome-ou-IP-tailscale-deste-pc>:5001/` — o Tailscale mostra esse
   endereço na lista de aparelhos do seu tailnet.

!!! warning "Ainda sem senha"
    `PAINEL_HOST=0.0.0.0` também deixa o painel visível para qualquer aparelho na sua rede local
    (Wi-Fi de casa), não só pela Tailscale — ele continua sem login. Use isso só em rede de
    confiança, e volte para o `.bat` normal (ou feche a janela) quando terminar.

!!! info "O Painel de Iniciativa embutido precisa do endereço certo"
    A aba **Painel de Iniciativa** de cada sessão busca os dados em `extra.painel_url`
    (`mkdocs.yml`) — por padrão `http://127.0.0.1:5001`, que só funciona no mesmo computador.
    Acessando o site de outro aparelho pela Tailscale, troque esse valor pelo endereço Tailscale
    deste PC antes de gerar o site, ou ele não vai achar o painel. E se o site estiver publicado
    em HTTPS (como o GitHub Pages), o navegador bloqueia por padrão qualquer chamada para um
    endereço `http://` comum — o Painel de Iniciativa embutido só funciona acessando o site por
    HTTP (ex.: `mkdocs serve` local ou pela Tailscale), não na versão publicada.

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

Marque **É um NPC genérico** para criar um modelo reutilizável (guarda, camponês, nobre…), em vez
de alguém específico — ele fica fora da tabela principal, num grupo **Genéricos** no menu, e
aparece como ponto de partida ao criar uma ficha de combate (ver mais abaixo).

## Adicionar um lugar

Em [Lugares](../lugares/index.md), o botão **Adicionar lugar** abre esta aba (ou acesse
`http://127.0.0.1:5001/lugar/novo`). Só o nome é obrigatório; tipo, cidade ou região e um resumo
de uma linha são opcionais. Crie o lugar aqui **antes** de escrever uma cena que acontece nele —
assim a aba **Lugares** da sessão pode linkar para a página de verdade.

## Adicionar um jogador

Em [Mestre → Jogadores](jogadores/index.md), o botão **Adicionar jogador** abre esta aba (ou
acesse `http://127.0.0.1:5001/jogador/novo`). Cadastra o personagem — nome, quem joga, raça e
classe, um resumo. A ficha de combate dele (CA, PV, ações…) é criada depois, como a de qualquer
NPC, pela aba **Ficha de combate**, escolhendo a página do jogador.

## Criar uma sessão nova

Em [Mestre → Sessões](sessoes/index.md), o botão **Nova sessão** abre esta aba (ou acesse
`http://127.0.0.1:5001/sessoes/nova`). Informe o número e o título — o resto é opcional: data,
resumo breve (aparece no cartão da lista de sessões), resumo rápido, jogadores, nível, duração,
tom, local, missão e recompensa. O painel cria a página de preparação com o mesmo layout da
Sessão 0 — abas **Resumo** (com a ficha da sessão), **Cenas**, **NPCs**, **Lugares**,
**Loot & Pistas**, **Segredos do Mestre** e **Painel de Iniciativa**, nessa ordem —, adiciona-a ao
menu em **Mestre → Sessões** e confere o site. A sessão aparece sozinha na lista de sessões, com
título e data na mesma linha e o resumo breve abaixo.

Antes de escrever as **Cenas**, vale ter os [Lugares](../lugares/index.md) e os
[NPCs](../personagens/index.md)/[Jogadores](jogadores/index.md) envolvidos já cadastrados — a cena
depende deles. Depois de criar a sessão, escolha quem participa dela em
**Participantes da sessão** (`/sessoes/participantes?pagina=<página da sessão>`) — é essa lista
que o Painel de Iniciativa embutido na própria página vai oferecer.

Essa é a página de **preparação**. Depois de jogar, registre o que aconteceu em
**Registrar sessão** (abaixo), que alimenta o [Diário de Sessões](../diario/index.md).

## Tocar uma sessão ao vivo

A aba **Painel de Iniciativa**, no final de cada página de sessão, é um bloco de notas e um
rastreador de combate pra usar durante a mesa — embutido na própria página do site, sem precisar
abrir outra aba do navegador nem outro site: ele busca os dados do Painel do Mestre (que precisa
estar rodando no seu computador) por baixo dos panos, e redesenha a tela a cada ação, sem
recarregar a página. É **preso à página da sessão**: a Sessão 0 tem o seu próprio combate, a
Sessão 3 do Diário teria o dela, e por aí vai, sem se misturar. Diferente do resto do painel, nada
aqui mexe em `docs/` nem no conteúdo do site — o estado fica só em `admin/dados/` (de fora do
git), porque é rascunho de sessão, não cânone nem conteúdo da wiki.

Se preferir usar o Painel direto, sem o site aberto, a mesma coisa continua disponível na aba
**Sessão ao vivo** (`http://127.0.0.1:5001/sessao-ao-vivo`) — só que ali o seletor de ficha mostra
todo stat-block do site, em vez de só os desta sessão.

### Notas e resumo

Uma caixa de anotação rápida registra uma linha com o horário a cada envio — útil pra marcar
coisas no calor do momento ("rolou 18 no furtividade", "jogador X perguntou sobre o Correntes").
O campo **Resumo da sessão**, abaixo, é de texto livre e pensado pra ir sendo escrito aos poucos;
no fim, o link "registrar a sessão no Diário" leva direto pra aba **Registrar sessão** já com esse
texto preenchido no campo "O que aconteceu".

### Iniciativa

Adicione cada jogador ou NPC com o nome, o tipo e o valor da rolagem de iniciativa. Se o NPC já
tem uma [ficha de combate](manutencao-do-canone.md#ficha-de-combate) nesta própria página ou na
página de um jogador/NPC marcado em **Participantes da sessão** (ver "Criar uma sessão nova",
acima), selecione-a em **Ficha vinculada** — o nome e o PV são preenchidos sozinhos (se deixados
em branco), e a ficha completa dele passa a aparecer na tela quando for a vez dele. O menu só
mostra essas fichas, não todo stat-block do site — é por isso que vale cadastrar os participantes
antes de tocar a sessão. Depois de adicionar todo mundo, a tabela fica ordenada sozinha, da maior
iniciativa pra menor.

Clique em **Próximo turno** para avançar — na primeira vez, já começa por quem tem a iniciativa
mais alta. A lista exibida sempre recomeça por quem está na vez (ela "gira", mas a ordem real de
iniciativa por baixo não muda), então não precisa catar a linha destacada numa mesa com muita
gente; ao voltar pro primeiro da lista, a rodada avança sozinha.

Cada linha tem controles rápidos:

- **PV**: um campo pra somar ou subtrair (ex.: `-7` ou `+5`) e aplicar.
- **Status**: texto livre separado por vírgula — exaustão, veneno, atordoado, ou qualquer outra
  condição (ex.: `Exausto (nível 1), Envenenado`).
- **Caído** / **Morto**: alternam um estado visual (linha apagada, nome riscado) — bons pra
  decidir rápido quem ainda está de pé numa mesa grande.
- **Remover**: tira da iniciativa (não apaga do log de ações já registradas).

### Ações e diário de combate

No formulário de ações, escolha quem agiu, o tipo (**Ataque**, **Cura** ou **Outro**), em quem (o
alvo), a arma/magia/habilidade usada e o valor (dano ou cura). Ao registrar, o painel já aplica
esse valor no PV do alvo lá em cima — não precisa fazer as duas contas. Cada ação registrada entra
no log, do mais recente pro mais antigo, com um botão para remover em caso de engano.

Logo abaixo, duas coisas calculadas sozinhas a partir desse log:

- **Diário de combate**: uma frase pronta por ação, agrupada por rodada (ex.: "**Capitão Harker**
  atacou Jogador Ana com Cimitarra, causando 6 de dano.") — rascunho pra copiar e ajustar na hora
  de escrever a história da campanha depois.
- **Resumo do combate**: quem mais causou dano, quem mais recebeu dano, quem mais curou e quem
  acertou mais golpes — útil pra analisar depois quem andou carregando o grupo.

### Encerrar um combate

Se a mesma página for ter mais de um combate ao longo do tempo (ou pra fechar depois de registrar
a sessão no Diário), use **Arquivar e começar do zero** no fim da página — guarda tudo (notas,
combate, log) num arquivo com data e hora em `admin/dados/combates/arquivadas/` e limpa a tela
para o próximo combate dessa mesma página.

### Encerrar

No fim da sessão, **Arquivar e começar do zero** guarda tudo (notas, combate, ações) num arquivo
com data e hora em `admin/dados/arquivadas/` e limpa a tela pra próxima sessão. Isso não apaga
nada — só tira da tela; os arquivos antigos continuam no disco se quiser consultar depois.

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

## Preencher a ficha de um personagem ou cidade

Na aba **Ficha**, escolha "Personagem" ou "Cidade", escolha o nome numa lista e preencha os
campos. Ao salvar, o painel cria (ou substitui) a seção **Ficha de personagem** — ou **Ficha da
cidade** — no rodapé daquela página, com exatamente os campos preenchidos.

Personagens:

| Campo | O que colocar |
|---|---|
| Aparência física | Altura, porte, marcas, roupas, o que chama atenção à primeira vista |
| Personalidade | Como a pessoa age, fala, o que a move |
| Traço marcante | Um hábito ou trejeito reconhecível |
| Ideal | O que essa pessoa defende |
| Vínculo | O que ou quem ela protege ou persegue |
| Defeito | O que pode ser sua ruína |
| Proficiências e idiomas | Perícias, ferramentas, armas, idiomas que fazem sentido para ela |

Cidades:

| Campo | O que colocar |
|---|---|
| População | Uma estimativa, mesmo que aproximada |
| Defesas e guarnição | Muralhas, guarda, frota, o que protege o lugar |

!!! warning "Salvar substitui a seção inteira"
    Cada vez que você salva a ficha de uma página, o painel **reescreve a seção inteira** com os
    valores atuais dos campos. Se você tiver escrito algo à mão nessa seção pelo editor genérico,
    fora desses campos, aquele texto some na próxima vez que salvar a ficha por aqui — para
    conteúdo que não se encaixa nos campos, coloque em outra seção da página.

## Criar ou editar uma ficha de combate

Na aba **Ficha de combate**, escolha a página onde o NPC deve aparecer (qualquer página da wiki,
não precisa ser uma de personagem — a Sessão 0, por exemplo, guarda as dela na própria página do
roteiro) e, se já existir uma ficha ali, escolha-a no segundo menu para editar; deixe em "— nova
ficha —" para criar uma. Criando uma ficha nova, o terceiro menu, **Começar a partir de um NPC
genérico**, preenche o formulário com os valores de um NPC-modelo já cadastrado (guarda, camponês,
bandido…) — é só ajustar o que for diferente e salvar; o modelo original não é alterado.

Preencha:

| Grupo | Campos |
|---|---|
| Identidade | Nome, tipo/papel, foto, CA, PV, deslocamento, espaços de magia, perícias, sentidos, idiomas, equipamento |
| Atributos | FOR, DES, CON, INT, SAB, CAR — só o valor; o modificador é calculado sozinho |
| Traços, ações e magias | Uma caixa de texto para cada, um traço/ação por linha no formato `Nome: descrição` |

A **foto** é opcional: envie um arquivo pelo campo "Enviar uma foto" (PNG, JPG, WEBP, GIF ou SVG) e
o caminho é preenchido sozinho; sem foto, o cartão aparece só com CA, PV, deslocamento e (se
preenchido) espaços de magia, sem moldura vazia. **Espaços de magia** também é opcional e de texto
livre (ex.: `1º: 4, 2º: 3`) — para NPCs que não conjuram, deixe em branco.

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

## Criar um item de Loot & Pistas

Na aba **Loot & Pistas**, escolha a página (normalmente a da sessão) e, se já existir um item ali,
escolha-o no segundo menu para editar; deixe em "— novo item —" para criar um. Preencha nome,
descrição, onde está (um lugar) e quem tem (um NPC ou jogador) — os dois últimos viram link
automaticamente se baterem com o nome de algo já cadastrado, senão ficam como texto puro.

Igual à ficha de combate, salvar **reescreve o cartão inteiro** a partir dos campos do formulário,
e o mesmo campo opcional "Inserir depois deste trecho" funciona para escolher onde um item novo
entra na página.

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
