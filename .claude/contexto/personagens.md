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
  `classe`/`subclasse`/`antecedente` são rótulos livres de cabeçalho, não multiclasse estruturado
  (o "motor de regras" que precisaria disso ainda não existe). `deslocamento_m` é número (passo de
  1,5 m no editor); `deslocamento_extra` (texto livre) cobre voo/escavar/nadar etc.
  `percepcao_passiva`/`investigacao_passiva`/`intuicao_passiva` (inteiros) são colunas próprias —
  todo personagem tem as três, não são um "sentido" escolhido (ver `Sentido` abaixo, que é só pra
  sentidos especiais de alcance). `iniciativa_extra` soma ao modificador de Destreza na exibição
  (não um total já pronto). `cd_conjuracao`/`bonus_ataque_magico` (inteiros nulos até o Mestre
  preencher) são números prontos, igual a `ca_total` — não calculados de classe/nível/atributo.
  `pv_temporario`/`dados_vida_total`/`dados_vida_usados`/`carga_maxima`/5 colunas de moeda
  (`moeda_pc/pp/pe/po/pl`) completam o cabeçalho da ficha. `carga_maxima` nulo = o widget usa o
  padrão SRD (2× Força) só pra exibir o total atual (soma de `peso_kg × quantidade` do inventário)
  e alertar sobrecarga — nunca grava esse cálculo no banco.
- **Catálogos compartilhados**, reutilizáveis entre fichas de qualquer tipo:
  `Equipamento`/`Magia`/`Habilidade`/`Idioma`/`Sentido`/`Pericia`, vinculados por tabelas de
  associação próprias (`FichaEquipamento` tem `quantidade`/`equipado`; `FichaSentido` tem `valor`
  **numérico** em metros — o mesmo sentido tem alcance diferente por personagem, ex. Visão no
  escuro 9 m vs. 36 m; `FichaPericia` tem `bonus` (inteiro, **pode ser negativo**) — o bônus final
  já pronto pra rolar, não calculado de atributo+proficiência, igual a `ca_total`). `Equipamento`
  tem `peso_kg` **numérico** (não texto) — converte sem perda a partir dos dados reais, que já
  seguiam o padrão "`<número> kg`". `origem_tipo`/`origem_personagem_slug` marcam o que nasceu
  exclusivo de um personagem (sem página própria), pra poder filtrar por origem no seletor.
  `FichaEquipamento`/`FichaHabilidade`/`FichaMagia` (o vínculo, não o catálogo) têm `favorito`
  (bool — acesso rápido, `serializar_ficha` ordena favoritos primeiro em todos os três); a aba
  Atributos do widget agrega os três num painel "★ Favoritos" (ver seção do widget abaixo).
  `FichaHabilidade` também tem `usos_maximo`/`usos_restantes`/`tipo_descanso` (contador real de uso
  por descanso, validado contra `banco.TIPOS_DESCANSO` — nulos = sem contador, só o texto livre de
  `Habilidade.usos`). `favorito`/contadores de uso são por ficha, não por item de catálogo, porque
  o mesmo item pode estar favoritado numa ficha e não na outra.
- `Equipamento`/`Magia`/`Habilidade` (o catálogo, não o vínculo) têm `tipo_acao` (`banco.TIPOS_ACAO`
  — `"acao"|"acao_bonus"|"reacao"|"nenhuma"`), preenchido uma vez por `scripts/preencher_tipo_acao.py`
  (parse de `Magia.tempo`/mapeamento de `Habilidade.tipo`/presença de `dano_formula` em
  Equipamento) e editável depois como qualquer outro campo do catálogo. Alimenta só o filtro da
  lista de Favoritos — não entra na economia de ação do Combat Tracker (ver
  `.claude/contexto/combate.md`), que continua manual.
- `Equipamento` também tem `cargas_maximo` (desde 2026-11-04, `None` = item sem cargas, consumível
  normal via `FichaEquipamento.quantidade`) — definição estática do catálogo (ex.: Varinha de
  Mísseis Mágicos = 7). A quantidade restante de cada instância é `FichaEquipamento.cargas_atual`
  (`None` = ainda cheio); o Combat Tracker é quem gasta cargas de verdade (ver
  `.claude/contexto/combate.md`, "Recursos consumíveis") — reverteu a decisão antiga de "monstro
  não rastreia consumo", a pedido do autor.
- **Cantêineres** (desde 2026-11-05, a pedido do autor ao implementar o design novo da ficha):
  `Equipamento.e_container` (bool) + `Equipamento.capacidade_kg` marcam um item do catálogo como
  cantêiner (Mochila, Bolsa de Componentes...) — cresce pelo mesmo picker "criar no catálogo" que
  já existe, sem rota nova. `FichaEquipamento.guardado_em_vinculo_id` é autorreferencial: aponta
  pro `FichaEquipamento.id` (da mesma ficha) que guarda este item; `None` = solto. `PUT
  /api/fichas/<id>/equipamentos/<vinculo>` (`admin/personagens_api.py::atualizar_vinculo_equipamento`)
  é a única rota que edita `quantidade`/`equipado`/`guardado_em_vinculo_id` depois que o item já
  foi adicionado (antes só dava pra definir uma vez, em `adicionar_vinculo`); passar da capacidade
  do cantêiner **avisa** (`{"aviso": "..."}`), não bloqueia — decisão de UX do próprio design,
  diferente do padrão bloqueia-com-forçar usado em recurso de combate.
- **Não são catálogos** — próprios de cada `Ficha`, sem valor de reuso entre personagens:
  `FichaEspacoMagia` (pool de espaços de magia: `nivel`/`maximo`/`usado`/`rotulo` — `rotulo`
  distingue dois pools no mesmo nível, ex. espaços normais vs. Magia de Pacto de um Bruxo);
  `FichaCondicao` (`nome` validado contra a lista fixa `banco.CONDICOES_D20`, as 15 condições do
  5e — não é um catálogo no banco, é um conjunto fechado de regras); `FichaEfeito`
  (`nome`/`tipo`/`origem`/`duracao`, `tipo` validado contra `banco.TIPOS_EFEITO`);
  `FichaResistenciaDano` (`nome` validado contra `banco.TIPOS_DANO`, os 13 tipos de dano do 5e;
  `modo` validado contra `banco.MODOS_RESISTENCIA_DANO` — `"imune"|"resistente"|"vulneravel"`, só
  um ativo por tipo de dano por ficha, alternado por `alternar_resistencia_dano`). Informativo —
  não entra na matemática de dano do Combat Tracker (ver `.claude/contexto/combate.md`).
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

## Motor de nível (Classe/Subclasse/ClasseFeature/FichaClasse)

Desde 2026-11-04, a pedido explícito do autor: reabre a decisão "classe/subclasse são rótulo
livre, sem motor de regras" descrita acima — só pra quem usar o botão **"⇧ Subir de nível"** no
cabeçalho da ficha (não é retroativo nem obrigatório; `Ficha.classe`/`subclasse`/`nivel` continuam
editáveis como texto livre em paralelo, pra NPCs ou personagens que não usem o motor).

- `Classe` (catálogo novo: `nome`, `dado_vida` 6/8/10/12, `atributo_conjuracao` opcional,
  `progressao_conjuracao` opcional — `"completo"|"meio"|"terco"|"pacto"`, ver
  `banco.PROGRESSOES_CONJURACAO`) e `Subclasse` (vinculada a uma Classe) **crescem sob demanda** —
  não há seed de todas as classes do PHB; o Mestre cria a Classe/Subclasse a primeira vez que
  precisa dela, direto no painel de "Subir de nível" (`+ nova classe no catálogo`). Sem rota de
  editar/excluir, mesmo padrão já usado por Equipamento/Magia/Habilidade (só cresce).
- `ClasseFeature` (classe_id, subclasse_id opcional, nivel, nome, descricao) é **opcional** — uma
  classe sem nenhuma cadastrada funciona normalmente pra PV/bônus de proficiência/slots, só não
  desbloqueia `Habilidade` nenhuma sozinha. Ao subir de nível, cada feature do nível vira
  (get-or-create) uma `Habilidade` com `origem_tipo="classe"` + `FichaHabilidade` vinculada — não
  tenta automatizar contadores de uso por feature (o Mestre ajusta `usos_maximo`/`tipo_descanso`
  manualmente depois, como qualquer outra Habilidade).
- `FichaClasse` (ficha_id, classe_id, subclasse_id opcional, nivel) — uma linha por classe que a
  ficha tem (multiclasse = várias linhas). `personagens_api.subir_de_nivel` faz tudo isso numa
  chamada: soma 1 no nível daquela classe (ou cria a linha, se for a primeira vez), recalcula
  `Ficha.nivel` (soma de todas as classes), `bonus_proficiencia` (tabela universal por nível total
  — `banco.bonus_proficiencia_por_nivel`, igual pra qualquer classe/combinação), PV (média do dado
  de vida + mod. de Constituição, ou um valor exato que o Mestre informar — pra quando rola o dado
  físico), espaços de magia (`recalcular_espacos_magia` — conjurador completo conta o nível
  inteiro, meio conta nível÷2, terço conta nível÷3, a soma consulta
  `banco.TABELA_SLOTS_CONJURADOR_COMPLETO`, regra padrão de multiclasse do 5e SRD; Magia de Pacto
  do Bruxo é um pool à parte, `rotulo="Pacto"`, via `banco.TABELA_SLOTS_PACTO_BRUXO`) e features
  novas. Também reescreve o texto derivado `Ficha.classe`/`subclasse` (ex. "Guerreiro 3 / Mago 2"),
  pra quem só olha esses dois campos continuar vendo a informação certa.
- `GET /api/classes` é público (lista com subclasses aninhadas); `POST /api/classes`,
  `POST /api/classes/<id>/subclasses` e `POST /api/personagens/<tipo>/<slug>/fichas/<id>/subir-
  nivel` exigem Modo Mestre, mesmo padrão do resto da API de personagens.

## Importação em massa dos livros (2026-11-05)

A pedido do autor, os catálogos deixaram de crescer só sob demanda nesta rodada — foram semeados
em massa a partir dos livros já convertidos em `referencias/pdfs/md/*.md` (ver
`scripts/importar_*.py`, todos one-off e idempotentes, casam por nome antes de criar):

- **`Raca`/`RacaTraco`** (tabela nova — não existia nenhum conceito de raça estruturado antes
  disso) — `scripts/importar_racas_livro.py`, parseando o capítulo de raças do Livro do Jogador
  convertido. Sub-raça é a mesma tabela (`raca_pai_id` apontando pra raça base), sem tabela
  separada. `Ficha.raca_id` (FK opcional, aditivo) ainda não é preenchido automaticamente em
  nenhuma ficha — fica disponível pra quando o motor de nível/criação de ficha for usar.
- **`fonte_id`** (FK pra `Fonte`, antes só um nome de tabela sem uso) foi ligado a `Equipamento`/
  `Magia`/`Habilidade`/`Pericia`/`Classe`, ao lado do `fonte` de texto livre que já existia (não
  removido). `Fonte.importado_em`/`arquivo_origem` registram **quais livros já alimentaram os
  catálogos** — consulte `banco.listar_fontes` pra ver o status.
- **Magias (417) e Itens (259)**: `scripts/importar_magias_wiki.py`/`importar_itens_wiki.py` não
  leem o livro convertido — leem o bloco `magia:`/`item:` já estruturado de cada página em
  `docs/magias/*.md`/`docs/itens/*.md` (fonte mais confiável que reprocessar o PDF).
- **Classes**: `scripts/importar_classes_livro.py` semeia só `Classe` (dado de vida, atributo/
  progressão de conjuração) das 12 classes do Livro do Jogador 2014. **`ClasseFeature`/
  `Subclasse` continuam crescendo sob demanda, como antes** — a tabela de progressão por nível do
  livro convertido saiu do Docling com cabeçalhos diferentes por classe (conjuradores têm colunas
  de espaços de magia mangled de formas distintas); não valeu o risco de atribuir uma
  característica ao nível errado numa referência de regras.
- **Monstros**: `scripts/importar_monstros_livro.py` leu os stat blocks do Manual dos Monstros
  convertido e criou 58 `Personagem`(tipo="monstro")/`Ficha` novos (dos 98 que já existiam antes
  desta rodada, foram ignorados — nunca sobrescreve um slug já em uso) + a página mínima em
  `docs/monstros/<slug>.md` quando não existia. Stat blocks corrompidos por um artefato do Docling
  (tabela de 6 colunas com cabeçalho/CA/PV duplicados) foram listados em
  `referencias/pdfs/md/monstros-nao-importados.md` em vez de entrar com dado errado — e uma boa
  fração do livro (famílias de monstros como "Goblins") usa uma sub-estrutura que esta primeira
  passada não reconhece, então o catálogo ainda está bem abaixo do total do livro.
- **Guia de Xanathar não foi processado nesta rodada** — o markdown convertido saiu com corrupção
  de caracteres generalizada (`Fonte.importado_em` continua `None` pra ele de propósito); precisa
  de uma reconversão/limpeza antes de alimentar qualquer catálogo com segurança.

## O widget (docs/javascripts/ficha.js)

Sucessor de `monstro-ficha.js` (2026-10-30 → 2026-10-31), mesmo esqueleto (busca ao carregar,
redesenha a cada ação). Duas faixas de abas: a de cima troca entre fichas (Base/variantes, igual
antes); a de baixo troca entre **sete abas de conteúdo** — Atributos (★ Favoritos, perícias,
sentidos, idiomas, resistências a dano), Inventário (equipamento + moeda + carga máxima), Grimório
(magias + pools de espaços de magia), Características (traços/ações/reações), Efeitos (condições
de alternar + efeitos aplicados), Biografia (campos do Personagem) e Diário (lista de entradas, só
adicionar/remover nesta versão, sem editar uma entrada já criada). Reaproveitado sem mudar o
padrão: chips com seta +/-, seletor de catálogo com busca sem perder foco (correção já feita uma
vez, mantida), `salvarFicha()` com salvamento em lote — agora também envia os campos do Personagem
(Biografia) num `PUT` separado quando a aba Biografia tem campos no DOM.

Desde a reforma visual estilo D&D Beyond (2026-11-04): a grade dos 6 atributos (`_atributosGrid`)
saiu de dentro da aba Atributos e passou a morar no `_cartao` (cabeçalho do stat-block), sempre
visível independente da aba de conteúdo ativa, ao lado de uma barra de PV colorida (`_barraPv` —
mesmo cálculo de faixa ok/ferido/crítico de `docs/javascripts/combate.js::barraPv`, duplicado por
não haver módulos JS no projeto, não compartilhado). A aba Atributos abre com `_listaFavoritos`: os
itens de `equipamentos`/`magias`/`habilidades` com `favorito=true`, agrupados por catálogo, com uma
fileira de filtro (Todas/Ação/Ação Bônus/Reação) sobre `tipo_acao`. Vale pros três tipos de
personagem (`this.tipo === "monstro"` só muda os chips do topo, não essa estrutura) — padronização
pedida pelo autor. Desde 2026-11-04, npc/jogador (não monstro) ganham um botão "⇧ Subir de nível"
ao lado dos chips, que abre um painel inline (`_painelNivel`, mesmo padrão visual do
`ficha-personagem__picker`) pra escolher/criar Classe+Subclasse e confirmar — ver "Motor de nível"
acima.

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
