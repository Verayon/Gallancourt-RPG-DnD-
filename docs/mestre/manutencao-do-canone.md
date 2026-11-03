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

Essa é a ficha de **planejamento** do Mestre (o que o NPC quer e esconde) — continua em Markdown,
editada pelo formulário de NPC do Painel. Para a ficha de jogo completa de D&D 5e — atributos, CA,
PV, perícias, inventário, grimório, características, biografia, diário — use a **Ficha de
combate** descrita abaixo, direto na página pública do personagem. Para criaturas e figurantes
**sem página própria** (bandidos de uma sessão, por exemplo), use a **Ficha de combate** do Painel
direto na página do roteiro (ver "Figurantes de sessão" abaixo). Para cidades, a **Ficha da
cidade** (Painel → Biografia). Não edite à mão sem necessidade as seções que usam marcadores
invisíveis (`<!-- campo:... -->`, `<!-- dados:statblock ... -->` ou
`<!-- personagem:ficha-dinamica -->`): o site/painel esperam encontrá-los para reler os valores
depois.

## Ficha de combate (monstros, NPCs nomeados e jogadores)

Desde 2026-10-31, monstro, NPC nomeado e jogador compartilham o **mesmo modelo de ficha**, com os
dados no **banco de dados** (`dados/gallancourt.db`, ver `admin/banco.py`/
`admin/personagens_api.py`), não em Markdown — a página só tem um marcador
(`<!-- personagem:ficha-dinamica -->`, dentro de `## Ficha de combate` para NPC/jogador; a página
inteira, no caso de monstro) que um widget (`docs/javascripts/ficha.js`) preenche na hora, puxando
a ficha pela API (`/api/personagens/<tipo>/<slug>`). A leitura é pública para qualquer um; editar
exige entrar em **🔑 Modo Mestre** (botão no cabeçalho, ao lado do alternador claro/escuro — abre
um popup de senha, mesma senha do Painel; não navega pra outra página).

A ficha tem um cabeçalho (CR — monstro — ou Nível/XP/Classe/Antecedente — NPC/jogador —, CA, PV
máximo/temporário, dados de vida, deslocamento, percepção passiva, iniciativa extra, os seis
atributos com modificador calculado sozinho) e sete abas:

- **Atributos** — perícias (bônus próprio, não calculado), sentidos (alcance em metros), idiomas.
- **Inventário** — equipamento (catálogo compartilhado), moeda (PC/PP/PE/PO/PL) e carga máxima.
- **Grimório** — magias (catálogo compartilhado) e pools de espaços de magia (nível, usados/
  máximo, com rótulo pra separar espaços normais de Magia de Pacto).
- **Características** — traços, ações e reações (catálogo compartilhado).
- **Efeitos** — condições (as 15 do 5e, liga/desliga) e efeitos aplicados (temporário/passivo/
  inativo, com origem e duração).
- **Biografia** — aparência, personalidade, traço marcante, ideal, vínculo, defeito, dados físicos,
  pessoas/lugares de interesse — pertence ao **personagem**, não a uma variante específica.
- **Diário** — lista de entradas (data, título, texto), uma por acontecimento.

Todo personagem tem sempre uma ficha **Base** (nunca removível). Em Modo Mestre, o botão **+** ao
lado das abas de ficha cria uma **variante** (ex.: Goblin → Arqueiro) — cópia independente e
totalmente editável da ficha atual (atributos, inventário, grimório etc.; Biografia/Diário
continuam compartilhados, por serem do personagem), com seu próprio botão **Excluir ficha**.
Equipamento, Traços/Ações/Reações, Magias, Idiomas, Sentidos e Perícias são catálogos
compartilhados entre personagens (botão **+ adicionar**, que abre uma busca no catálogo
correspondente, com opção de criar uma entrada nova quando não existir ainda).

A migração inicial (`scripts/migrar_monstros_para_banco.py` e
`scripts/migrar_npcs_jogadores_para_banco.py`, uso único, já rodadas) também espelhou
`docs/itens/*.md`/`docs/magias/*.md`/`docs/pericias/*.md` nos catálogos correspondentes — essas
páginas continuam existindo e sendo a fonte de leitura/lore; o banco é só um espelho consultável
delas para o seletor "+ adicionar".

## Combat Tracker

Cada página de sessão (`docs/mestre/sessoes/sessao-N-*.md`) tem uma aba **Combat Tracker**, a
última da lista — ela roda o combate ao vivo usando as fichas de monstro/NPC/jogador descritas
acima: iniciativa (base + desempate oculto), PV com temporário, grade de condições, economia de
ação (1 Ação/1 Ação Bônus/1 Reação por turno), testes de morte, concentração, reações manuais
(Contramagia/Esquiva Sobrenatural) e, ao encerrar, distribuição de XP e loot. **Monstro** entra
como uma cópia isolada (não altera o catálogo); **NPC nomeado e jogador** leem/escrevem direto na
Ficha real (PV, espaços de magia e itens consumidos persistem entre sessões, até um **Descanso
longo** na própria ficha). Substitui por completo o antigo "Painel de Iniciativa"
(`admin/sessao_viva.py`, retirado). Detalhes em `.claude/contexto/combate.md`.

## Figurantes de sessão

Para uma criatura sem página própria (bandidos de uma sessão, por exemplo) ou pra começar a partir
de um NPC genérico (guarda, camponês...; essas páginas vivem em `docs/personagens/genericos/`,
criadas pelo Painel — sem índice próprio ainda), continue usando a
aba **Ficha de combate** do [Painel do Mestre](painel.md) — ela insere o cartão direto na página
de sessão escolhida e guarda os valores num comentário invisível (`<!-- dados:statblock ... -->`).
Esse sistema mais simples (texto em Markdown, não banco de dados) é de propósito: um figurante
raramente precisa virar um personagem reutilizável de verdade — se precisar, crie uma página de
NPC pra ele normalmente. Veja exemplos em
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
3. Acrescente um link para ela no corpo da página-índice da categoria (`docs/cidades/index.md`,
   `docs/eventos/index.md`...) — um card no `<div class="grid cards" markdown>` ou uma linha na
   tabela, conforme o padrão já usado ali. **Não** edite o `nav` do `mkdocs.yml`: o menu da
   esquerda só lista as seis categorias principais (Lore, Wiki, Compêndio, Mestre,
   Configurações, Changelog, Roadmap); toda subcategoria se acessa clicando no corpo da página,
   não pelo menu.
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
(Intrigas, Na história…). As caixas **Em aberto** são reunidas numa última aba. Não é preciso
escrever nada de especial para as abas: basta usar `##`.

Uma aba é montada automaticamente:

- **Linha do tempo** — os acontecimentos de `dados/linha-do-tempo.yml` que envolvem o NPC, em ordem
  cronológica. Mudanças de situação, localização, afiliação ou título aparecem também na caixa do
  topo e na tabela de NPCs. Cidades e facções ganham a mesma seção no fim da página.

As demais seções da página, incluindo uma **Biografia** (preenchida pela aba **Biografia** do
[Painel do Mestre](painel.md)) ou uma **Ficha de combate** (veja abaixo) — com sua "ficha completa"
opcional de inventário/grimório/características/efeitos, cada um virando sua própria aba —, são
`##` normais no corpo do texto — não há mágica especial além da divisão em abas.

## Relações e intrigas

As páginas [Relações entre cidades](../mundo/relacoes-entre-cidades.md) e
[Intrigas da nobreza](../mundo/intrigas-da-nobreza.md), e as tabelas de relações nas páginas de
cidades e personagens, são geradas pelo script `scripts/gerar_relacoes.py`. Para mudar uma
relação, edite as listas `PARES` (cidades) ou `INTRIGAS` (nobres) no script e rode
`python3 scripts/gerar_relacoes.py`. Não edite à mão o conteúdo entre os marcadores
`<!-- inicio:gerado -->` e `<!-- fim:gerado -->`: ele é sobrescrito a cada execução.
