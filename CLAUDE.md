# CLAUDE.md

Wiki de lore da campanha de RPG (D&D 5e) **Crônicas de Gallancourt**, gerada com MkDocs Material
a partir de arquivos Markdown. Todo o conteúdo e toda a comunicação com o autor são em
**português do Brasil**; nomes próprios franceses mantêm os acentos (Baie de l'Éclair,
L'Ordre de Célestien, Magnetér).

## Comandos

```bash
pip install -r requirements.txt       # MkDocs 1.6 + Material 9 (fixado em mkdocs<2) + Flask
mkdocs serve                          # site local em http://127.0.0.1:8000
mkdocs build --strict                 # valida: falha com link ou âncora quebrados
python3 scripts/gerar_relacoes.py     # regenera relações entre cidades e intrigas
python3 admin/app.py                  # Painel do Mestre em http://127.0.0.1:5001
```

Guia de operação completo (comandos, rotina, solução de problemas) em `MANUTENCAO.md` — é o
arquivo que o autor lê para não depender do Claude Code no dia a dia. Ao mudar algo que afete como
o projeto é operado (comandos, portas, dependências, o Painel), atualize esse arquivo junto.

Rode `mkdocs build --strict` antes de todo commit. O build precisa terminar sem avisos.

## Estrutura

```
docs/
├── index.md, visao-geral.md   Início e resumo do cenário em uma página
├── historia/                  A crônica em capítulos + cronologia
├── eventos/                   Uma página por evento
├── geografia/                 Península, cordilheira, Cicatriz, ilhas, Nirador, mapas
├── cidades/                   5 cidades de Gallancourt + 3 de L'Ordre
├── faccoes/                   Estados, casas, organizações, frotas
├── personagens/               Uma página por NPC
├── mundo/                     Relações, intrigas, religião, economia, glossário
├── compendio/                 Leitura consolidada e completa: história, uma página por cidade,
│                              personagens, política, geografia e religião, pendências
└── mestre/                    Lacunas, inconsistências, fontes, manutenção do cânone
fontes/                        Acervo do autor (não editar); guia em fontes/README.md
├── textos/                    PDFs, documentos e transcrições .md
├── imagens/                   Mapas, ilustrações, retratos
└── videos/                    Vídeos
scripts/gerar_relacoes.py      Fonte única dos dados de relações e intrigas
mkdocs.yml                     Configuração e menu (nav) do site
```

## Regras do projeto (decididas pelo autor)

1. **Só conteúdo pré-campanha.** A wiki documenta o mundo como está quando a campanha começa.
   Não escreva planos de campanha, ganchos de aventura, atos, finais ou eventos futuros. Uma
   seção "Campanha" já foi criada e removida a pedido do autor (recuperável no commit `047b0af`).
2. **Precedência das fontes.** `fontes/textos/Historia_Gallancourt.pdf` (texto do autor, também
   chamado Versão 2; transcrição em `cronicas-de-gallancourt-v2.md`) **prevalece** sobre a
   Versão 1 (`cronicas-de-gallancourt-v1.md`) e sobre `Gallancourt_Dossie_Geral_Expandido.md`.
   Dentro do PDF, a versão revisada (páginas 1–8) prevalece sobre os rascunhos antigos
   (páginas 9–17). A posição exata da Versão 1 em relação ao dossiê ainda aguarda o autor
   (`docs/compendio/pendencias.md`).
3. **Nunca invente fatos como cânone.** Toda informação pertence a uma categoria:
   - texto corrido = cânone registrado nas fontes;
   - `!!! info "Leitura cartográfica"` = interpretação dos mapas;
   - `!!! abstract "Inferência funcional"` = dedução razoável, não confirmada;
   - `!!! question "Em aberto"` = ainda não definido.
4. **Marcas de estado** para relações e adições: `CANON`, `PLANEJADO`, `POSSIBILIDADE`
   (proposta do Claude, aguardando o autor), `SEGREDO` (verdade que os personagens não sabem),
   `DESCONHECIDO`, `CONSEQUÊNCIA`. Ao propor algo novo, marque `POSSIBILIDADE`; só o autor promove
   para `CANON`.
5. **Divergências entre fontes** não se resolvem em silêncio: pergunte ao autor e registre a
   decisão em `docs/mestre/inconsistencias.md`.
6. **Segredos.** Conteúdo `SEGREDO` fica em caixas `!!! warning "SEGREDO"` ou com a marca inline.
   Se o site for publicado para os jogadores, esse conteúdo precisa ser separado.

## Decisões já tomadas

| Decisão | Detalhe |
|---|---|
| Estado ocidental | Chama-se **Gallancourt**, governado pela **Aliança dos Lordes** via **Conseil des Seigneurs** |
| Torre do Trovão | Líder: **Arquimago Elian Lumière** (substituiu Kaelen Thorne). O **Duque Jeanesse Lumière** continua como chefe da Casa Lumière |
| Guilda naval | Líder: **Mestre Louis de Montclair** (substituiu Bromli Stonehammer) |
| Período após o Édito | **Ano de Sangue** (não "Mês de Sangue") |
| Scyras | **Marquesa** Scyras de la Maison Corbeau; pai traído por aristocratas da capital |
| Alfonse Enry | **Lorde**; o massacre da família do irmão é recente, obra de L'Ordre |
| Thibault de la Rivière | Traidor **infiltrado**, ainda comandante da Patrulha da Fronteira |
| Henri du Valois | Idealista disfarçado de playboy corrupto |
| Títulos dos rascunhos antigos | Não adotados; listados em `docs/mestre/inconsistencias.md` |

Perguntas ainda abertas estão em `docs/mestre/lacunas.md`.

## Identidade visual ("High Fantasy")

O site tem um padrão visual próprio, definido em `docs/stylesheets/extra.css`. Ao criar páginas
novas, siga-o em vez do visual padrão do Material.

- **Navegação:** só 3 itens de topo na barra lateral — **Início** (`index.md`), **Lore**
  (`lore.md`, página única e contínua) e **Wiki** (`wiki.md`, hub que expande em todas as outras
  seções: Cidades, Personagens, Facções, Eventos, Geografia, Mundo, Crônica em capítulos,
  Compêndio, Referência do Mestre). `navigation.tabs` fica **desligado** de propósito — tudo mora
  na barra lateral, nunca em abas no topo.
- **A Lore é só narrativa.** `lore.md` conta a história como uma crônica contínua, sem `<sup>`,
  sem `!!!` (admonições) e sem links de referência — é para ler como um livro. A versão anotada,
  com a origem de cada fato nas fontes (V1/V2/dossiê) e as caixas de "em aberto"/"divergência",
  mora em `compendio/historia-de-gallancourt.md` e faz parte do Compêndio, não da Lore. Ao
  atualizar a história, atualize as duas, cada uma no seu registro.
- **Cartões com imagem.** Toda página de listagem (índices de Cidades, Personagens, Facções,
  Eventos, Geografia, Mundo, Mestre, Compêndio) usa cartões de imagem clicável, não tabelas:
  ```markdown
  -   [![](../assets/placeholders/<categoria>.svg){ .card-portrait }](destino.md)

      **[Título](destino.md)**

      Descrição curta de uma ou duas linhas.
  ```
  Categorias disponíveis em `docs/assets/placeholders/`: `cidade`, `personagem`, `casa`,
  `estado`, `organizacao`, `evento`, `geografia`, `tema`. Use a mesma moldura em todos os cartões
  do mesmo tipo até existir uma imagem real. Imagens de verdade vão em `docs/assets/imagens/`
  (convenção em `docs/assets/imagens/LEIA-ME.txt`); ao adicionar uma, troque o `src` do cartão
  correspondente (e, se fizer sentido, a ficha da página de detalhe).
- **Fontes:** títulos em **Cinzel** (`Cinzel Decorative` só no herói/logo); corpo de texto em
  **EB Garamond**. Carregadas via `@import` do Google Fonts no topo do `extra.css`
  (`theme.font: false` no `mkdocs.yml` evita que o Material baixe Roboto por cima).
  Ícones de portal usam a sintaxe `:material-<nome>:` (requer `pymdownx.emoji` já configurado).
- **Paleta:** duas variantes com nomes próprios — **Grimório** (escura, `slate`, padrão) e
  **Pergaminho** (clara, `default`). Definidas como variáveis `--gc-*` e sobrepostas às variáveis
  do Material em `[data-md-color-scheme="slate"]` / `[data-md-color-scheme="default"]`. Dourado
  (`--gc-gold`) é o acento; roxo profundo é a cor primária do cabeçalho.
- **Classes utilitárias para conteúdo:**
  - `.hero` — banner de capa com imagem de fundo (`docs/assets/hero-bg.svg`), usado só no
    `index.md`. Para trocar por uma arte real da campanha, salve o arquivo em `docs/assets/` e
    troque a `url(...)` da regra `.hero` no `extra.css`.
  - `.lore-scroll` — envolve o corpo da página de Lore: leitura em coluna estreita, capitular na
    primeira letra, divisores ornamentais antes de cada `##`. Não aplique a páginas de referência
    (tabelas ficam apertadas nessa largura).
  - `.wiki-portal` — envolve o hub `wiki.md`.
- Favicon: `docs/assets/favicon.svg`. Logo do tema: ícone `material/sword-cross`.

## Diário de sessões e calendário

A partir de agora o site também é usado **durante e depois de cada sessão jogada**, não só na
preparação. Duas peças cuidam disso:

- **Data real automática.** O plugin `git-revision-date-localized` (em `mkdocs.yml`) mostra, no
  rodapé de toda página, a data da última edição e a da criação — tiradas do histórico do git, sem
  precisar anotar nada à mão. Só funciona depois que a mudança é commitada; antes disso, mostra a
  data de hoje como aproximação. Por isso, commitar com frequência (ver checklist do `README.md`)
  também mantém esse rodapé correto.
- **`docs/diario/`** é o registro manual de cada sessão: uma página `sessao-NN.md` por sessão, com
  a ficha (data real, data na campanha, local, personagens), o resumo do que aconteceu e a lista de
  páginas que mudaram por causa dela. `docs/diario/index.md` tem o modelo pronto para copiar, a
  tabela de sessões e uma linha do tempo em `mermaid`. Ao processar uma sessão nova (pedida pelo
  autor ou registrada por ele):
  1. crie `diario/sessao-NN.md` a partir do modelo;
  2. edite de fato as páginas listadas em "Atualizações no cânone" daquela sessão;
  3. adicione uma linha na tabela e um marco na linha do tempo de `diario/index.md`;
  4. registre `diario/sessao-NN.md` no `nav:` do `mkdocs.yml`, dentro de **Wiki → Diário de
     Sessões**;
  5. se a mudança merece ser lembrada na própria página do personagem/cidade/facção, adicione lá
     uma seção `## Histórico de sessões` (opcional; só existe onde já houve uma mudança
     registrada) com uma linha `- **[Sessão N](../diario/sessao-NN.md)** (data na campanha) — o
     que mudou.
- **`docs/mundo/calendario.md`** define a data ficcional: formato `DD de <mês> de <ano>`, usando os
  nomes de mês reais e um ano fictício à escolha do autor (ex.: `24 de outubro de 1453`). É uma
  proposta mínima (`POSSIBILIDADE`); ajuste se o autor preferir nomes de mês próprios.

### Painel do Mestre (`admin/`)

Um app Flask local (fora de `docs/`, não faz parte do site publicado) que faz os cinco passos do
registro de sessão por um formulário: marcar NPCs/cidades, escrever o resumo, aplicar. Guia de uso
completo em `docs/mestre/painel.md`; a lógica de leitura/escrita fica isolada em
`admin/wiki_data.py` (testável sem subir o Flask — todas as funções recebem `root: Path`, e o app
lê `GALLANCOURT_ADMIN_ROOT` do ambiente para permitir apontar para uma cópia de teste). Convenções
que o painel depende de encontrar, e que **não podem ser removidas** das páginas que ele edita:

- os marcadores `<!-- inicio:sessoes -->`/`<!-- fim:sessoes -->` e
  `<!-- inicio:timeline -->`/`<!-- fim:timeline -->` em `docs/diario/index.md`;
- o texto exato `**Próxima:** —` no fim de cada `sessao-NN.md` (é o que o painel substitui ao
  encadear a próxima sessão);
- a linha `- diario/index.md` no `nav:` do `mkdocs.yml` (é a âncora onde novas sessões são
  inseridas);
- os marcadores `<!-- campo:<chave> -->`/`<!-- /campo:<chave> -->` dentro de `## Ficha de
  personagem` (personagens) e `## Ficha da cidade` (cidades) — um par por campo, invisíveis no
  site (são comentários HTML). A aba **Ficha** do painel lê e regrava a seção inteira a partir
  desses marcadores; os campos e rótulos estão em `admin/wiki_data.py`
  (`CAMPOS_FICHA_NPC`/`CAMPOS_FICHA_CIDADE`) — para adicionar um campo novo, acrescente-o nessa
  lista.

Ao testar mudanças no painel, use uma cópia em `GALLANCOURT_ADMIN_ROOT` — nunca aplique uma sessão
de teste direto no `docs/diario/` real.

## Convenções das páginas

- Nome de arquivo: minúsculas, sem acentos, com hífens (`louis-de-montclair.md`).
- Toda página começa com front matter de `tags` (usadas no índice de tags).
- Personagens, cidades, facções e eventos têm uma ficha lateral:
  `<div class="ficha" markdown>` + tabela com cabeçalho vazio (`| | |`).
- Links sempre relativos entre arquivos `.md` (`../cidades/dodixie.md`), nunca URLs do site.
- Toda página nova precisa entrar no `nav` do `mkdocs.yml` e receber links das páginas
  relacionadas (cidade, casa, eventos, índice da seção).
- Diagramas em blocos ` ```mermaid ` (renderizados no navegador, carregados de CDN).

## Relações e intrigas: use o script

As páginas `docs/mundo/relacoes-entre-cidades.md` e `docs/mundo/intrigas-da-nobreza.md`, e os
trechos entre `<!-- inicio:gerado -->` e `<!-- fim:gerado -->` nas páginas de cidades e
personagens, são **gerados** por `scripts/gerar_relacoes.py`. Para mudar uma relação:

1. edite `PARES` (cidades) ou `INTRIGAS` (nobres) no script;
2. rode `python3 scripts/gerar_relacoes.py`;
3. rode `mkdocs build --strict`.

Nunca edite à mão o conteúdo gerado: ele é sobrescrito. Ao renomear um personagem, atualize
também o dicionário `P` e a lista `grupos` do script.

## O Compêndio

`docs/compendio/` repete, em páginas longas, o que está espalhado pela wiki, e acrescenta a
origem de cada informação (siglas V2, V2-r, V1, D). Ao mudar um fato, mude **as duas** versões: a
página da wiki e a página do Compêndio. As tabelas de relações do Compêndio são escritas à mão; a
fonte única continua sendo o script. Divergências e propostas pendentes ficam em
`docs/compendio/pendencias.md`.

## Checklist ao incorporar um novo documento do autor

1. Guarde o original em `fontes/textos/` (ou `imagens/`, `videos/`) com uma transcrição `.md`
   quando tiver texto, e registre-o em `fontes/README.md`.
2. Compare com a wiki; liste o que é novo e o que conflita.
3. Pergunte ao autor sobre cada conflito antes de alterar.
4. Aplique, registre as divergências em `docs/mestre/inconsistencias.md`, marque lacunas
   respondidas em `docs/mestre/lacunas.md` e atualize `docs/mestre/fontes.md`.
5. Procure nomes antigos com `grep -rn` para não deixar referências órfãs.
