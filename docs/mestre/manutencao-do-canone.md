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
[Painel do Mestre](painel.md). Para combate — atributos, CA, PV, perícias, equipamento, ações e
magias —, use a **Ficha de combate** (ver abaixo). Não edite essas três seções à mão sem
necessidade: elas usam marcadores invisíveis (`<!-- campo:... -->` ou `<!-- dados:statblock ... -->`)
que o painel espera encontrar para reler os valores depois.

## Ficha de combate

Um cartão visual de NPC para rodar à mesa, no estilo de uma ficha oficial: nome, CA, PV,
deslocamento, os seis atributos com modificador calculado sozinho, perícias, sentidos, idiomas,
equipamento, traços, ações, reações e magias. Preenchida pela aba **Ficha de combate** do
[Painel do Mestre](painel.md), que insere o cartão na página escolhida (qualquer uma — não precisa
ser uma página de personagem) e guarda os valores num comentário invisível (`<!-- dados:statblock
... -->`) para poder reabrir e editar depois. Veja exemplos em
[Sessão 0 — Fichas de combate](sessoes/sessao-0-os-grilhoes-da-estrada.md#fichas-de-combate).

## Como adicionar uma página

**NPCs e sessões:** use os botões **Adicionar NPC** (na página [NPCs](../personagens/index.md)) e
**Nova sessão** (em [Mestre → Sessões](sessoes/index.md)). Eles abrem o
[Painel do Mestre](painel.md), que cria a página no padrão certo e a coloca no menu.

**Outras páginas:**

1. Crie o arquivo `.md` na pasta da categoria (`docs/cidades/`, `docs/eventos/` …),
   usando nomes em minúsculas, sem acentos e com hífens (ex.: `nova-cidade.md`).
2. Copie a estrutura de uma página existente da mesma categoria: *front matter* com `tags`,
   título, ficha lateral (`<div class="ficha" markdown>`), descrição, relações e "Em aberto".
3. Adicione a página ao `nav` em `mkdocs.yml`.
4. Crie links a partir das páginas relacionadas (cidade, casa, eventos).
5. Rode `mkdocs build --strict` para verificar links quebrados.

## Como é uma página de NPC

Os dados rápidos do NPC ficam no topo do arquivo, no bloco `npc:` do *front matter*. O site usa
esse bloco para montar a caixa com o retrato e para preencher a tabela de [NPCs](../personagens/index.md):

```yaml
npc:
  titulo: Marquesa            # colunas da tabela de NPCs (texto simples, para filtrar)
  raca: Humana
  cidade: Dodixie
  afiliacao: Casa Corbeau
  resumo: Governante de fato; jovem e implacável.   # aparece na tabela e na caixa do topo
  retrato: ../assets/imagens/personagens/scyras-corbeau.png   # vazio = moldura padrão
  ficha:                      # linhas da caixa do topo (aceitam links)
    Título: Marquesa
    Casa: "[Corbeau](../faccoes/casa-corbeau.md) (líder)"
```

O texto abaixo do título vira a aba **Visão geral**, e cada seção `##` vira uma aba própria
(Intrigas, Ficha de personagem, Histórico de sessões…). As caixas **Em aberto** são reunidas numa
última aba. Não é preciso escrever nada de especial para as abas: basta usar `##`.

## Relações e intrigas

As páginas [Relações entre cidades](../mundo/relacoes-entre-cidades.md) e
[Intrigas da nobreza](../mundo/intrigas-da-nobreza.md), e as tabelas de relações nas páginas de
cidades e personagens, são geradas pelo script `scripts/gerar_relacoes.py`. Para mudar uma
relação, edite as listas `PARES` (cidades) ou `INTRIGAS` (nobres) no script e rode
`python3 scripts/gerar_relacoes.py`. Não edite à mão o conteúdo entre os marcadores
`<!-- inicio:gerado -->` e `<!-- fim:gerado -->`: ele é sobrescrito a cada execução.
