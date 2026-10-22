---
tags:
  - Mestre
---

# Manutenção do cânone

## Categorias de informação

Todo o conteúdo desta wiki pertence a uma de quatro categorias:

| Categoria | Significado | Como aparece |
|---|---|---|
| **Cânone registrado** | Explicitamente presente nas crônicas e notas | Texto corrido |
| **Leitura cartográfica** | Descrição visual ou interpretação prudente dos mapas | Caixa `!!! info "Leitura cartográfica"` |
| **Inferência funcional** | Conclusão logística ou política razoável, ainda não confirmada como fato diegético | Caixa `!!! abstract "Inferência funcional"` |
| **Em aberto** | Precisa ser definido pelo autor ou pode ser descoberto na campanha | Caixa `!!! question "Em aberto"` |

## Marcas de estado para novas adições

| Marca | Uso |
|---|---|
| `CANON` | Fato confirmado pelo autor |
| `PLANEJADO` | Elemento pretendido, ainda sujeito a alteração |
| `POSSIBILIDADE` | Ideia de trama ou explicação não escolhida |
| `SEGREDO` | Fato verdadeiro no cenário, ainda não conhecido pelos personagens |
| `DESCONHECIDO` | Informação ainda não definida nem pelo autor |
| `CONSEQUÊNCIA` | Resultado que deve emergir das ações dos jogadores ou NPCs |

Exemplo de uso em uma página:

```markdown
!!! warning "SEGREDO"
    O nobre infiltrado que abriu Valynesse era ...
```

!!! danger "Segredos e jogadores"
    Esta wiki é pública por padrão se publicada no GitHub Pages. Guarde conteúdo `SEGREDO`
    fora do repositório público (ou em um repositório privado) se os jogadores tiverem acesso ao
    site.

## Ficha de NPC

Para cada NPC, a ficha pode registrar os campos abaixo. Isso permite que os personagens do
mundo ajam de modo coerente sem determinar antecipadamente todas as consequências da campanha.

```markdown
## Ficha de NPC

| Campo | Valor |
|---|---|
| **Objetivo** | |
| **Temor** | |
| **Ação atual** | |
| **Conhecimento** | O que sabe (e o que não sabe) |
| **Recursos** | |
| **Vínculos** | |
| **Segredo** | |
| **Gatilhos de mudança** | O que faria este NPC mudar de lado ou de plano |
```

Essa é a ficha de **planejamento** do Mestre (o que o NPC quer e esconde). Para aparência física,
personalidade e proficiências — o retrato do personagem, não seus planos —, use a seção **Ficha de
personagem** (e, para cidades, **Ficha da cidade**), preenchida pela aba **Ficha** do
[Painel do Mestre](painel.md). Não edite essas duas seções à mão sem necessidade: elas usam
marcadores invisíveis (`<!-- campo:... -->`) que o painel espera encontrar para reler os valores
depois.

## Como adicionar uma página

1. Crie o arquivo `.md` na pasta da categoria (`docs/personagens/`, `docs/cidades/` …),
   usando nomes em minúsculas, sem acentos e com hífens (ex.: `nova-personagem.md`).
2. Copie a estrutura de uma página existente da mesma categoria: *front matter* com `tags`,
   título, ficha lateral (`<div class="ficha" markdown>`), descrição, relações e "Em aberto".
3. Adicione a página ao `nav` em `mkdocs.yml`.
4. Crie links a partir das páginas relacionadas (cidade, casa, eventos).
5. Rode `mkdocs build --strict` para verificar links quebrados.

## Relações e intrigas

As páginas [Relações entre cidades](../mundo/relacoes-entre-cidades.md) e
[Intrigas da nobreza](../mundo/intrigas-da-nobreza.md), e as tabelas de relações nas páginas de
cidades e personagens, são geradas pelo script `scripts/gerar_relacoes.py`. Para mudar uma
relação, edite as listas `PARES` (cidades) ou `INTRIGAS` (nobres) no script e rode
`python3 scripts/gerar_relacoes.py`. Não edite à mão o conteúdo entre os marcadores
`<!-- inicio:gerado -->` e `<!-- fim:gerado -->`: ele é sobrescrito a cada execução.
