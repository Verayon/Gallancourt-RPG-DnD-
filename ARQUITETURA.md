# Auditoria e proposta de arquitetura — Gallancourt

Documento da Etapa A pedida pelo autor: diagnóstico real do projeto (inspecionado em código, não
em documentação), avaliação da reescrita proposta (Next.js + React + TypeScript + Tailwind +
PostgreSQL + Prisma) e uma recomendação fundamentada antes de qualquer implementação.

**Resumo executivo:** o projeto é bem mais estruturado do que uma "wiki estática" sugere — já
tem CRUD genérico pelo Painel, um modelo de dados semi-estruturado (JSON embutido em Markdown),
e, principalmente, **já separa o estado de combate (efêmero) da ficha-base (persistente)**, que é
exatamente um dos requisitos centrais do briefing. A limitação real não é "tudo é texto solto" —
é que não existe um banco de dados consultável, e toda escrita de conteúdo canônico dispara uma
reconstrução completa do site (hoje 70–130s, 1024 páginas). **Não recomendo a reescrita completa
para Next.js/React/Postgres/Prisma agora** — o custo (abandonar uma ferramenta funcionando, testada
e recém-publicada, por um projeto de várias semanas, com um servidor Postgres para manter) não se
paga para o estágio atual (uso solo, uma campanha, infraestrutura já frágil o bastante pra ter
dado trabalho hospedar hoje). Proponho uma alternativa que resolve os mesmos problemas reais —
dados estruturados, sem duplicação, Mesa do Mestre sem rebuild — sem trocar de stack. Decisão do
autor nas perguntas do final.

## 1. O que existe hoje (inspecionado em código)

| Camada | Arquivo(s) | Linhas | O que faz |
|---|---|---|---|
| Conteúdo/lore | `docs/**/*.md` | 1024 páginas, 4,1 MB | Markdown + front matter YAML. Fonte única de verdade de tudo — lore E dados "estruturados" |
| Build | MkDocs Material + `hooks/gallancourt.py` | 1065 | Gera tabelas/abas/cartões a partir do front matter a cada build |
| App/admin | `admin/app.py` | 1444 | Rotas Flask — cada POST reescreve um `.md` e, na maioria dos casos, dispara `mkdocs build --strict` inteiro |
| Lógica de domínio | `admin/wiki_data.py` | 1843 | Isolado do Flask de propósito; lê/escreve Markdown+YAML, sem banco |
| Combate ao vivo | `admin/sessao_viva.py` | 340 | **Isolado do resto** — estado em `admin/dados/combates/*.json`, fora do git, sem rebuild |
| Dados "de tabela" | `dados/*.yml` | ~4 arquivos pequenos | linha do tempo, changelog, roadmap, bugs — um YAML cada |
| Testes | `scripts/testar_site.py` | 1 arquivo | Build + smoke tests de rotas + Playwright; nenhum teste de regra de jogo (não existe regra automatizada ainda) |
| Auth | `admin/app.py` (hoje) | — | 1 senha compartilhada, sessão Flask; sem papéis, sem usuários |

**Como cada conceito do briefing já existe (ou não) hoje:**

| Conceito pedido | Equivalente atual | Observação |
|---|---|---|
| `Actor` / `CharacterBuild` | JSON embutido em comentário HTML (`<!-- dados:statblock -->`) na página do NPC/jogador | Schema é uma lista Python fixa (`CAMPOS_STATBLOCK_*`), não um schema de banco; sem validação de tipo além de "campo obrigatório" |
| `ActorResource`, `Feature`, `Attack`, `Spell`, `InventoryItem` | Campos dentro do mesmo JSON (texto livre na maioria) — **implementado hoje à noite**: grupos `inventario`, `magias_detalhe`, `caracteristicas`, `efeitos` como listas de objetos | É dado estruturado, mas vive dentro de um arquivo de página, não em tabelas relacionáveis |
| `CombatState`, `EncounterParticipant`, `ResourceUsage` | `admin/sessao_viva.py` — `admin/dados/combates/<página>.json` | **Já separado da ficha-base** (mudar PV em combate não toca o statblock); já sobrevive a reiniciar o Painel (estado em disco); **não dispara rebuild** |
| `CombatEvent` (log auditável) | `log_acoes` dentro do mesmo JSON | Existe, mas sem timestamp granular nem possibilidade de consulta entre sessões |
| `RollRecord` | Não existe | Toda rolagem é feita fora do sistema (dado físico/app separado) e só o resultado é digitado |
| `ActiveEffect`, `ConditionDefinition`, `ConcentrationState` | Campo `status`/`flag` livre no combatente + a lista `efeitos` nova de hoje | **Sem motor de regras** — é só anotação visível, nada aplica automaticamente |
| `Adventure`, `GameSession`, `Scene`, `Encounter` | Página de sessão (`docs/mestre/sessoes/*.md`) com abas geradas (Cenas, NPCs, Loot, etc.) | Cenas/Encontros são seções de texto, não registros — não há como "carregar um encontro preparado" na Mesa do Mestre sem reescrever manualmente |
| `LootTable`/`EncounterLoot` | Sistema "Loot & Pistas" (`CAMPOS_ITEM_TEXTO`) | Cartões por sessão, sem ligação formal a um `InventoryItem` do compêndio |
| `EntityRelationship` | `scripts/gerar_relacoes.py` — deriva tabelas de relações a partir de campos de front matter (`afiliacao`, etc.) | Regerado por script, não é uma tabela de relações consultável em tempo real |
| `User`/`CampaignMembership`/`CharacterOwnership` | Não existe | Hoje: 1 senha para o Painel inteiro, acesso de jogador não existe |
| Motor de regras (`resolveAttack`, `applyDamage`, …) | Não existe | Toda matemática de jogo é feita pelo Mestre; o sistema só calcula modificador de atributo e total de perícia/salvaguarda (adicionado hoje) |

**O que já está certo, de acordo com os próprios princípios do briefing:**

- Estado de combate **já não é** a mesma coisa que a ficha do compêndio, e **já não** exige rebuild.
- `admin/wiki_data.py`/`admin/sessao_viva.py` já são isolados do Flask (lógica de domínio
  separada da camada HTTP), testáveis por chamada direta de função.
- Lore em Markdown, hospedado em git — exatamente o que o §6 do briefing pede para manter.
- Existe suíte de testes de regressão (`scripts/testar_site.py`, 29 verificações hoje, 0 falhas)
  cobrindo build, Painel e navegador.

**Limitações reais (confirmadas em código, não hipotéticas):**

1. **Toda escrita de conteúdo canônico (NPC, item, página) dispara `mkdocs build --strict`
   inteiro** — medido hoje em produção: 70 a 134 segundos, com 1024 páginas. Cresce com o
   conteúdo. Isso é real e vai incomodar cada vez mais.
2. **Sem banco relacional**: `listar_statblocks`/`listar_npcs`/etc. fazem `rglob("*.md")` e
   abrem/regex-parseiam cada arquivo a cada chamada. Funciona a 1024 páginas; não vai escalar
   indefinidamente, e não dá para fazer uma consulta tipo "todo item mágico que algum jogador
   carrega" sem varrer tudo.
3. **Sem integridade referencial**: um `dono` de item perdido ou `afiliacao` de NPC pode apontar
   para algo que não existe; o sistema degrada silenciosamente (`_link_se_existir` só vira texto
   simples).
4. **Sem motor de regras**: tudo que envolve matemática de D&D (ataque, salvaguarda, dano,
   condição) é digitado manualmente pelo Mestre. O briefing pede isso como objetivo central da
   Mesa do Mestre.
5. **Auth é um cadeado único**, não um sistema de usuários — adequado para "só o Mestre usa hoje",
   insuficiente para "jogadores acessam no futuro" sem reconstrução.
6. **Sem portal de jogador** nem qualquer noção de propriedade de personagem.

## 2. Avaliação da stack proposta (Next.js/React/TS/Tailwind/Postgres/Prisma)

Tecnicamente, é uma escolha correta e moderna **para um produto multiusuário em crescimento**.
Para este projeto, hoje, os custos superam os benefícios:

- **Escala real**: 1 usuário principal (o Mestre), uma campanha, ~7 jogadores. Os problemas que
  Next.js/Postgres resolvem bem (múltiplos usuários concorrentes, consultas relacionais
  complexas, APIs versionadas) não são o gargalo medido aqui — o gargalo medido é "rebuild
  demorado em cada escrita", que tem soluções muito mais baratas (abaixo).
- **Custo operacional novo**: hoje o projeto roda com um duplo-clique num `.bat`, sem instalar
  servidor nenhum além do Python. Postgres exige um processo de banco rodando, backup, migrações
  (`prisma migrate`) — justamente a noite de hoje foi gasta só para conseguir expor o Painel atual
  (simples) fora da rede local. Adicionar um banco de verdade multiplica essa superfície.
- **Descontinuidade total da stack**: Next.js/React/TS não reaproveita nada do código Python
  existente (1843 + 1444 + 1065 + 340 linhas) nem dos hooks do MkDocs. Seria, na prática, duas
  aplicações completamente diferentes coexistindo até a migração terminar — ida e volta que o
  próprio briefing (§6, §12) pede para evitar ("não reescreva tudo de uma vez quando houver uma
  forma segura de migrar gradualmente"; "evite reescrita destrutiva").
- **Prazo real**: um recorte honesto de "fundação funcional" (Next.js + Postgres + Prisma +
  autenticação básica + 1 fatia vertical) é, no mínimo, dias de trabalho contínuo — não cabe numa
  sessão, e deixaria o projeto com duas aplicações pela metade simultaneamente por um bom tempo.

**Avaliação honesta da tensão no próprio briefing**: os princípios do §3/§12 (preservar, migrar
gradualmente, não reescrever tudo de uma vez) e a arquitetura de destino prescrita no §5 (trocar
toda a stack de aplicação) **se contradizem na prática** — trocar Flask+MkDocs por
Next.js+Postgres+Prisma é, por definição, reescrever a camada de aplicação inteira. Dá para
preservar o *conteúdo* (Markdown) gradualmente; não dá para "gradualmente" trocar o motor que lê e
serve esse conteúdo sem, em algum momento, ter duas aplicações rodando em paralelo.

## 3. Alternativa proposta — mesmos objetivos, sem trocar de stack

Resolve os mesmos problemas reais (dados estruturados, sem duplicação, Mesa do Mestre sem
reconstrução total, motor de regras testável, caminho pronto para contas de jogador) mantendo
Python/Flask e o conteúdo em Markdown onde já funciona bem:

1. **Banco real para dados operacionais** (SQLite para começar — zero infraestrutura nova, um
   arquivo; Postgres fica disponível depois se/quando precisar de acesso concorrente de verdade),
   via SQLAlchemy ou Prisma Client Python: `Actor`, `CharacterBuild`, inventário, magias,
   características, efeitos, `CombatState`, `CombatEvent`, `Adventure`/`Encounter` — tudo o que
   hoje é JSON dentro de Markdown ou YAML solto. O Markdown continua sendo só para lore/texto
   corrido (exatamente como o §6 do briefing pede).
2. **Escrita de conteúdo operacional para de disparar `mkdocs build`** — passa a atualizar o
   banco e servir a página relevante dinamicamente (ou via fragmento renderizado), sem tocar no
   site estático inteiro. Isso sozinho já resolve a queixa central de "Mesa do Mestre não pode
   depender de reconstruir o site".
3. **Motor de regras em Python puro, testável sem Flask**: funções como `calcular_ataque`,
   `aplicar_dano`, `aplicar_condicao`, testadas com `pytest`, independentes de rota HTTP — mesmo
   objetivo do §8/§14 do briefing, sem precisar de TypeScript para isso.
4. **Autenticação por usuário** (ainda simples — Flask-Login ou similar) preparando papéis
   Mestre/Jogador e propriedade de personagem, sem precisar de Next.js para isso.
5. **Se, depois disso, a interface Jinja+vanilla JS ficar claramente limitante** para a Mesa do
   Mestre (muitos componentes interativos, estado complexo no cliente), aí sim uma camada
   React/Vue **só nessa página**, consumindo uma API JSON que o Flask já exporia nessa altura — uma
   migração de interface localizada, não uma reescrita de aplicação inteira.

Isso segue à risca a ordem de prioridade que o próprio briefing pede no §12 ("fundação, modelo de
dados, depois Mesa do Mestre, depois motor de regras") — só que sem descartar 43 commits de
trabalho funcionando, testado e publicado hoje.

## 4. Riscos de qualquer um dos dois caminhos

- **Se for reescrita completa (Next.js/Postgres)**: risco alto de ficar com duas aplicações
  incompletas em paralelo por semanas; custo de infraestrutura novo (Postgres rodando em casa,
  hoje já foi difícil só expor o Flask); todo o código de hoje (ficha completa, auth, hospedagem)
  vira trabalho descartado antes de ser usado numa sessão de verdade.
- **Se for a alternativa incremental**: menor risco, mas não entrega a "aplicação web integrada
  com React" que o briefing descreve como visão de produto — se isso for um requisito não
  negociável do autor (não só um meio para os fins descritos), a alternativa não serve.

## 5. Status

**Decisão do autor:** caminho incremental em Python (§3), sem trocar de stack.

**Etapa B — fundação do banco de dados: implementada.** `admin/banco.py` (SQLAlchemy) +
`alembic/` (migrações versionadas) + `tests/` (pytest). Duas entidades iniciais, nenhuma
migrada de algo que já existia: `Campanha` (registro único, visível no cabeçalho do Painel) e
`Fonte` (livros de referência — PHB/DMG/MM/XGE/SRD semeados). Rota `/fontes` no Painel não chama
`publicar_build()`: salvar uma fonte leva ~0,1s, contra 70–130s de um `mkdocs build --strict`
completo — prova, em produção, que dado operacional não precisa mais disparar reconstrução do
site. Nada do que já funcionava foi tocado. Detalhes de uso em
`.claude/contexto/banco-de-dados.md`.

**Próxima fatia candidata** (não iniciada, decisão do autor quando for a hora): migrar fichas de
combate (Actor/CharacterBuild) para o banco — maior ganho real (reuso de um monstro/NPC em vários
encontros, hoje só possível copiando dados), mas também a mudança mais arriscada (toca
`hooks/gallancourt.py`, `ficha_combate.html`, `sessao_viva.py`/`sessao_ao_vivo.html`). Só depois
disso faz sentido parar de disparar rebuild nas escritas que hoje disparam, e só depois de ter
Actor estruturado no banco faz sentido começar o motor de regras (`calcular_ataque`,
`aplicar_dano`…).
