---
tags:
  - Mundo
  - Política
  - Cidades
---

# Relações entre cidades

Cada cidade da Aliança tem **um motivo para precisar** e **um motivo para desconfiar** de cada
uma das outras. É assim que elas se relacionam quando a campanha começa.

!!! info "Como ler"
    O motivo **positivo** marcado com `CANON` vem do dossiê. Os demais motivos e os estados são
    `POSSIBILIDADE`: propostas para o autor aprovar, ajustar ou descartar.

## Escala de relação

| Estado | Significado |
|---|---|
| 🟢 **Aliado** | Interesses alinhados e dependência assumida. |
| 🔵 **Cordial** | Relação boa, mas com atritos administráveis. |
| ⚪ **Neutro** | Contato pragmático, sem afeto nem hostilidade. |
| 🟠 **Tenso** | Cooperação formal sobre desconfiança real. |
| 🔴 **Hostil velado** | Sorrisos no conselho, facas nos bastidores. |

## Mapa de relações

```mermaid
graph LR
    DOD["Dodixie"]
    BAI["Baie de l'Éclair"]
    NMO["Nouvelle-Montagne"]
    SAR["Saint-Armand"]
    VAL["Valynesse"]
    DOD ---|Tenso| BAI
    DOD ---|Cordial| NMO
    DOD ---|Neutro| SAR
    DOD ---|Tenso| VAL
    BAI ---|Neutro| NMO
    BAI ---|Tenso| SAR
    BAI ---|Cordial| VAL
    NMO ---|Aliado| SAR
    NMO ---|Tenso| VAL
    SAR ---|Hostil velado| VAL
    linkStyle 0 stroke:#ef6c00,stroke-width:3px
    linkStyle 1 stroke:#0277bd,stroke-width:3px
    linkStyle 2 stroke:#9e9e9e,stroke-width:3px
    linkStyle 3 stroke:#ef6c00,stroke-width:3px
    linkStyle 4 stroke:#9e9e9e,stroke-width:3px
    linkStyle 5 stroke:#ef6c00,stroke-width:3px
    linkStyle 6 stroke:#0277bd,stroke-width:3px
    linkStyle 7 stroke:#2e7d32,stroke-width:3px
    linkStyle 8 stroke:#ef6c00,stroke-width:3px
    linkStyle 9 stroke:#c62828,stroke-width:3px
```

## Matriz

| | Dodixie | Baie de l'Éclair | Nouvelle-Montagne | Saint-Armand | Valynesse |
|---|---|---|---|---|---|
| **[Dodixie](../cidades/dodixie.md)** | — | 🟠 Tenso | 🔵 Cordial | ⚪ Neutro | 🟠 Tenso |
| **[Baie de l'Éclair](../cidades/baie-de-l-eclair.md)** | 🟠 Tenso | — | ⚪ Neutro | 🟠 Tenso | 🔵 Cordial |
| **[Nouvelle-Montagne](../cidades/nouvelle-montagne.md)** | 🔵 Cordial | ⚪ Neutro | — | 🟢 Aliado | 🟠 Tenso |
| **[Saint-Armand](../cidades/saint-armand.md)** | ⚪ Neutro | 🟠 Tenso | 🟢 Aliado | — | 🔴 Hostil velado |
| **[Valynesse](../cidades/valynesse.md)** | 🟠 Tenso | 🔵 Cordial | 🟠 Tenso | 🔴 Hostil velado | — |

## Os dez pares

### Dodixie × Baie de l'Éclair

**Estado:** 🟠 Tenso `POSSIBILIDADE`

| | |
|---|---|
| **Motivo positivo** `CANON` | As duas marinhas da Aliança: rotas comerciais e operações navais conjuntas. |
| **Motivo negativo** `POSSIBILIDADE` | Disputam as mesmas rotas e portos. Baie sofreu pirataria durante a guerra, e o corsário Rochefort, que ataca essas rotas, age em segredo para a Casa Corbeau. Se Baie descobrir, a aliança naval racha. |

### Dodixie × Nouvelle-Montagne

**Estado:** 🔵 Cordial `POSSIBILIDADE`

| | |
|---|---|
| **Motivo positivo** `CANON` | Dodixie compra grão e escoa a produção de Nouvelle-Montagne pelo mar. |
| **Motivo negativo** `POSSIBILIDADE` | Dodixie depende de comida que não produz, e Élodie Vaucluse defende usar o grão como alavanca política. A frota pirata financiada por Lucien de Saint-Pierre ataca navios, possivelmente os de Rochefort. |

### Dodixie × Saint-Armand

**Estado:** ⚪ Neutro `POSSIBILIDADE`

| | |
|---|---|
| **Motivo positivo** `CANON` | Saint-Armand garante a proteção terrestre que uma cidade naval não tem. |
| **Motivo negativo** `POSSIBILIDADE` | Corbeau vê um exército cada vez maior como ameaça à própria autonomia; Saint-Armand se ressente de que a marinha fique com a glória e o dinheiro. As redes de espionagem de Corbeau podem saber dos planos de golpe de Armand. |

### Dodixie × Valynesse

**Estado:** 🟠 Tenso `POSSIBILIDADE`

| | |
|---|---|
| **Motivo positivo** `CANON` | Política e espionagem: Valynesse coordena, Dodixie informa e financia. |
| **Motivo negativo** `POSSIBILIDADE` | Duas redes de espionagem (Corbeau e Beaumont) vigiam uma à outra. Scyras desconfia de que o Doge governa como um rei sem coroa. |

### Baie de l'Éclair × Nouvelle-Montagne

**Estado:** ⚪ Neutro `POSSIBILIDADE`

| | |
|---|---|
| **Motivo positivo** `POSSIBILIDADE` | Baie compra grão e mármore; Nouvelle-Montagne precisa das rotas do oeste para vender. |
| **Motivo negativo** `POSSIBILIDADE` | O controle de Vigny sobre as rotas encarece o frete; a frota pirata ligada a Lucien de Saint-Pierre ataca justamente as rotas de Baie. |

### Baie de l'Éclair × Saint-Armand

**Estado:** 🟠 Tenso `POSSIBILIDADE`

| | |
|---|---|
| **Motivo positivo** `POSSIBILIDADE` | A Torre do Trovão poderia dar à fronteira magia de guerra que nenhum exército tem. |
| **Motivo negativo** `POSSIBILIDADE` | Kaelen Thorne se recusa a pôr a Torre a serviço do exército; Armand quer tempestades como arma. A fé tradicional de Saint-Armand desconfia de uma cidade governada por magos. |

### Baie de l'Éclair × Valynesse

**Estado:** 🔵 Cordial `POSSIBILIDADE`

| | |
|---|---|
| **Motivo positivo** `CANON` | Comércio e política: Baie vende, Valynesse financia. |
| **Motivo negativo** `POSSIBILIDADE` | Os financistas de Valynesse querem taxar as rotas de Vigny; a Casa Lumière teme ser reduzida a província do Doge. |

### Nouvelle-Montagne × Saint-Armand

**Estado:** 🟢 Aliado `POSSIBILIDADE`

| | |
|---|---|
| **Motivo positivo** `CANON` | Alimento em troca de proteção: o pacto nascido no Massacre da Aurora Velada, mantido por Juliette Clermont. |
| **Motivo negativo** `POSSIBILIDADE` | Dependência gera ressentimento: os clãs discutem se o preço da proteção é justo, e Élodie quer renegociá-lo. Um golpe de Armand só funcionaria com o grão de Helga, que tem a chave nas mãos. |

### Nouvelle-Montagne × Valynesse

**Estado:** 🟠 Tenso `POSSIBILIDADE`

| | |
|---|---|
| **Motivo positivo** `CANON` | Nouvelle-Montagne alimenta a antiga capital. |
| **Motivo negativo** `POSSIBILIDADE` | Choque entre o poder do dinheiro (Magnetér) e o poder da comida (Roche). Valynesse se lembra de que sua fome tem dono. |

### Saint-Armand × Valynesse

**Estado:** 🔴 Hostil velado `POSSIBILIDADE`

| | |
|---|---|
| **Motivo positivo** `CANON` | Saint-Armand é a espada da Aliança; Valynesse paga por ela. |
| **Motivo negativo** `POSSIBILIDADE` | Armand considerou um golpe, e o alvo natural é a centralidade de Valynesse. Beaumont vigia o exército. Saint-Armand lembra que segurou o istmo enquanto os outros entravam na capital. |

## Relações com L'Ordre de Célestien

| Lado da Aliança | Lado de L'Ordre | Estado | Tensão | Oportunidade ilícita |
|---|---|---|---|---|
| Saint-Armand | Chantépierre | 🔴 Hostil velado | Vigilância mútua nos passos; é aqui que qualquer guerra começa. | Contrabando e deserções atravessam a fronteira nos dois sentidos. |
| Valynesse | Montclair de Lune | 🔴 Hostil velado | Guerra de espiões: Beaumont contra os tribunais de L'Ordre. | Thibault de la Rivière entregou segredos da Aliança a L'Ordre; ninguém sabe quanto. |
| Dodixie | L'Ordre | 🔴 Hostil velado | Embargo oficial; a cidade multicultural é tudo o que a doutrina da pureza odeia. | La Voile Noire lucra contrabandeando mercadorias e pessoas pela fronteira. |
| Baie de l'Éclair | L'Ordre | 🔴 Hostil velado | A magocracia é heresia aos olhos de L'Ordre. | Rotas marítimas próximas das águas orientais podem ser usadas para desembarques. |
| Nouvelle-Montagne | L'Ordre | 🟠 Tenso | O celeiro foi o primeiro alvo da Coroa; seria de novo. | Grão vendido às escondidas para o leste renderia fortunas a quem ousasse. |

Ver também: [Intrigas da nobreza](intrigas-da-nobreza.md) · [Teia política](teia-politica.md).
