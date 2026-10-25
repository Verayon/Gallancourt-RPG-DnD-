# Páginas de NPC, ficha de D&D 5e e linha do tempo

> Detalhes de referência, separados do `CLAUDE.md` para economizar contexto.
> Leia este arquivo quando for mexer em NPCs, na tabela de NPCs, na ficha 5e, na linha do tempo ou em `hooks/`.

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
  e Situação mostram o **estado atual** (com as mudanças da linha do tempo aplicadas) e a coluna
  Nível vem de `ficha5e.nivel`.

## Ficha de D&D 5e (`ficha5e:`)

Bloco opcional no front matter do NPC, escrito pela aba **Ficha de NPC** do Painel (`/ficha5e`) ou
ao criar o NPC. Guarda só valores digitados (atributos, perícias com nível 0/1/2, CA, PV, ataques,
equipamento, magias por nível, personalidade, detalhes); o hook calcula modificadores, proficiência
pelo nível, resistências, perícias, percepção passiva, iniciativa, CD e ataque de magia e monta a
aba **Ficha de personagem**. Campos, rótulos e fórmulas ficam só em `hooks/ficha5e.py` — para
acrescentar um campo, mude ali (formulário do Painel e exibição usam as mesmas listas). **Nunca
invente valores de ficha para NPCs do cânone**: só o autor preenche.

## Linha do tempo (`dados/linha-do-tempo.yml`)

Lista de acontecimentos (`id`, `data` na campanha, `sessao`, `titulo`, `descricao`, `envolvidos`,
`notas` por página, `mudancas` de `situacao`/`cidade`/`afiliacao`/`titulo`). Ordem cronológica pela
data no formato `DD de <mês> de <ano>`; sem data, pela sessão. O hook mostra a seção/aba
**Linha do tempo** em cada página envolvida, a caixa "Situação atual" em cidades/facções, as linhas
"… atual" na caixa do NPC e a página `mestre/linha-do-tempo.md` (`<!-- linha-do-tempo:geral -->`).
O "Registrar sessão" do Painel cria um acontecimento com a nota de cada NPC/lugar marcado — a antiga
seção `## Histórico de sessões` nas páginas não é mais usada.
