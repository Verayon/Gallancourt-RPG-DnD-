# Crônicas de Gallancourt

Wiki de lore da campanha de RPG (D&D) ambientada em **Gallancourt**, um reino partido entre a
Aliança dos Lordes e a teocracia de L'Ordre de Célestien.

O site é gerado com [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) a partir de
arquivos Markdown, com busca, tags, modo escuro e navegação por categorias.

## Estrutura do conteúdo

```
docs/
├── index.md        Página inicial e princípio central da ambientação
├── visao-geral.md  O cenário resumido em uma página, com diagramas
├── historia/       A crônica em capítulos + cronologia
├── eventos/        Batalhas, decretos e períodos (uma página por evento)
├── geografia/      Península, cordilheira, Cicatriz, ilhas, divisão territorial, mapas
├── cidades/        As 5 cidades da Aliança e as 3 de L'Ordre
├── faccoes/        Estados, as cinco casas, outras casas e organizações
├── personagens/    Uma página por NPC
├── mundo/          Conflitos, teia política, relações entre cidades, intrigas da nobreza,
│                   religião, economia, operações clandestinas, glossário
└── mestre/         Referência rápida, lacunas, manutenção do cânone, inconsistências, fontes
fontes/             Documentos-fonte: PDF do autor (prevalece) e dossiê
```

## Rodando localmente

```bash
pip install -r requirements.txt
mkdocs serve          # http://127.0.0.1:8000 com recarga automática
mkdocs build --strict # gera ./site e falha se houver links quebrados
```

## Adicionando conteúdo

Veja `docs/mestre/manutencao-do-canone.md`: categorias de informação (cânone, leitura
cartográfica, inferência, em aberto), marcas de estado (`CANON`, `SEGREDO` …), modelo de ficha
de NPC e o passo a passo para criar uma página nova.
