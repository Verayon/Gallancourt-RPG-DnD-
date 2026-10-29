# Páginas de NPC e linha do tempo

> Detalhes de referência, separados do `CLAUDE.md` para economizar contexto.
> Leia este arquivo quando for mexer em NPCs, na tabela de NPCs, na linha do tempo ou em `hooks/`.

# Páginas de NPC

Cada `docs/personagens/<slug>.md` tem um bloco `npc:` no front matter (`titulo`, `raca`, `cidade`,
`afiliacao`, `resumo`, `retrato`, `ficha`) e `hide: [toc]`. O hook `hooks/gallancourt.py`:

- monta, logo abaixo do `# Título`, a caixa com o retrato e as linhas de `ficha` (não escreva a
  antiga `<div class="ficha">` nessas páginas);
- transforma o texto antes do primeiro `##` na aba **Visão geral**, cada `##` em uma aba, e as
  caixas `!!! question "Em aberto"` numa última aba. Por isso as ferramentas que acrescentam
  seções `##` no fim da página (Painel, `gerar_relacoes.py`) continuam funcionando;
- gera a tabela de `personagens/index.md` no lugar de `<!-- npcs:tabela -->`, lendo o bloco `npc:`
  de todas as páginas. `titulo`, `raca`, `cidade`, `afiliacao` e `situacao` são texto simples (viram
  filtros); links vão só em `ficha`. Valor desconhecido = `—`. As colunas Cidade, Afiliação, Título
  e Situação mostram o **estado atual** (com as mudanças da linha do tempo aplicadas).

A biografia simples (gênero/idade/altura/peso/olhos/cabelo/pele/fé, aparência, personalidade,
traço, ideal, vínculo, defeito, proficiências) é escrita pela aba **Biografia** do Painel
(`CAMPOS_FICHA_PERSONAGEM`/`TIPOS_FICHA` em `admin/wiki_data.py`, tipos `"npc"` e `"jogador"`)
como uma seção `## Biografia` normal no corpo da página — não é um bloco de front matter nem uma
aba gerada automaticamente (vira aba sozinha porque o motor de abas transforma qualquer `##` numa
aba). Para NPCs/jogadores de combate, veja a **ficha de combate** (`.stat-block`, marcador
`<!-- dados:statblock ... -->`) em `docs/mestre/manutencao-do-canone.md` — a partir dela também dá
para preencher uma "ficha completa" opcional (perícias/salvaguardas com total calculado,
inventário, grimório, características, efeitos), que vira abas extras (Inventário/Grimório/
Características/Efeitos) na página.

## Linha do tempo (`dados/linha-do-tempo.yml`)

Lista de acontecimentos (`id`, `data` na campanha, `sessao`, `titulo`, `descricao`, `envolvidos`,
`notas` por página, `mudancas` de `situacao`/`cidade`/`afiliacao`/`titulo`). Ordem cronológica pela
data no formato `DD de <mês> de <ano>`; sem data, pela sessão. O hook mostra a seção/aba
**Linha do tempo** em cada página envolvida, a caixa "Situação atual" em cidades/facções, as linhas
"… atual" na caixa do NPC e a página `mestre/linha-do-tempo.md` (`<!-- linha-do-tempo:geral -->`).
O "Registrar sessão" do Painel cria um acontecimento com a nota de cada NPC/lugar marcado — a antiga
seção `## Histórico de sessões` nas páginas não é mais usada.
