# Convenções de conteúdo, relações e Compêndio

> Detalhes de referência, separados do `CLAUDE.md` para economizar contexto.
> Leia este arquivo quando for criar ou editar páginas de conteúdo, relações/intrigas ou o Compêndio.

# Convenções das páginas

- Nome de arquivo: minúsculas, sem acentos, com hífens (`louis-de-montclair.md`).
- Toda página começa com front matter de `tags` (usadas no índice de tags).
- Cidades, facções, eventos e sessões têm uma ficha lateral (NPCs usam o bloco `npc:`):
  `<div class="ficha" markdown>` + tabela com cabeçalho vazio (`| | |`).
- Links sempre relativos entre arquivos `.md` (`../cidades/dodixie.md`), nunca URLs do site.
- Toda página nova precisa entrar no `nav` do `mkdocs.yml` e receber links das páginas
  relacionadas (cidade, casa, eventos, índice da seção).
- Diagramas em blocos ` ```mermaid ` (renderizados no navegador, carregados de CDN).

# Relações e intrigas: use o script

As páginas `docs/mundo/relacoes-entre-cidades.md` e `docs/mundo/intrigas-da-nobreza.md`, e os
trechos entre `<!-- inicio:gerado -->` e `<!-- fim:gerado -->` nas páginas de cidades e
personagens, são **gerados** por `scripts/gerar_relacoes.py`. Para mudar uma relação:

1. edite `PARES` (cidades) ou `INTRIGAS` (nobres) no script;
2. rode `python3 scripts/gerar_relacoes.py`;
3. rode `mkdocs build --strict`.

Nunca edite à mão o conteúdo gerado: ele é sobrescrito. Ao renomear um personagem, atualize
também o dicionário `P` e a lista `grupos` do script.

# O Compêndio

`docs/compendio/` repete, em páginas longas, o que está espalhado pela wiki, e acrescenta a
origem de cada informação (siglas V2, V2-r, V1, D). Ao mudar um fato, mude **as duas** versões: a
página da wiki e a página do Compêndio. As tabelas de relações do Compêndio são escritas à mão; a
fonte única continua sendo o script. Divergências e propostas pendentes ficam em
`docs/compendio/pendencias.md`.
