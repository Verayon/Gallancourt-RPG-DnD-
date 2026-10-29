---
name: nova-pagina
description: Cria uma página nova na wiki de Gallancourt (cidade, evento, facção, NPC, lugar/geografia ou tema do Mundo) seguindo o padrão do site, com menu, índice e links. Use quando o autor pedir para adicionar algo novo ao site pelo chat.
argument-hint: "<tipo> <assunto e informações>"
---

# Criar uma página nova

Pedido: `$ARGUMENTS`

**Use só o que o autor informou.** O que faltar fica em `!!! question "Em aberto"` — não invente
fatos. Antes de escrever, leia `.claude/contexto/conteudo.md` (convenções) e, para listagens,
`.claude/contexto/visual.md` (cartões).

## NPC

- Se o autor estiver no computador, o mais barato é o Painel (**Adicionar NPC**). Pelo chat, use a
  função `criar_npc` de `admin/wiki_data.py` (ela já cria o arquivo no padrão, coloca no menu no
  grupo da cidade e valida o build):

  ```bash
  python -c "import sys; sys.path.insert(0, 'admin'); import wiki_data as wd; from pathlib import Path; \
  print(wd.criar_npc(Path('.'), {'nome': '...', 'titulo': '...', 'raca': '...', 'cidade': '...', \
  'afiliacao': '...', 'resumo': '...', 'descricao': '...'}))"
  ```

- A tabela de NPCs se atualiza sozinha. Biografia (aba **Biografia**) e ficha de combate
  (aba **Ficha de combate**, com a "ficha completa" opcional de inventário/grimório/
  características/efeitos) só se o autor pedir — ver `.claude/contexto/npcs.md`.

## Cidade, evento, facção, lugar ou tema

1. Arquivo em `docs/<pasta>/<nome-sem-acento-com-hifens>.md`, copiando a estrutura de uma página
   irmã: front matter com `tags`, `# Título`, ficha (`<div class="ficha" markdown>` + tabela com
   cabeçalho vazio), texto, e `!!! question "Em aberto"` no fim.
2. Menu: acrescente no `nav:` do `mkdocs.yml`, no grupo certo (ex.: cidade em
   `Wiki → Cidades → Aliança dos Lordes`).
3. Índice da seção: acrescente um cartão em `docs/<pasta>/index.md` (formato em `visual.md`).
4. Links: ligue a página nova a partir das páginas relacionadas (cidade, casa, evento) e vice-versa.
5. Se for cânone que muda a história, atualize também `docs/compendio/` e, se narrativo, a Lore.

## Validar e entregar

- `mkdocs build --strict` sem avisos.
- Responda em poucas linhas: o arquivo criado, onde entrou no menu e o que ficou "Em aberto".
