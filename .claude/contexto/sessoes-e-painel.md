# Sessões, Diário e Painel do Mestre

> Detalhes de referência, separados do `CLAUDE.md` para economizar contexto.
> Leia este arquivo quando for mexer no Painel (`admin/`), no Diário, nas páginas de sessão ou no calendário.

# Diário de sessões e calendário

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
  4. registre `diario/sessao-NN.md` no `nav:` do `mkdocs.yml`, dentro de **Mestre → Diário de
     Sessões**;
  5. registre em `dados/linha-do-tempo.yml` o que mudou com cada NPC/cidade/facção (pelo Painel,
     aba Linha do tempo) — não escreva mais `## Histórico de sessões` nas páginas.
- **`docs/mundo/calendario.md`** define a data ficcional: formato `DD de <mês> de <ano>`, usando os
  nomes de mês reais e um ano fictício à escolha do autor (ex.: `24 de outubro de 1453`). É uma
  proposta mínima (`POSSIBILIDADE`); ajuste se o autor preferir nomes de mês próprios.

## Painel do Mestre (`admin/`)

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
- os marcadores `<!-- campo:<chave> -->`/`<!-- /campo:<chave> -->` dentro de `## Ficha da cidade`
  ou `## Biografia` — um par por campo, invisíveis no site. A aba **Biografia** do painel lê
  e regrava a seção inteira a partir desses marcadores; os campos estão em `admin/wiki_data.py`
  (`CAMPOS_FICHA_CIDADE`, `CAMPOS_FICHA_PERSONAGEM`, via `TIPOS_FICHA` — tipos `"npc"`/`"jogador"`/
  `"cidade"`);
- dentro de uma ficha de combate (`<!-- inicio:statblock:<slug> -->...<!-- fim:... -->`), os
  marcadores internos `<!-- bloco:ficha -->`/`<!-- bloco:inventario -->`/`<!-- bloco:grimorio -->`/
  `<!-- bloco:caracteristicas -->`/`<!-- bloco:efeitos -->` (cada um com seu par de fechamento) —
  é por eles que `hooks/gallancourt.py::_extrair_blocos_personagem` decide em qual aba cada pedaço
  da "ficha completa" opcional entra. Fichas salvas antes desses marcadores existirem não os têm;
  nesse caso o cartão inteiro cai na aba **Ficha** (compatibilidade mantida de propósito);
- numa página de monstro (front matter `monstro:`) com mais de uma ficha de combate — a base e
  variantes criadas pelo botão **Criar variante a partir desta ficha** em `/ficha-combate` (ex.:
  Goblin → Arqueiro, Lanceiro) —, `hooks/gallancourt.py::_paginar_variantes` agrupa todas numa aba
  por ficha, rotulada pelo campo `rotulo_variante` de cada uma (`admin/wiki_data.py`,
  `CAMPOS_STATBLOCK_TEXTO`). Com uma ficha só, não mexe em nada;
- o bloco `npc:` (ou `jogador:`) no front matter das páginas de NPC/jogador;
- em `docs/mestre/sessoes/sessao-<n>-*.md`, os marcadores `<!-- mestre:alternancia -->`/
  `<!-- /mestre:alternancia -->` logo após o H1 e no fim das abas, e o `<div class="painel-
  iniciativa" data-pagina="...">` entre eles — é por eles que `hooks/gallancourt.py::
  _alternancia_mestre` monta o alternador **Página normal / Modo Mestre** no topo da página (ver
  `docs/javascripts/alternancia-mestre.js`);
- `dados/linha-do-tempo.yml` — edite pelo Painel ou mantendo o formato descrito no cabeçalho dele.

Ao testar mudanças no painel, use uma cópia em `GALLANCOURT_ADMIN_ROOT` — nunca aplique uma sessão
de teste direto no `docs/diario/` real.

# Sessões (Mestre → Sessões)

Uma página por sessão em `docs/mestre/sessoes/sessao-<n>-<slug>.md`, no layout da Sessão 0: um
alternador **Página normal / Modo Mestre** logo após o H1 (ver bullet do `mestre:alternancia`
acima); do lado "Normal", ficha (`<div class="ficha">`) + abas `=== "Resumo"`, `"Cenas"`, `"NPCs"`,
`"Lugares"`, `"Loot & Pistas"`, `"Segredos do Mestre"`; do lado "Mestre", só o Painel de
Iniciativa (`admin/sessao_viva.py` + `docs/javascripts/painel-iniciativa.js`), em largura cheia. O
front matter tem `sessao: {numero: N}`. A lista em `mestre/sessoes/index.md` é gerada pelo hook no
lugar de `<!-- sessoes:lista -->`.

Os botões **Adicionar NPC** e **Nova sessão** apontam para o Painel (`extra.painel_url` no
`mkdocs.yml`, rotas `/npc/novo` e `/sessoes/nova`), que cria a página e a insere no `nav` abaixo das
linhas âncora `      - NPCs:` e `      - Sessões:` — não mude a indentação nem o texto dessas linhas.
