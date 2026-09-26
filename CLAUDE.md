# CLAUDE.md

Wiki de lore da campanha de RPG (D&D 5e) **Crônicas de Gallancourt**, gerada com MkDocs Material
a partir de arquivos Markdown. Todo o conteúdo e toda a comunicação com o autor são em
**português do Brasil**; nomes próprios franceses mantêm os acentos (Baie de l'Éclair,
L'Ordre de Célestien, Magnetér).

## Comandos

```bash
pip install -r requirements.txt       # MkDocs 1.6 + Material 9 (fixado em mkdocs<2)
mkdocs serve                          # site local em http://127.0.0.1:8000
mkdocs build --strict                 # valida: falha com link ou âncora quebrados
python3 scripts/gerar_relacoes.py     # regenera relações entre cidades e intrigas
```

Rode `mkdocs build --strict` antes de todo commit. O build precisa terminar sem avisos.

## Estrutura

```
docs/
├── index.md, visao-geral.md   Início e resumo do cenário em uma página
├── historia/                  A crônica em capítulos + cronologia
├── eventos/                   Uma página por evento
├── geografia/                 Península, cordilheira, Cicatriz, ilhas, Nirador, mapas
├── cidades/                   5 cidades de Gallancourt + 3 de L'Ordre
├── faccoes/                   Estados, casas, organizações, frotas
├── personagens/               Uma página por NPC
├── mundo/                     Relações, intrigas, religião, economia, glossário
└── mestre/                    Lacunas, inconsistências, fontes, manutenção do cânone
fontes/                        Documentos-fonte originais (não editar)
scripts/gerar_relacoes.py      Fonte única dos dados de relações e intrigas
mkdocs.yml                     Configuração e menu (nav) do site
```

## Regras do projeto (decididas pelo autor)

1. **Só conteúdo pré-campanha.** A wiki documenta o mundo como está quando a campanha começa.
   Não escreva planos de campanha, ganchos de aventura, atos, finais ou eventos futuros. Uma
   seção "Campanha" já foi criada e removida a pedido do autor (recuperável no commit `047b0af`).
2. **Precedência das fontes.** `fontes/Historia_Gallancourt.pdf` (texto do autor) **prevalece**
   sobre `fontes/Gallancourt_Dossie_Geral_Expandido.md`. Dentro do PDF, a versão revisada
   (páginas 1–8) prevalece sobre os rascunhos antigos (páginas 9–17).
3. **Nunca invente fatos como cânone.** Toda informação pertence a uma categoria:
   - texto corrido = cânone registrado nas fontes;
   - `!!! info "Leitura cartográfica"` = interpretação dos mapas;
   - `!!! abstract "Inferência funcional"` = dedução razoável, não confirmada;
   - `!!! question "Em aberto"` = ainda não definido.
4. **Marcas de estado** para relações e adições: `CANON`, `PLANEJADO`, `POSSIBILIDADE`
   (proposta do Claude, aguardando o autor), `SEGREDO` (verdade que os personagens não sabem),
   `DESCONHECIDO`, `CONSEQUÊNCIA`. Ao propor algo novo, marque `POSSIBILIDADE`; só o autor promove
   para `CANON`.
5. **Divergências entre fontes** não se resolvem em silêncio: pergunte ao autor e registre a
   decisão em `docs/mestre/inconsistencias.md`.
6. **Segredos.** Conteúdo `SEGREDO` fica em caixas `!!! warning "SEGREDO"` ou com a marca inline.
   Se o site for publicado para os jogadores, esse conteúdo precisa ser separado.

## Decisões já tomadas

| Decisão | Detalhe |
|---|---|
| Estado ocidental | Chama-se **Gallancourt**, governado pela **Aliança dos Lordes** via **Conseil des Seigneurs** |
| Torre do Trovão | Líder: **Arquimago Elian Lumière** (substituiu Kaelen Thorne). O **Duque Jeanesse Lumière** continua como chefe da Casa Lumière |
| Guilda naval | Líder: **Mestre Louis de Montclair** (substituiu Bromli Stonehammer) |
| Período após o Édito | **Ano de Sangue** (não "Mês de Sangue") |
| Scyras | **Marquesa** Scyras de la Maison Corbeau; pai traído por aristocratas da capital |
| Alfonse Enry | **Lorde**; o massacre da família do irmão é recente, obra de L'Ordre |
| Thibault de la Rivière | Traidor **infiltrado**, ainda comandante da Patrulha da Fronteira |
| Henri du Valois | Idealista disfarçado de playboy corrupto |
| Títulos dos rascunhos antigos | Não adotados; listados em `docs/mestre/inconsistencias.md` |

Perguntas ainda abertas estão em `docs/mestre/lacunas.md`.

## Convenções das páginas

- Nome de arquivo: minúsculas, sem acentos, com hífens (`louis-de-montclair.md`).
- Toda página começa com front matter de `tags` (usadas no índice de tags).
- Personagens, cidades, facções e eventos têm uma ficha lateral:
  `<div class="ficha" markdown>` + tabela com cabeçalho vazio (`| | |`).
- Links sempre relativos entre arquivos `.md` (`../cidades/dodixie.md`), nunca URLs do site.
- Toda página nova precisa entrar no `nav` do `mkdocs.yml` e receber links das páginas
  relacionadas (cidade, casa, eventos, índice da seção).
- Diagramas em blocos ` ```mermaid ` (renderizados no navegador, carregados de CDN).

## Relações e intrigas: use o script

As páginas `docs/mundo/relacoes-entre-cidades.md` e `docs/mundo/intrigas-da-nobreza.md`, e os
trechos entre `<!-- inicio:gerado -->` e `<!-- fim:gerado -->` nas páginas de cidades e
personagens, são **gerados** por `scripts/gerar_relacoes.py`. Para mudar uma relação:

1. edite `PARES` (cidades) ou `INTRIGAS` (nobres) no script;
2. rode `python3 scripts/gerar_relacoes.py`;
3. rode `mkdocs build --strict`.

Nunca edite à mão o conteúdo gerado: ele é sobrescrito. Ao renomear um personagem, atualize
também o dicionário `P` e a lista `grupos` do script.

## Checklist ao incorporar um novo documento do autor

1. Guarde o original em `fontes/`.
2. Compare com a wiki; liste o que é novo e o que conflita.
3. Pergunte ao autor sobre cada conflito antes de alterar.
4. Aplique, registre as divergências em `docs/mestre/inconsistencias.md`, marque lacunas
   respondidas em `docs/mestre/lacunas.md` e atualize `docs/mestre/fontes.md`.
5. Procure nomes antigos com `grep -rn` para não deixar referências órfãs.
