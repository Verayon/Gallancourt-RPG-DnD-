---
tags:
  - Compêndio
---

# Compêndio de Gallancourt

O Compêndio reúne **num só lugar tudo o que as fontes dizem** sobre cada assunto. A wiki divide o
cenário em muitas páginas curtas, boas para consulta rápida; aqui cada assunto ocupa uma página
longa, que você pode ler do início ao fim e que junta as duas versões das *Crônicas de
Gallancourt*, o dossiê e as decisões já tomadas.

<div class="grid cards" markdown>

-   [![](../assets/placeholders/tema.svg){ .card-portrait }](historia-de-gallancourt.md)

    **[História de Gallancourt](historia-de-gallancourt.md)**

    A versão anotada da crônica, do reino de D'Aubren à Guerra Fria, com a origem de cada fato nas
    fontes e a linha do tempo. Para a leitura corrida, sem anotações, veja a
    **[Lore](../lore.md)**.

-   [![](../assets/placeholders/cidade.svg){ .card-portrait }](cidades/index.md)

    **[Cidades](cidades/index.md)**

    Uma página por cidade: geografia, gente, história antes, durante e depois da guerra,
    famílias, figuras de poder, lugares, relações e segredos.

-   [![](../assets/placeholders/personagem.svg){ .card-portrait }](personagens.md)

    **[Personagens](personagens.md)**

    Todos os NPCs num só lugar, com raça, título, cidade e as variações entre as fontes,
    incluindo os NPCs propostos.

-   [![](../assets/placeholders/estado.svg){ .card-portrait }](politica-e-faccoes.md)

    **[Política e facções](politica-e-faccoes.md)**

    Aliança dos Lordes, Conseil des Seigneurs, as cinco casas, as outras casas, organizações,
    frotas, a teia de conexões e a economia.

-   [![](../assets/placeholders/geografia.svg){ .card-portrait }](geografia-e-religiao.md)

    **[Geografia e religião](geografia-e-religiao.md)**

    A península, Nirador, a cordilheira, a Cicatriz, as ilhas, os mapas e a fé de Amaunator.

-   [![](../assets/placeholders/tema.svg){ .card-portrait }](pendencias.md)

    **[Pendências para o autor](pendencias.md)**

    O que as novas fontes trouxeram de divergente ou de proposto, esperando decisão.

</div>

## Como ler o Compêndio

### De onde vem cada informação

As fontes estão em `fontes/textos/` e são citadas pelas siglas abaixo.

| Sigla | Fonte | Peso |
|---|---|---|
| **V2** | *Crônicas de Gallancourt: Um Reino Dividido (Versão Revisada)*, páginas 1–8 | Prevalece sobre todas |
| **V2-r** | Mesma fonte, páginas 9–17 (rascunhos anteriores) | Usada onde não conflita com a V2 |
| **V1** | *Crônicas de Gallancourt*, Versão 1 | Usada onde não conflita com a V2 |
| **D** | *Dossiê Geral Expandido de Gallancourt* | Usada onde não conflita com a V2 |

Quando uma informação vem só da V1 ou só do dossiê, a sigla aparece ao lado dela
(<sup>V1</sup>, <sup>D</sup>). O que não tem sigla está na V2 ou é confirmado por mais de uma fonte.

### Categorias e marcas

O Compêndio segue as mesmas regras da wiki ([Manutenção do cânone](../mestre/manutencao-do-canone.md)):

- texto corrido é **cânone registrado** nas fontes;
- `!!! info "Leitura cartográfica"` é interpretação dos mapas;
- `!!! abstract "Inferência funcional"` é dedução razoável, não confirmada;
- `!!! question "Em aberto"` ainda não foi definido;
- `!!! warning "SEGREDO"` é verdade que os personagens não sabem;
- `POSSIBILIDADE` é proposta ainda não aprovada pelo autor — é o caso dos NPCs que a V1 sugere
  com a palavra "proponho";
- `!!! failure "Divergência"` marca um ponto em que as fontes discordam e o autor ainda não decidiu.
  Todas estão listadas em [Pendências](pendencias.md).

!!! danger "Segredos"
    O Compêndio é material do Mestre e contém todos os segredos do cenário.

## Relação com o resto da wiki

As páginas da wiki continuam sendo a referência rápida, e as tabelas de relações entre cidades e
de intrigas continuam sendo geradas por `scripts/gerar_relacoes.py`. Ao mudar um fato no
Compêndio, mude também a página correspondente da wiki (e o script, se for uma relação).
