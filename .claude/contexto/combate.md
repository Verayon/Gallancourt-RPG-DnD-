# Combat Tracker (iniciativa, PV em combate, XP e loot)

> Detalhes de referência, separados do `CLAUDE.md` para economizar contexto.
> Leia este arquivo antes de mexer em `admin/combate_api.py`, nas tabelas `Combate`/
> `CombateParticipante`/... em `admin/banco.py`, ou em `docs/javascripts/combate.js`.

## Por que existe e o que substituiu

O autor pediu um Combat Tracker de verdade pro Painel do Mestre, pensando em rodar combates à
mesa usando os tokens (monstro/NPC/jogador) que já vivem no banco desde a unificação de 2026-10-31
(ver `.claude/contexto/personagens.md`). Isso **substitui por completo** o antigo "Painel de
Iniciativa" (`admin/sessao_viva.py`, `docs/javascripts/painel-iniciativa.js`,
`docs/javascripts/alternancia-mestre.js`, retirados): aquele sistema guardava estado num JSON por
página (`admin/dados/combates/*.json`), só acessível com o Painel Flask rodando localmente, e
combatentes eram nome/PV digitados à mão, sem vínculo real com nenhuma Ficha.

**Onde vive**: uma aba, **"Master's Shield"** (2026-11-05, nome temporário — ver seção abaixo;
antes se chamava só "Combat Tracker"), dentro da própria página de sessão
(`docs/mestre/sessoes/sessao-N-*.md`), sempre a última da lista de abas (depois de "Segredos do
Mestre") — não é mais um alternador Página normal/Modo Mestre separado. O marcador
`<!-- combate:painel -->` (dentro da aba, ver `admin/wiki_data.py::_modelo_sessao`) vira uma `<div
class="combate-painel ficha-personagem" data-pagina="...">` vazia (mesmo padrão de
`hooks/gallancourt.py::_ficha_dinamica_personagem`) — `docs/javascripts/combate.js` busca
`/api/combate/<pagina>` ao carregar e desenha tudo ali. **GET é público** (leitura livre, como o
resto do site); toda escrita exige a mesma sessão de Modo Mestre que já edita fichas.

## Master's Shield — painel sempre visível por cima do Combat Tracker (2026-11-05, Fase 1)

O projeto passou a ter dois propósitos (Wiki + VTT simplificado pra mesa presencial, sem mapa) —
o Combat Tracker evolui pra esse VTT, batizado **Master's Shield** (nome ainda temporário, o autor
pediu pra adiar o nome final). Diferente do Combat Tracker (que só mostra algo além do botão
"Iniciar combate" quando há um `Combate` ativo), o Master's Shield fica **sempre visível** na
página de sessão — calendário de jogo, localidade atual e um log de interações relacional (ligado
a Fichas/lugares/rolagens, não texto livre), pra permitir consultas depois ("quando", "onde",
"quem", "qual rolagem"). O Combat Tracker continua existindo exatamente como descrito neste
arquivo, só que aninhado visualmente dentro do Master's Shield.

- **Dois marcadores, duas raízes, na mesma aba**: `<!-- sessaoviva:painel -->` (novo, sempre
  injetado por `hooks/gallancourt.py::_sessao_viva_dinamica`, raiz `.sessao-viva-painel`, widget
  `docs/javascripts/sessao_viva.js`) fica **acima** de `<!-- combate:painel -->` (sem mudança —
  continua um `<div>` separado, `combate.js` não foi tocado). Não são pai/filho no DOM — dois
  widgets independentes, cada um buscando sua própria API.
- **Schema novo** (`admin/banco.py`, migração `7b2e4c9a1f6d`): `SessaoAoVivo` (nome temporário —
  uma linha por `pagina_rel_docs`, mesmo padrão de `Combate`; guarda o momento atual
  ano/mes/dia/hora/minuto — `mes` é texto livre, porque `docs/mundo/calendario.md` deixa a duração
  dos meses em aberto de propósito — e `lugar_atual_id`); `Lugar` (local canônico, com
  `pagina_rel_docs` quando já tem página na wiki — importados uma vez de `docs/lugares/*.md` por
  `scripts/importar_lugares.py` — ou provisório, `canonico=False`, criado ao vivo durante a sessão,
  com `lugar_pai_id` apontando pro lugar canônico que o contém; nenhuma automação promove um
  provisório a canônico ainda, isso é revisão manual do Mestre depois da sessão); `Interacao` +
  `InteracaoParticipante` (sempre via `Ficha.id`, nunca `Personagem` direto — mesmo padrão de
  `CombateParticipante`) + `Rolagem` (presa a uma Interacao; `online` distingue dado físico
  digitado vs. rolado pelo próprio sistema em `sessao_viva_api.rolar_online`).
- **`combate_api.distribuir_xp`/`aplicar_loot` agora chamam `sessao_viva_api.registrar_interacao`**
  (tipo `"xp"`/`"loot"`) — antes esses dois eventos não passavam por `registrar_log` nem por
  nenhum outro log, ficavam fora de qualquer rastro consultável.
- **Fora de escopo nesta Fase 1** (ver o plano "Master's Shield — Fase 1"): nenhum botão de
  "fechar sessão" agrega o log ainda pra pré-popular o Diário/linha do tempo
  (`wiki_data.aplicar_sessao`/`registrar_sessao_na_linha_do_tempo`) — isso é a Fase 2, depois que
  esta fundação estiver validada em uso real.

## Cópia (monstro) vs. vínculo real (NPC/jogador) — regra central

Confirmada explicitamente com o autor, é a decisão de schema mais importante deste sistema:

- **Monstro**: ao entrar no tracker, PV/PV temporário/condições vivem numa **cópia isolada**
  (`CombateParticipante.copia_pv_atual`/`copia_pv_temporario` + `CombateParticipanteCondicao`) —
  **nada** toca a `Ficha` real do catálogo. Necessário porque o mesmo monstro-base pode ter várias
  cópias simultâneas no mesmo combate (ex.: "4 a 6 Goblins" da Sessão 1) — se o PV morasse na
  Ficha, todas as cópias compartilhariam o mesmo PV.
- **NPC nomeado e jogador**: únicos, nunca duplicados — o tracker lê e escreve **direto na Ficha
  real** (`Ficha.pv_atual`/`pv_temporario`, `FichaCondicao` de verdade — a mesma que aparece na
  aba Efeitos da ficha). Isso persiste entre sessões **de propósito**: o PV de um jogador no fim de
  uma luta continua lá na próxima sessão, até um **Descanso Longo**.
- Em código, `combate_api._e_copia(participante)` decide o caminho: olha
  `participante.ficha.personagem.tipo == "monstro"`. Toda função que toca PV/condição
  (`ajustar_pv`, `alternar_condicao`, `definir_pv_temporario`) passa por esse branch — não leia só
  a Ficha ou só a cópia, confira sempre o tipo primeiro.
- **Espaços de magia e cargas de item mágico** seguem a mesma regra cópia/real (desde 2026-11-04,
  revertendo a simplificação anterior "monstro não rastreia consumo" — a pedido explícito do
  autor): npc/jogador leem/escrevem direto em `FichaEspacoMagia.usado`/`FichaEquipamento.
  cargas_atual`; monstro usa uma cópia isolada, `CombateParticipanteRecursoCopia` (mesmo princípio
  de `copia_pv_atual`), semeada a partir dos pools da Ficha base em `adicionar_participante` — duas
  cópias simultâneas do mesmo monstro (ex. "Goblin Xamã 1"/"2") gastam seus próprios slots sem
  interferir uma na outra, e nada disso toca a Ficha real do catálogo.

## Descanso Longo e Descanso Curto

`personagens_api.descanso_longo(sessao, ficha)` — só faz sentido pra npc/jogador (monstro no
tracker é sempre uma cópia descartável, não "descansa"). Reseta `pv_atual`→`pv_maximo`,
`pv_temporario`→0, todos os `FichaEspacoMagia.usado`→0, toda `FichaHabilidade.usos_restantes` com
`tipo_descanso` em `("curto", "longo")`→`usos_maximo`, e recupera metade dos dados de vida totais
(aproximação SRD, arredondada pra baixo, mínimo 1 — não modela a escolha de gastar Dados de Vida).
**Não** limpa condições automaticamente — o Mestre remove manualmente as que devem acabar.
Endpoint: `POST /api/personagens/<tipo>/<slug>/fichas/<ficha_id>/descanso-longo`; botão "Descanso
longo" em `docs/javascripts/ficha.js` (`_rodape`), visível só pra fichas de tipo npc/jogador.
`descanso_curto` (mesmo arquivo) é a versão leve — só repõe `usos_restantes` das habilidades com
`tipo_descanso == "curto"`, não toca PV/slots/dados de vida; botão "Descanso curto" ao lado.

## Schema (`admin/banco.py`)

- `Combate(pagina_rel_docs, rodada, turno_participante_id, ativo, criado_em, finalizado_em)` — uma
  página pode ter vários Combates ao longo do tempo (um por encontro); só um fica `ativo` por vez.
  `turno_participante_id` **não** tem `ForeignKey` (evita referência circular dentro da mesma
  migração) — é só um ponteiro de posição, confira sempre se o id ainda existe.
- `CombateParticipante(combate_id, ficha_id, nome_exibicao, iniciativa_base, iniciativa_desempate,
  acao_usada, acao_bonus_usada, reacao_usada, movimento_usado, concentrando_em,
  death_save_sucessos/falhas, copia_pv_atual, copia_pv_temporario)` — `movimento_usado` (desde
  2026-11-05) segue exatamente o mesmo padrão dos outros três flags de economia de ação:
  `_resetar_economia_acao` zera os quatro, só no participante que entra no turno
  (`proximo_turno`); `nome_exibicao` existe porque vários participantes podem
  compartilhar a mesma Ficha de monstro (ex.: "Goblin 1", "Goblin 2"). A ordenação de iniciativa é
  sempre `iniciativa_base + iniciativa_desempate * 0.01` (ver `combate_api._ordem`), nunca
  armazenada — recalculada a cada leitura. `iniciativa_desempate` é preenchido automaticamente ao
  adicionar o participante (`adicionar_participante`, mod. de Destreza da Ficha) — continua editável
  via `atualizar_iniciativa` pra casos especiais (ex.: dote Alerta).
- `CombateParticipanteCondicao(participante_id, nome)` — espelha `FichaCondicao` real quando o
  participante é npc/jogador; fica só aqui quando é monstro.
- `CombateLogEntrada(combate_id, rodada, criado_em, texto, tipo)` — texto pronto pra exibir/
  exportar, não recalculado.

## Encontro planejado (pré-carrega o Combat Tracker)

Desde 2026-11-04: uma página de sessão pode ter vários rascunhos de encontro
(`EncontroPlanejado`/`EncontroParticipantePlanejado` em `admin/banco.py`, lógica isolada em
`admin/encontro_api.py`), montados com antecedência na aba **NPCs** (marcador
`<!-- encontro:planejado -->`, widget `docs/javascripts/encontro.js`) — escolher NPCs/monstros/
jogadores do banco, sem precisar que o combate já exista. `api_iniciar_combate` (`admin/app.py`)
cria o `Combate` normalmente e, se um `encontro_id` veio no corpo, chama
`encontro_api.carregar_no_combate`, que só itera os participantes planejados chamando
`combate_api.adicionar_participante` pra cada um — nenhuma lógica de combate nova, o rascunho é só
uma lista de `ficha_id`/nome de exibição salva antes da hora. O rascunho em si nunca participa do
combate e continua existindo depois (não é apagado ao ser usado). Desde 2026-11-05, a tela "sem
combate" abre esse fluxo como modal (`data-acao="abrir-iniciar-combate"`,
`combate.js::_modalIniciarCombate`, mesma família `.combate-modal` do resumo pós-combate) em vez do
`<select>` solto — cartões clicáveis com nome/contagem/prévia da ordem, sem endpoint novo.

## Recursos consumíveis: bloqueia uso indevido, com opção de forçar

Desde 2026-11-04 (a pedido do autor): conjurar uma magia ou usar um item com carga no Combat
Tracker confere se o recurso existe antes de gastar — `combate_api.conjurar_magia`/
`usar_carga_item`. Sem espaço de magia do nível certo (ou sem carga), a chamada devolve
`{"bloqueado": True, "motivo": "..."}` **sem gravar nada**. Desde 2026-11-05, em vez de um
`window.confirm()`, isso vira `this.bloqueio = {motivo, forcar()}` em `combate.js` e um banner
inline no painel do token (`.combate-painel__bloqueio`, role="alert") com "Cancelar"/"Forçar mesmo
assim" — Forçar chama de novo com `forcar: true`, que ignora o bloqueio e consome mesmo assim (loga
"forçado" na entrada do log). `conjurar_magia` também valida que o nível do espaço escolhido é
suficiente pra magia (`Magia.nivel <= nivel_slot`) — conjurar num espaço maior que o mínimo é
permitido, de propósito. Os outros `window.confirm`/`window.prompt` do arquivo (remover
participante, oferecer reação, teste de morte, checagem de concentração) não entraram nessa
reversão — ficaram como estavam.

Cargas de item mágico (`Equipamento.cargas_maximo`, estático no catálogo; `FichaEquipamento.
cargas_atual`, por instância — `None` = ainda não usado, conta como cheio) só existem quando o
catálogo define `cargas_maximo`; item sem isso continua se comportando como consumível normal
(decrementa `FichaEquipamento.quantidade`, igual a antes). Pra monstro (cópia), a função cai no
mesmo branch de `CombateParticipanteRecursoCopia` usado pra slot de magia — não tenta decrementar
`quantidade` de uma cópia, que não existe.

## Lógica (`admin/combate_api.py`)

Isolado do Flask, como `personagens_api.py`/`wiki_data.py` — toda função recebe uma `Session` já
aberta. Pontos que não são óbvios:

- `pv_atual(participante)`/`pv_temporario(participante)`/`condicoes_ativas(participante)` são os
  helpers que escondem o branch cópia/real — use-os em vez de ler `participante.copia_pv_atual`
  ou `participante.ficha.pv_atual` direto em código novo.
- `ajustar_pv` consome primeiro o PV temporário, só depois o PV atual; cura respeita
  `ficha.pv_maximo` (lido sempre da Ficha real, mesmo pra cópia — o máximo não varia por cópia).
  PV chegando a 0 aplica "Caído" automaticamente; voltar a ter PV > 0 remove "Caído" e zera os
  contadores de teste de morte.
- `proximo_turno` avança a ordem; ao voltar ao topo, incrementa `rodada` e chama
  `_decrementar_duracoes`, que só entende duração numérica em `FichaEfeito.duracao` (ex.: "3
  rodadas") — texto livre não numérico (ex.: "até o fim do combate") não é tocado.
- `oferecer_reacao`/gatilhos de Contramagia e Esquiva Sobrenatural são **manuais** nesta versão —
  o Mestre clica um botão "Oferecer reação" quando sabe que se aplica; não há detecção automática
  (decisão do autor: a prioridade real agora é terminar de preencher dados nas fichas, não
  construir um motor de detecção). Não crie um campo novo em `Habilidade`/`Magia` pra isso sem o
  autor pedir.
- `calcular_resumo_xp` só soma `CR_PARA_XP` de participantes **tipo monstro** mortos — NPC nomeado
  usa nível/XP próprios (sem CR), por isso não entra na soma automática.
- `compilar_loot` só lê participantes **tipo monstro** mortos (nunca escreve na Ficha real deles)
  — não inclui NPC nomeado morto de propósito, pra não esvaziar o inventário de um personagem com
  identidade própria sem uma ação explícita do Mestre. Soma automaticamente uma moeda extra sorteada
  (`_rolar_moeda_por_cr_medio`, usa `random` de verdade) pelo CR médio dos monstros mortos — **não**
  gera itens mágicos aleatórios (exigiria uma tabela de raridade que o projeto não tem; decisão de
  escopo, não esquecimento — amplie quando o autor pedir uma tabela de tesouro de verdade).
- `aplicar_loot` recebe uma lista de escolhas (`modo: "dividir"` soma ÷ nº de jogadores
  participantes, resto fica com o primeiro; `modo: "individual"` exige `ficha_id` do jogador
  escolhido) — sempre escreve direto nas Fichas reais dos jogadores.
- `resolver_resistencia` checa Evasão **pelo nome** — se a Ficha do alvo tiver uma `Habilidade`
  chamada exatamente "Evasão" (case-insensitive) entre suas `habilidades_vinculo`, um sucesso no
  teste zera o dano em vez de reduzir à metade. Não é um campo de schema novo de propósito — reusa
  o catálogo de Habilidades que já existe.

## Widget (`docs/javascripts/combate.js`)

Mesmo esqueleto de `ficha.js`/`roadmap.js`: busca ao carregar, redesenha a cada ação a partir da
resposta (`self.dados` sempre é o objeto `combate` serializado, nunca um estado paralelo). Sem
combate ativo, mostra só um botão "Iniciar combate" (Modo Mestre) ou nada (leitura). Com combate
ativo: lista de cards à esquerda (iniciativa, grade de 15 condições como toggle, checkbox "alvo"
pra marcar quem recebe o próximo ataque/resistência, clique no card troca o "Painel do Token" à
direita), painel do token em foco, formulário de Ataque/Cura manual (d20 físico + bônus + dano,
compara com a CA de cada alvo marcado), modal de Teste de Resistência em área, log de combate
(com export TXT/JSON) e o modal de Resumo Pós-Combate (XP + loot) ao clicar "Encerrar combate".
Testes de morte e concentração usam `window.prompt`/`window.confirm` em vez de um modal próprio —
simplificação deliberada (menos UI pra um fluxo de poucos cliques), reconsidere se o autor achar
confuso na mesa.

## O que NÃO fazer

- Não faça PV/condição de monstro escreverem na Ficha real — quebra a reusabilidade do catálogo
  entre combates.
- Não assuma que `turno_participante_id` sempre aponta pra um participante existente — ele pode
  ter sido removido; confira antes de usar.
- Não tente reaproveitar `admin/sessao_viva.py` nem os JS antigos — foram retirados de propósito;
  se precisar de alguma ideia de lá, releia o histórico do git, não reintroduza os arquivos.
