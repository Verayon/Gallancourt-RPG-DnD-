# Identidade visual e navegação do site

> Detalhes de referência, separados do `CLAUDE.md` para economizar contexto.
> Leia este arquivo quando for mexer em CSS, layout, menu, cartões ou criar páginas de listagem.

# Identidade visual ("High Fantasy")

O site tem um padrão visual próprio, definido em `docs/stylesheets/extra.css`. Ao criar páginas
novas, siga-o em vez do visual padrão do Material.

- **Navegação (decidida pelo autor):** 6 itens de topo na barra lateral, nesta ordem —
  **Início** (`index.md`), **Lore** (`lore/index.md` + Gallancourt em uma página + Crônica em
  capítulos), **Wiki** (`wiki/index.md` + Mundo, Geografia, Cidades, Facções, **NPCs**, Eventos),
  **Compêndio**, **Mestre** (`mestre/index.md` + Sessões, Diário de Sessões, Referência rápida) e
  **Configurações** (`configuracoes/index.md` + Painel, registro manual, manutenção do cânone,
  lacunas, inconsistências, fontes, tags). A seção de personagens se chama **NPCs** no site (a
  pasta continua `personagens/`). `navigation.tabs` e `navigation.sections` ficam **desligados**:
  toda seção é uma barra que abre e fecha, com a seta dentro da própria barra.
- **Barra lateral:** itens finos, só com contorno (sem fundo), seta integrada na barra — regras
  na seção 4 do `extra.css`. Não volte às "caixas dentro de caixas".
- **A Lore é só narrativa.** `lore/index.md` conta a história como uma crônica contínua, sem `<sup>`,
  sem `!!!` (admonições) e sem links de referência — é para ler como um livro. A versão anotada,
  com a origem de cada fato nas fontes (V1/V2/dossiê) e as caixas de "em aberto"/"divergência",
  mora em `compendio/historia-de-gallancourt.md` e faz parte do Compêndio, não da Lore. Ao
  atualizar a história, atualize as duas, cada uma no seu registro.
- **Cartões com imagem.** Toda página de listagem (índices de Cidades, Personagens, Facções,
  Eventos, Geografia, Mundo, Mestre, Compêndio) usa cartões de imagem clicável, não tabelas:
  ```markdown
  -   [![](../assets/placeholders/<categoria>.svg){ .card-portrait }](destino.md)

      **[Título](destino.md)**

      Descrição curta de uma ou duas linhas.
  ```
  Categorias disponíveis em `docs/assets/placeholders/`: `cidade`, `personagem`, `casa`,
  `estado`, `organizacao`, `evento`, `geografia`, `tema`. Use a mesma moldura em todos os cartões
  do mesmo tipo até existir uma imagem real. Imagens de verdade vão em `docs/assets/imagens/`
  (convenção em `docs/assets/imagens/LEIA-ME.txt`); ao adicionar uma, troque o `src` do cartão
  correspondente (e, se fizer sentido, a ficha da página de detalhe).
- **Fontes:** títulos em **Cinzel** (`Cinzel Decorative` só no herói/logo); corpo de texto em
  **EB Garamond**. Carregadas via `@import` do Google Fonts no topo do `extra.css`
  (`theme.font: false` no `mkdocs.yml` evita que o Material baixe Roboto por cima).
  Ícones de portal usam a sintaxe `:material-<nome>:` (requer `pymdownx.emoji` já configurado).
- **Paleta:** duas variantes com nomes próprios — **Grimório** (escura, `slate`, padrão) e
  **Pergaminho** (clara, `default`). Definidas como variáveis `--gc-*` e sobrepostas às variáveis
  do Material em `[data-md-color-scheme="slate"]` / `[data-md-color-scheme="default"]`. Dourado
  (`--gc-gold`) é o acento; roxo profundo é a cor primária do cabeçalho.
- **Classes utilitárias para conteúdo:**
  - `.hero` — banner de capa com imagem de fundo (`docs/assets/hero-bg.svg`), usado só no
    `index.md`. Para trocar por uma arte real da campanha, salve o arquivo em `docs/assets/` e
    troque a `url(...)` da regra `.hero` no `extra.css`.
  - `.lore-scroll` — envolve o corpo da página de Lore: leitura em coluna estreita, capitular na
    primeira letra, divisores ornamentais antes de cada `##`. Não aplique a páginas de referência
    (tabelas ficam apertadas nessa largura).
  - `.wiki-portal` — envolve o hub `wiki/index.md`.
- Favicon: `docs/assets/favicon.svg`. Logo do tema: ícone `material/sword-cross`.
