---
name: incorporar-documento
description: Compara um documento novo do autor (texto, PDF, transcrição) com a wiki de Gallancourt, lista o que é novo e o que conflita, pergunta sobre os conflitos e incorpora. Use quando o autor enviar um texto de lore para atualizar o site.
argument-hint: "<caminho do arquivo>"
---

# Incorporar um documento do autor

Arquivo: `$ARGUMENTS`

## 1. Guardar o original

- Mova/copie o original para `fontes/textos/` (ou `fontes/imagens/`, `fontes/videos/`).
- Se tiver texto, crie uma transcrição `.md` ao lado (para PDF, extraia o texto uma vez) e
  registre ambos em `fontes/README.md`. Daqui em diante, **trabalhe só com a transcrição**.

## 2. Comparar sem ler a wiki inteira

- Liste os nomes próprios, lugares, datas e eventos do documento.
- Para cada um, `grep -rn "<nome>" docs/` e leia só os trechos encontrados.
- Monte duas listas: **novo** (não existe na wiki) e **conflito** (a wiki diz outra coisa).
  Considere a precedência das fontes do `CLAUDE.md` (regra 2).

## 3. Perguntar antes de mudar

- Pergunte ao autor sobre **cada conflito**, de uma vez só (agrupe em no máximo 4 perguntas),
  com as opções e a recomendação.
- O que é só **novo** e não conflita pode ser incorporado direto.

## 4. Aplicar

- Edite as páginas da wiki afetadas **e** a versão anotada correspondente em `docs/compendio/`
  (ver `.claude/contexto/conteudo.md`). Na Lore (`docs/lore/index.md`) só narrativa, sem marcas.
- Relações entre cidades/nobres mudaram? Edite `scripts/gerar_relacoes.py` e rode-o.
- NPC novo? Siga a skill `nova-pagina` (bloco `npc:`, menu, tabela automática).
- Registre as divergências resolvidas em `docs/mestre/inconsistencias.md`, marque lacunas
  respondidas em `docs/mestre/lacunas.md` e atualize `docs/mestre/fontes.md`.
- Nome trocado? `grep -rn "<nome antigo>"` em `docs/`, `scripts/`, `CLAUDE.md` e `.claude/` para
  não deixar referências órfãs.

## 5. Validar e entregar

- `mkdocs build --strict` sem avisos.
- Responda ao autor: o que entrou, o que mudou por decisão dele e o que ficou em aberto.
