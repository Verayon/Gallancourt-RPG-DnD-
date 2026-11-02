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

Desde 2026-10-31, a Biografia de NPC/jogador **não** é mais escrita pelo Painel — é uma aba do
widget de ficha de combate (`docs/javascripts/ficha.js`), com os dados no banco (`Personagem` em
`admin/banco.py`), editável direto na página em Modo Mestre, junto com Atributos/Inventário/
Grimório/Características/Efeitos/Diário na mesma ficha. `CAMPOS_FICHA_PERSONAGEM`
(`admin/wiki_data.py`) continua existindo só como referência (é o que as colunas de `Personagem`
espelham); `TIPOS_FICHA` não tem mais `"npc"`/`"jogador"`. Ver `.claude/contexto/personagens.md`
antes de mexer em qualquer coisa relacionada à ficha de combate de NPC/jogador.

## Linha do tempo (`dados/linha-do-tempo.yml`)

Lista de acontecimentos (`id`, `data` na campanha, `sessao`, `titulo`, `descricao`, `envolvidos`,
`notas` por página, `mudancas` de `situacao`/`cidade`/`afiliacao`/`titulo`). Ordem cronológica pela
data no formato `DD de <mês> de <ano>`; sem data, pela sessão. O hook mostra a seção/aba
**Linha do tempo** em cada página envolvida, a caixa "Situação atual" em cidades/facções, as linhas
"… atual" na caixa do NPC e a página `mestre/linha-do-tempo.md` (`<!-- linha-do-tempo:geral -->`).
O "Registrar sessão" do Painel cria um acontecimento com a nota de cada NPC/lugar marcado — a antiga
seção `## Histórico de sessões` nas páginas não é mais usada.
