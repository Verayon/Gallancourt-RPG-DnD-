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

**Onde vive**: uma aba nova, **"Combat Tracker"**, dentro da própria página de sessão
(`docs/mestre/sessoes/sessao-N-*.md`), sempre a última da lista de abas (depois de "Segredos do
Mestre") — não é mais um alternador Página normal/Modo Mestre separado. O marcador
`<!-- combate:painel -->` (dentro da aba, ver `admin/wiki_data.py::_modelo_sessao`) vira uma `<div
class="combate-painel ficha-personagem" data-pagina="...">` vazia (mesmo padrão de
`hooks/gallancourt.py::_ficha_dinamica_personagem`) — `docs/javascripts/combate.js` busca
`/api/combate/<pagina>` ao carregar e desenha tudo ali. **GET é público** (leitura livre, como o
resto do site); toda escrita exige a mesma sessão de Modo Mestre que já edita fichas.

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
- **Espaços de magia e itens consumidos** seguem a mesma regra via as tabelas que a Ficha já tinha
  (`FichaEspacoMagia.usado`, quantidade em `FichaEquipamento`) — só pra npc/jogador, escritos
  direto. Para monstro, esta v1 **não** rastreia consumo de slot/munição durante o combate
  (simplificação assumida; o Mestre acompanha narrativamente se precisar).

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
  acao_usada, acao_bonus_usada, reacao_usada, concentrando_em, death_save_sucessos/falhas,
  copia_pv_atual, copia_pv_temporario)` — `nome_exibicao` existe porque vários participantes podem
  compartilhar a mesma Ficha de monstro (ex.: "Goblin 1", "Goblin 2"). A ordenação de iniciativa é
  sempre `iniciativa_base + iniciativa_desempate * 0.01` (ver `combate_api._ordem`), nunca
  armazenada — recalculada a cada leitura. `iniciativa_desempate` é preenchido automaticamente ao
  adicionar o participante (`adicionar_participante`, mod. de Destreza da Ficha) — continua editável
  via `atualizar_iniciativa` pra casos especiais (ex.: dote Alerta).
- `CombateParticipanteCondicao(participante_id, nome)` — espelha `FichaCondicao` real quando o
  participante é npc/jogador; fica só aqui quando é monstro.
- `CombateLogEntrada(combate_id, rodada, criado_em, texto, tipo)` — texto pronto pra exibir/
  exportar, não recalculado.

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
