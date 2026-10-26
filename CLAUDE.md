# CLAUDE.md

Wiki de lore da campanha de D&D 5e **Crônicas de Gallancourt** (MkDocs Material). Conteúdo e
conversa em **português do Brasil**; nomes franceses mantêm os acentos (Baie de l'Éclair,
L'Ordre de Célestien, Magnetér).

## Comandos

```bash
mkdocs build --strict                 # validação rápida (links, âncoras, menu)
python scripts/testar_site.py         # teste completo e fixo — ou o comando /testar-site
python scripts/gerar_relacoes.py      # regenera relações entre cidades e intrigas
mkdocs serve | python admin/app.py    # site :8000 | Painel do Mestre :5001
```

`MANUTENCAO.md` é o manual do autor (comandos, rotina, problemas); ao mudar como o projeto é
operado, atualize-o junto.

## Onde está cada coisa

| Caminho | O quê |
|---|---|
| `docs/` | O site. Menu: Início, Lore, Wiki (Mundo, Geografia, Cidades, Facções, NPCs=`personagens/`, Eventos), Compêndio, Mestre (sessões, diário, linha do tempo), Configurações |
| `hooks/` | Código que roda no build: `gallancourt.py` (NPCs, tabelas, abas), `linha_tempo.py` |
| `admin/` | Painel do Mestre (Flask local) — cria NPCs, sessões, fichas, acontecimentos |
| `dados/linha-do-tempo.yml` | Acontecimentos da campanha (fonte única) |
| `scripts/` | `gerar_relacoes.py` (fonte única das relações), `testar_site.py` (teste fixo) |
| `fontes/` | Acervo do autor — **não editar**; guia em `fontes/README.md` |

**Antes de mexer numa área, leia só o arquivo de contexto dela:**

| Vai mexer em… | Leia |
|---|---|
| CSS, layout, menu, cartões, páginas de listagem | `.claude/contexto/visual.md` |
| NPCs, tabela de NPCs, ficha 5e, linha do tempo, `hooks/` | `.claude/contexto/npcs.md` |
| Painel, Diário, sessões, calendário | `.claude/contexto/sessoes-e-painel.md` |
| Páginas de conteúdo, relações/intrigas, Compêndio | `.claude/contexto/conteudo.md` |

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
- **Respostas curtas** ao autor: o que mudou, onde, e o que ele precisa decidir.

## Comandos do projeto (skills em `.claude/skills/`)

- `/testar-site` — roda o teste fixo e resume o resultado (só quando o autor pedir).
- `/incorporar-documento <arquivo>` — compara um texto novo do autor com a wiki e incorpora.
- `/nova-pagina <tipo> <assunto>` — cria cidade, evento, facção, NPC ou lugar no padrão do site.

Antes de commitar: `mkdocs build --strict` sem avisos. Commits e push só no branch de trabalho.
