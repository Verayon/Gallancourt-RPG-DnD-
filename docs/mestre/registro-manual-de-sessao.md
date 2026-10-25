---
tags:
  - Mestre
  - Diário
---

# Como registrar uma sessão manualmente

O [Painel do Mestre](painel.md) faz os passos abaixo por você. Esta página existe para quem prefere
editar os arquivos à mão, ou para entender o que o painel está fazendo.

1. **Copie o modelo abaixo** para um arquivo novo `docs/diario/sessao-NN.md` (`NN` é o número da
   sessão, com zero à esquerda: `sessao-01.md`, `sessao-02.md`…).

    ```markdown
    ---
    tags:
      - Diário
    ---

    # Sessão NN — título curto da sessão

    <div class="ficha" markdown>

    | | |
    |---|---|
    | **Data real** | AAAA-MM-DD |
    | **Data na campanha** | DD de mês de ano — ex.: 24 de outubro de 1453 |
    | **Local(is)** | [Cidade](../cidades/cidade.md) |
    | **Personagens dos jogadores** | Nome (jogador) — Nome (jogador) |
    | **NPCs em cena** | [Fulano](../personagens/fulano.md) |

    </div>

    ## O que aconteceu

    Resumo em texto corrido: o que os jogadores fizeram, decidiram e descobriram.

    ## Atualizações no cânone

    - [Nome da página](../caminho/pagina.md) — o que mudou nela e por quê.
    - Nova página: [Nome do NPC novo](../personagens/nome.md) — criada porque…

    ---

    **Anterior:** [Sessão NN-1](sessao-(NN-1).md) · **Próxima:** —
    ```

2. **Preencha a ficha** com as duas datas, o local e quem estava em cena.
3. **Escreva o resumo** e liste, em "Atualizações no cânone", toda página que mudou por causa da
   sessão — e depois **edite de fato** essas páginas (a lista aqui é um índice do que fazer, não
   substitui a edição).
4. **Registre a sessão em três lugares**:
      - uma linha nova na tabela em "Sessões registradas", em [Diário de Sessões](../diario/index.md),
        entre os marcadores `<!-- inicio:sessoes -->` e `<!-- fim:sessoes -->`;
      - um marco novo na linha do tempo `mermaid`, entre `<!-- inicio:timeline -->` e
        `<!-- fim:timeline -->`, na mesma página;
      - uma entrada nova em `nav:`, dentro do `mkdocs.yml`, na seção **Mestre → Diário de Sessões**.
5. Se uma página específica mudou de um jeito que vale a pena guardar a razão (uma revelação, uma
   morte, uma aliança quebrada), adicione nela uma seção `## Histórico de sessões` com uma linha
   como:

    ```markdown
    ## Histórico de sessões

    - **[Sessão 3](../diario/sessao-03.md)** (12 de novembro de 1453) — Scyras revelou que…
    ```

    Essa seção é opcional e só existe nas páginas que já tiveram uma mudança registrada — não
    precisa adicioná-la em branco nas páginas que ainda não mudaram.

Também pode pedir para eu (Claude) fazer esses passos por você em conversa: diga o que aconteceu na
sessão e eu crio o arquivo, atualizo as páginas afetadas e registro tudo no lugar certo.
