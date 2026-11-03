# CLAUDE.md

Wiki de lore da campanha de D&D 5e **Crônicas de Gallancourt** (MkDocs Material). Conteúdo e
conversa em **português do Brasil**; nomes franceses mantêm os acentos (Baie de l'Éclair,
L'Ordre de Célestien, Magnetér).

## Comandos

```bash
mkdocs build --strict                 # validação rápida (links, âncoras, menu)
python scripts/testar_site.py         # teste completo e fixo — ou o comando /testar-site
python scripts/gerar_relacoes.py      # regenera relações entre cidades e intrigas
python admin/app.py                   # site + Painel do Mestre juntos, :5001 (um servidor só)
mkdocs serve                          # opcional: só recarga automática ao editar .md, :8000
pytest                                # testes do banco de dados (tests/) — ver ARQUITETURA.md
alembic upgrade head                  # cria/atualiza dados/gallancourt.db (rodar uma vez após clonar)
```

`MANUTENCAO.md` é o manual do autor (comandos, rotina, problemas); ao mudar como o projeto é
operado, atualize-o junto.

O Painel pode ficar acessível fora de `127.0.0.1` (ver `PAINEL_HOST`/`PAINEL_HTTPS` em
`admin/app.py`) — hoje o site também fica acessível publicamente via Cloudflare Tunnel (link
temporário, muda a cada reinício do túnel — ver item de Roadmap sobre domínio fixo). **O site é
público para leitura** mesmo com `PAINEL_SENHA` definida — só escrita (Painel inteiro, e qualquer
`POST`/`PUT`/`DELETE` de API) exige login. "Modo Mestre" (botão no cabeçalho, popup de senha) usa essa
mesma sessão/senha — ver `.claude/contexto/personagens.md`. O Roadmap (`docs/roadmap/index.md`) também é
editável (adicionar/editar/excluir, com responsável opcional) direto na página em Modo Mestre, sem
precisar do Painel nem de `mkdocs build` — a API é `/api/roadmap` (`admin/app.py`), lendo/escrevendo
`dados/roadmap.yml` (`hooks/roadmap.py`); o menu da esquerda só mostra as categorias principais —
subcategorias se acessam clicando no corpo da página da categoria (padrão já usado por Monstros).

**Changelog sempre atualizado:** ao final de qualquer sessão que mude algo visível ao autor/jogadores
(feature nova, mudança de comportamento, correção notável), acrescente uma versão em
`dados/changelog.yml` antes de concluir — é a única forma de quem acompanha o site saber o que mudou.

## Onde está cada coisa

| Caminho | O quê |
|---|---|
| `docs/` | O site. Menu: Início, Lore, Wiki (Mundo, Geografia, Cidades, Lugares, Facções, NPCs=`personagens/`, Eventos), Compêndio, Mestre (sessões, jogadores, diário, linha do tempo), Configurações |
| `hooks/` | Código que roda no build: `gallancourt.py` (NPCs, tabelas, abas), `linha_tempo.py` |
| `admin/` | Painel do Mestre (Flask local) — cria NPCs, sessões, fichas, acontecimentos |
| `admin/painel_local.env` | Segredos locais do Painel (`PAINEL_SENHA` de login) — gitignorado, nunca commitado; sem ele o login fica desligado (uso só local) |
| `admin/banco.py` + `alembic/` | Banco SQLite (`dados/gallancourt.db`, gitignorado) — Campanha/Fontes e, desde 2026-10-31, a ficha de combate de monstros, NPCs nomeados e jogadores (ver `.claude/contexto/personagens.md`) |
| `admin/personagens_api.py` | Leitura/escrita das fichas de personagem no banco — isolado do Flask, como `wiki_data.py` |
| `admin/combate_api.py` | Combat Tracker (iniciativa, PV, condições, XP/loot) — ver `.claude/contexto/combate.md` |
| `tests/` | Testes `pytest` do banco de dados (único teste de "regra"/estado hoje; `scripts/testar_site.py` é integração de site) |
| `dados/linha-do-tempo.yml` | Acontecimentos da campanha (fonte única) |
| `dados/changelog.yml` | Versões do site (ver `hooks/changelog.py`). Acrescente com `scripts/registrar_changelog.py` (sem precisar do Painel) |
| `dados/roadmap.yml` | O que falta fazer (ver `hooks/roadmap.py`). Leia/edite direto o YAML, ou chame `wd.salvar_item_roadmap`/`wd.apagar_item_roadmap` (`admin/wiki_data.py`) — mesma função usada pelo widget em Modo Mestre na página `/roadmap/` |
| `dados/bugs.yml` | Bugs reportados pelo botão "🐞 Reportar bug" de qualquer página (ver `hooks/bugs.py`) |
| `scripts/` | `gerar_relacoes.py` (fonte única das relações), `testar_site.py` (teste fixo), `registrar_changelog.py` (changelog sem o Painel) |
| `fontes/` | Acervo do autor — **não editar**; guia em `fontes/README.md` |

**Antes de mexer numa área, leia só o arquivo de contexto dela:**

| Vai mexer em… | Leia |
|---|---|
| CSS, layout, menu, cartões, páginas de listagem | `.claude/contexto/visual.md` |
| NPCs, tabela de NPCs, ficha 5e, linha do tempo, `hooks/` | `.claude/contexto/npcs.md` |
| Painel, Diário, sessões, calendário | `.claude/contexto/sessoes-e-painel.md` |
| Páginas de conteúdo, relações/intrigas, Compêndio | `.claude/contexto/conteudo.md` |
| Banco de dados (`admin/banco.py`, Alembic, o que migrar ou não) | `.claude/contexto/banco-de-dados.md` |
| Fichas de personagem (monstro/NPC/jogador), variantes, Modo Mestre, catálogos compartilhados | `.claude/contexto/personagens.md` |
| Combat Tracker (aba das páginas de sessão), iniciativa, PV em combate, XP/loot | `.claude/contexto/combate.md` |

## Regras do projeto (decididas pelo autor)

1. **Só conteúdo pré-campanha** nas páginas do mundo. Planos de campanha, ganchos e finais não
   entram (seção "Campanha" removida a pedido; recuperável no commit `047b0af`). Material de mesa
   mora em Mestre → Sessões.
2. **Precedência das fontes:** `fontes/textos/Historia_Gallancourt.pdf` (Versão 2; transcrição
   `cronicas-de-gallancourt-v2.md`) > Versão 1 (`cronicas-de-gallancourt-v1.md`) e
   `Gallancourt_Dossie_Geral_Expandido.md`. No PDF, págs. 1–8 (revisadas) > 9–17 (rascunhos).
   A posição da Versão 1 frente ao dossiê aguarda o autor (`docs/compendio/pendencias.md`).
3. **Nunca invente fatos como cânone.** Texto corrido = cânone; `!!! info "Leitura cartográfica"`;
   `!!! abstract "Inferência funcional"`; `!!! question "Em aberto"`. Nunca invente valores de ficha
   5e para NPCs do cânone.
4. **Marcas:** `CANON`, `PLANEJADO`, `POSSIBILIDADE` (proposta sua), `SEGREDO`, `DESCONHECIDO`,
   `CONSEQUÊNCIA`. Proposta nova é `POSSIBILIDADE`; só o autor promove a `CANON`.
5. **Divergência entre fontes:** pergunte ao autor e registre em `docs/mestre/inconsistencias.md`.
6. **Segredos** em `!!! warning "SEGREDO"` ou marca inline; separar antes de mostrar aos jogadores.

## Decisões já tomadas

Estado ocidental = **Gallancourt**, governado pela **Aliança dos Lordes** via **Conseil des
Seigneurs** · Torre do Trovão: **Arquimago Elian Lumière** (não Kaelen Thorne); **Duque Jeanesse
Lumière** chefia a casa · Guilda naval: **Mestre Louis de Montclair** (não Bromli) · **Ano de
Sangue** (não Mês) · **Marquesa** Scyras, pai traído por aristocratas da capital · **Lorde** Alfonse
Enry; massacre recente, obra de L'Ordre · Thibault de la Rivière: traidor **infiltrado** · Henri du
Valois: idealista disfarçado · títulos dos rascunhos antigos não adotados. Perguntas abertas:
`docs/mestre/lacunas.md`.

## Economia de tokens

- **Não abra os originais grandes** de `fontes/` (PDF, imagens de 3–29 MB): use as transcrições `.md`.
- **Busque antes de ler:** `grep -rn` pelo nome ou termo e leia só o trecho; não percorra páginas
  inteiras nem a pasta `docs/` em sequência.
- **Prefira os scripts e o Painel** a editar muitos arquivos à mão: relações → `gerar_relacoes.py`;
  NPC, sessão e acontecimento → funções de `admin/wiki_data.py`.
- **Validação:** `mkdocs build --strict` durante o trabalho; o teste completo só quando o autor
  pedir (`/testar-site`). Da saída, leia só o resumo e as linhas ❌.
- **Testes só quando o autor pedir — igual a commit/push.** Pedido de implementação, ajuste ou
  alteração entrega só o que foi pedido: nada de `pytest`, escrever testes novos ou rodar
  `/testar-site` por conta própria. Só roda quando o autor pedir explicitamente (ou quando a tarefa
  pedida for literalmente escrever/rodar testes).
- **Changelog: registre sempre, sem precisar pedir** — é o oposto da regra de testes/commit. Ao
  terminar qualquer mudança (implementação, remoção, ajuste, correção de bug), rode
  `python scripts/registrar_changelog.py <versao> <data> "<mudança 1>" ["<mudança 2>" ...]`
  (escreve direto em `dados/changelog.yml`, sem precisar do Painel rodando). Versão: incremente o
  último número em 0.1 (ex.: 0.4 → 0.5), a menos que o autor peça outro número.
- **Markdown/YAML continuam sendo a fonte de verdade de tudo que já existe** (lore, ficha de
  planejamento de NPC, Changelog/Roadmap/linha do tempo) — não migre nada disso pro banco
  (`admin/banco.py`) sem o autor pedir explicitamente; ver `ARQUITETURA.md` pro porquê. **Exceção:
  a ficha de combate** de monstro/NPC nomeado/jogador (`Personagem`/`Ficha` em `admin/banco.py`) —
  essa já vive no banco desde 2026-10-31, de propósito; ver `.claude/contexto/personagens.md`
  antes de mexer ali. NPCs genéricos, figurantes de sessão e a ficha de cidade continuam no
  sistema antigo (Markdown/JSON embutido), também de propósito.
- **Respostas curtas** ao autor: o que mudou, onde, e o que ele precisa decidir.

## Comandos do projeto (skills em `.claude/skills/`)

- `/testar-site` — roda o teste fixo e resume o resultado (só quando o autor pedir).
- `/incorporar-documento <arquivo>` — compara um texto novo do autor com a wiki e incorpora.
- `/nova-pagina <tipo> <assunto>` — cria cidade, evento, facção, NPC ou lugar no padrão do site.

Antes de commitar: `mkdocs build --strict` sem avisos. Commits e push só no branch de trabalho.
