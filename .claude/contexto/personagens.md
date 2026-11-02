# Personagens: monstro, NPC nomeado e jogador (banco de dados, não Markdown)

> Detalhes de referência, separados do `CLAUDE.md` para economizar contexto.
> Leia este arquivo antes de mexer em `docs/monstros/`, `admin/personagens_api.py`, nas tabelas
> de personagem em `admin/banco.py`, ou em `docs/javascripts/ficha.js`/`modo-mestre.js`.

## Por que é diferente de outras coisas em Markdown

A **ficha de combate** de monstro, NPC nomeado e jogador vive no banco (`dados/gallancourt.db`),
não em Markdown — desde a migração de monstros em 2026-10-30
(`scripts/migrar_monstros_para_banco.py`) e a unificação com NPC/jogador em 2026-10-31
(`scripts/migrar_npcs_jogadores_para_banco.py`), ambas de uso único, já rodadas. O autor queria
que a **mesma ficha** sirva de "token" pra qualquer um dos três — pensando no futuro sistema de
combate/iniciativa — e que criar variantes (Goblin → Arqueiro) ou editar qualquer campo aconteça
**direto na página pública**, com resposta instantânea, sem esperar `mkdocs build` (70-130s) a
cada edição. Ver `ARQUITETURA.md` e os planos salvos "Monstros no banco de dados" e "Unificar o
modelo de ficha" para o raciocínio completo.

**O que continua em Markdown, de propósito** (não migrar sem o autor pedir):
- A **ficha de planejamento** de NPC (objetivo/temor/segredo/vínculos — ver
  `.claude/contexto/npcs.md`) e a página do NPC em si (lore, biografia narrativa fora da aba
  Biografia da ficha de combate).
- **NPCs genéricos** (`docs/personagens/genericos/*.md` — guarda, camponês...): moldes de texto
  pra copiar num figurante, não personagens com identidade própria.
- **Figurantes de sessão** sem página própria (bandidos de uma sessão etc.): continuam no sistema
  leve antigo (`admin/wiki_data.py::salvar_statblock`/`ficha_combate.html`, JSON embutido em
  comentário HTML) — ver "Figurantes de sessão" em `docs/mestre/manutencao-do-canone.md`. Um
  figurante raramente precisa virar um personagem reutilizável de verdade; se precisar, vira uma
  página de NPC normal.
- A **ficha de cidade** (`wiki_data.TIPOS_FICHA["cidade"]`) — sistema de marcadores
  `<!-- campo:x -->` à parte, não tocado por nada disso.

## O que existe hoje

- **Schema** (`admin/banco.py`): `Personagem` (o ator — `tipo` discrimina "monstro"|"npc"|
  "jogador", `TIPOS_ATOR`; slug/nome/tamanho/`tipo_criatura`/alinhamento/`foto`, 1:N) → `Ficha`
  (uma ficha de combate; a primeira de cada personagem é sempre `is_base=True`, nunca removível;
  as demais são variantes, cópias independentes e totalmente editáveis). Único por `(tipo, slug)`,
  **não** por `slug` global — um NPC e um monstro podem ter o mesmo slug sem colidir (pastas
  diferentes, sem checagem cruzada hoje).
- **Biografia e Diário moram no `Personagem`, não na `Ficha`** — pertencem ao personagem, não a
  uma variante de combate (a aparência de um Goblin não muda entre a ficha Base e a variante
  Arqueiro). Biografia: `genero`/`idade`/`altura`/`peso_corporal`/`olhos`/`cabelo`/`pele`/`fe`
  (texto curto) + `aparencia`/`personalidade`/`traco`/`ideal`/`vinculo`/`defeito`/
  `pessoas_interesse`/`lugares_interesse` (texto livre — "pessoas/lugares de interesse" são texto,
  não links de verdade pra páginas de NPC/lugar, por decisão do autor: evitar relacionar/calcular
  automaticamente antes da hora). Diário: tabela `PersonagemDiarioEntrada` (data/título/texto) —
  **lista de entradas separadas**, não um texto único, também decisão explícita do autor.
- **Atributos são inteiros** (não texto) — o modificador é calculado, não digitado (ver
  `admin/personagens_api.py::modificador`, replicado em JS). `Ficha.cr` guarda só o valor SRD do
  monstro (ex.: "1/4" — XP vem de `CR_PARA_XP`, tabela fixa, não armazenado); `nivel`/`xp` são o
  equivalente pra NPC/jogador — escalas diferentes, por isso campos separados, não reaproveitados.
  `classe`/`antecedente` são rótulos livres de cabeçalho, não multiclasse estruturado (o "motor de
  regras" que precisaria disso ainda não existe). `deslocamento_m` é número (passo de 1,5 m no
  editor); `deslocamento_extra` (texto livre) cobre voo/escavar/nadar etc. `percepcao_passiva`
  (inteiro) é coluna própria — todo personagem tem uma, não é um "sentido" escolhido.
  `iniciativa_extra` soma ao modificador de Destreza na exibição (não um total já pronto).
  `pv_temporario`/`dados_vida_total`/`dados_vida_usados`/`carga_maxima`/5 colunas de moeda
  (`moeda_pc/pp/pe/po/pl`) completam o cabeçalho da ficha.
- **Catálogos compartilhados**, reutilizáveis entre fichas de qualquer tipo:
  `Equipamento`/`Magia`/`Habilidade`/`Idioma`/`Sentido`/`Pericia`, vinculados por tabelas de
  associação próprias (`FichaEquipamento` tem `quantidade`/`equipado`; `FichaSentido` tem `valor`
  **numérico** em metros — o mesmo sentido tem alcance diferente por personagem, ex. Visão no
  escuro 9 m vs. 36 m; `FichaPericia` tem `bonus` (inteiro, **pode ser negativo**) — o bônus final
  já pronto pra rolar, não calculado de atributo+proficiência, igual a `ca_total`). `Equipamento`
  tem `peso_kg` **numérico** (não texto) — converte sem perda a partir dos dados reais, que já
  seguiam o padrão "`<número> kg`". `origem_tipo`/`origem_personagem_slug` marcam o que nasceu
  exclusivo de um personagem (sem página própria), pra poder filtrar por origem no seletor.
- **Não são catálogos** — próprios de cada `Ficha`, sem valor de reuso entre personagens:
  `FichaEspacoMagia` (pool de espaços de magia: `nivel`/`maximo`/`usado`/`rotulo` — `rotulo`
  distingue dois pools no mesmo nível, ex. espaços normais vs. Magia de Pacto de um Bruxo);
  `FichaCondicao` (`nome` validado contra a lista fixa `banco.CONDICOES_D20`, as 15 condições do
  5e — não é um catálogo no banco, é um conjunto fechado de regras); `FichaEfeito`
  (`nome`/`tipo`/`origem`/`duracao`, `tipo` validado contra `banco.TIPOS_EFEITO`).
- **Lógica** (`admin/personagens_api.py`): isolado do Flask, como `wiki_data.py`/`sessao_viva.py`
  — toda função recebe uma `Session` já aberta. Serializa personagem/ficha pra JSON, cria variante
  (copiando atributos + todos os vínculos e pools da Base, exceto Biografia/Diário que já são
  compartilhados por morarem no Personagem), bloqueia excluir a Base, CRUD de vínculos/pools/
  condições/efeitos/entradas de diário.
- **API** (`admin/app.py`, bloco "API JSON de personagens"): `GET /api/personagens/<tipo>/<slug>`
  e `GET /api/catalogo/<tipo>` são **públicos** mesmo com `PAINEL_SENHA` definida (ver "Acesso"
  abaixo); toda escrita (`POST`/`PUT`/`DELETE`) exige a mesma sessão do Painel. `tipo` entra na
  URL porque slug sozinho não é mais globalmente único. Rotas de vínculo (`/api/fichas/<id>/...`)
  não levam `tipo`/`slug` — já são por `ficha_id`, independentes do tipo do dono.
- **Renderização** (`hooks/gallancourt.py::_ficha_dinamica_personagem`): o marcador
  `<!-- personagem:ficha-dinamica -->` vira uma `<div class="ficha-personagem" data-tipo="..."
  data-slug="...">` **vazia**. Quem desenha o conteúdo é `docs/javascripts/ficha.js`, buscando a
  API ao carregar — mesmo padrão já comprovado em `.painel-iniciativa`/`painel-iniciativa.js`.
  Consequência: **criar/editar/excluir uma ficha nunca dispara `mkdocs build`**; só é preciso
  reconstruir quando um personagem novo é criado (página `.md` nova) ou o front matter muda. Pra
  **monstro**, a página inteira é só o marcador (sem outro conteúdo). Pra **NPC/jogador**, o
  marcador fica dentro de uma seção `## Ficha de combate` normal, no meio de outras abas de prosa
  (Visão geral, Linha do tempo, Em aberto...) — `hooks/gallancourt.py::_paginar_npc` divide a
  página em abas por `##`, sem mais nenhuma lógica especial de "achar ou juntar" uma ficha
  (isso existia quando a ficha era texto/JSON embutido; não existe mais).
- **Catálogo de Equipamento/Magias/Perícias**: espelha `docs/itens/*.md`/`docs/magias/*.md`/
  `docs/pericias/*.md` (campo `slug_origem` aponta pra página de origem) — essas páginas continuam
  a fonte de leitura/lore, **não foram tocadas** pela migração; o banco é só um espelho consultável
  delas, usado pelo seletor "+ adicionar" na ficha.

## O widget (docs/javascripts/ficha.js)

Sucessor de `monstro-ficha.js` (2026-10-30 → 2026-10-31), mesmo esqueleto (busca ao carregar,
redesenha a cada ação). Duas faixas de abas: a de cima troca entre fichas (Base/variantes, igual
antes); a de baixo troca entre **sete abas de conteúdo** — Atributos (perícias/sentidos/idiomas),
Inventário (equipamento + moeda + carga máxima), Grimório (magias + pools de espaços de magia),
Características (traços/ações/reações), Efeitos (condições de alternar + efeitos aplicados),
Biografia (campos do Personagem) e Diário (lista de entradas, só adicionar/remover nesta versão,
sem editar uma entrada já criada). Reaproveitado sem mudar o padrão: chips com seta +/-, seletor
de catálogo com busca sem perder foco (correção já feita uma vez, mantida), `salvarFicha()` com
salvamento em lote — agora também envia os campos do Personagem (Biografia) num `PUT` separado
quando a aba Biografia tem campos no DOM.

## Acesso: o site é público pra leitura

`admin/app.py::_exigir_login` libera sem login qualquer `GET` em `servir_site` (o site) e nos
prefixos `/api/personagens`, `/api/catalogo`, `/api/auth/` — só escrita (`POST`/`PUT`/`DELETE`) e
o resto do Painel continuam exigindo senha. "Modo Mestre" é a **mesma sessão** do Painel: botão no
**cabeçalho** (injetado por `docs/javascripts/modo-mestre.js`, ao lado do alternador claro/escuro),
abre um **popup** de senha (`POST /api/auth/entrar`/`POST /api/auth/sair`), recarrega a página ao
confirmar.

## Foto do personagem

Uma por `Personagem` (compartilhada entre Base e variantes). `salvar_foto_personagem` grava em
**dois lugares**: `docs/assets/imagens/personagens-ficha/<tipo>-<slug>.<ext>` (fonte, sobrevive a
um `mkdocs build`) e o mesmo caminho em `site/` (pra ficar visível na hora). O nome do arquivo
leva o `tipo` porque slug sozinho não é mais único. **Não confundir** com
`docs/assets/imagens/personagens/` (retrato da caixa de identidade no topo da página de NPC,
`npc.retrato` no front matter — sistema diferente, não tocado).

## O que NÃO fazer

- Não reintroduza a ficha de combate em Markdown/JSON embutido pra monstro/NPC nomeado/jogador —
  isso foi removido de propósito.
- Não migre NPCs genéricos, figurantes de sessão ou a ficha de cidade pra este schema sem o autor
  pedir — continuam em Markdown, de propósito (ver seção "Por que é diferente" acima).
- Não assuma que o site inteiro está atrás de senha em nenhuma lógica nova — só escrita está.
- Não assuma slug globalmente único — sempre filtre por `(tipo, slug)`.
