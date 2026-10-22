# Acervo de fontes

Tudo o que o autor fornece para o projeto fica aqui, **sem edição**: é a matéria-prima da wiki
(`docs/`). A leitura consolidada dessas fontes está no Compêndio (`docs/compendio/`).

```
fontes/
├── textos/     Documentos do autor e transcrições (.pdf, .md, .txt, .docx)
├── imagens/    Mapas, ilustrações, retratos, brasões
└── videos/     Vídeos e gravações de sessão de criação
```

Crie outras pastas se surgirem novos tipos (por exemplo `audios/`). Imagens que devem **aparecer
no site** também precisam de uma cópia em `docs/assets/` (o MkDocs só publica o que está em
`docs/`); a versão original continua aqui.

## Convenções

- Nome de arquivo: minúsculas, sem acentos, com hífens, e com versão ou data quando houver mais de
  uma (`cronicas-de-gallancourt-v2.md`, `mapa-regional-2026-09.png`).
- Um PDF ou imagem que tenha texto importante ganha uma **transcrição `.md`** ao lado, para que o
  conteúdo possa ser buscado e comparado.
- Registre toda fonte nova na tabela abaixo e em `docs/mestre/fontes.md`.

## Fontes registradas

| # | Arquivo | O que é | Precedência |
|---|---|---|---|
| 1 | `textos/Historia_Gallancourt.pdf` | *Crônicas de Gallancourt: Um Reino Dividido (Versão Revisada)* — PDF do autor, 17 páginas. É o mesmo documento que a "Versão 2" | **Prevalece.** Páginas 1–8 (revisadas) acima das páginas 9–17 (rascunhos) |
| 2 | `textos/cronicas-de-gallancourt-v2.md` | Transcrição de `Crônicas de Gallancourt Vers.2.pdf` (= fonte 1) | Igual à fonte 1 |
| 3 | `textos/cronicas-de-gallancourt-v1.md` | Transcrição de `Crônicas de Gallancourt Vers.1.pdf`, 9 páginas: crônica, linha do tempo, reação de cada cidade ao Édito, personagens (com propostas de novos NPCs) e teia de conexões | Abaixo da fonte 1. Versão anterior, origem de boa parte do dossiê |
| 4 | `textos/Gallancourt_Dossie_Geral_Expandido.md` | *Dossiê Geral Expandido de Gallancourt*: crônica consolidada, leitura de dois mapas, método do cânone | Abaixo da fonte 1; completa o que o PDF não cobre |

> **PDF da Versão 1:** o PDF original ainda não está no repositório. Salve-o como
> `textos/cronicas-de-gallancourt-v1.pdf`.

As regras de precedência e o modo de tratar divergências estão no `CLAUDE.md`, na raiz do projeto.
