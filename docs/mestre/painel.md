---
tags:
  - Mestre
  - Diário
---

# Painel do Mestre

Uma ferramenta local, separada do site, para registrar sessões e editar páginas **sem mexer em
arquivo nenhum à mão**. Ela roda no seu computador, ao lado do site (que continua em
`http://127.0.0.1:8000`), e escreve diretamente nos arquivos de `docs/`. Como o `mkdocs serve` fica
de olho nessa pasta, assim que o painel salva alguma coisa, o site se atualiza sozinho.

!!! warning "Ferramenta só sua"
    O painel não tem senha nem login — quem tiver acesso ao seu computador e souber o endereço
    consegue editar o site por ele. Ele só escuta `127.0.0.1` (não aparece para outros aparelhos da
    rede), então isso é seguro enquanto for só você usando, na sua própria máquina.

## Como abrir

Dentro da pasta do projeto:

```bash
.venv\Scripts\python admin\app.py
```

Ou, no Windows, dê duplo clique em `admin/iniciar-painel.bat`. Depois, abra
**http://127.0.0.1:5001/** no navegador. Deixe essa janela do terminal aberta enquanto usa o
painel — fechá-la desliga a ferramenta (o site em si continua no ar, servido pelo `mkdocs serve`).

## Registrar uma sessão

Na aba inicial:

1. Marque os **NPCs** e as **cidades** (ou outros lugares) que participaram da sessão.
2. Ao lado de cada um, um campo opcional deixa anotar algo específico que aconteceu com aquele
   personagem ou lugar — por exemplo, ao lado de "Scyras Corbeau": *"revelou seu acordo secreto com
   Rochefort a um dos jogadores"*. Se deixar em branco, entra um texto genérico.
3. Preencha a data real, a data na campanha, um título curto e o resumo da sessão.
4. Clique em **Aplicar**.

O painel então:

- cria `docs/diario/sessao-NN.md` com a ficha, o resumo e a lista de atualizações;
- liga a sessão anterior a essa, no rodapé de cada uma ("Anterior" / "Próxima");
- adiciona uma linha em [Sessões registradas](../diario/index.md#sessoes-registradas) e um marco na
  linha do tempo;
- adiciona, no rodapé de cada NPC e cidade marcados, uma linha na seção **Histórico de sessões**
  (criando a seção se ainda não existir);
- registra a página nova no menu do site (`mkdocs.yml`);
- roda `mkdocs build --strict` para conferir que nada quebrou, e mostra o resultado na tela.

Se alguma coisa der errado (por exemplo, o build falhar), o painel mostra o erro em vez de deixar o
site quebrado em silêncio — nesse caso, nada é revertido automaticamente, então corrija o problema
apontado (ou peça para o Claude Code corrigir) antes de rodar o `mkdocs build --strict` de novo.

## Preencher a ficha de um personagem ou cidade

Na aba **Ficha**, escolha "Personagem" ou "Cidade", escolha o nome numa lista e preencha os
campos. Ao salvar, o painel cria (ou substitui) a seção **Ficha de personagem** — ou **Ficha da
cidade** — no rodapé daquela página, com exatamente os campos preenchidos.

Personagens:

| Campo | O que colocar |
|---|---|
| Aparência física | Altura, porte, marcas, roupas, o que chama atenção à primeira vista |
| Personalidade | Como a pessoa age, fala, o que a move |
| Traço marcante | Um hábito ou trejeito reconhecível |
| Ideal | O que essa pessoa defende |
| Vínculo | O que ou quem ela protege ou persegue |
| Defeito | O que pode ser sua ruína |
| Proficiências e idiomas | Perícias, ferramentas, armas, idiomas que fazem sentido para ela |

Cidades:

| Campo | O que colocar |
|---|---|
| População | Uma estimativa, mesmo que aproximada |
| Defesas e guarnição | Muralhas, guarda, frota, o que protege o lugar |

!!! warning "Salvar substitui a seção inteira"
    Cada vez que você salva a ficha de uma página, o painel **reescreve a seção inteira** com os
    valores atuais dos campos. Se você tiver escrito algo à mão nessa seção pelo editor genérico,
    fora desses campos, aquele texto some na próxima vez que salvar a ficha por aqui — para
    conteúdo que não se encaixa nos campos, coloque em outra seção da página.

## Editar qualquer página

Na aba **Editar**, escolha uma página numa lista (com o título de cada uma, para não precisar saber
o nome do arquivo), edite o texto Markdown na caixa e clique em **Salvar**. É a mesma sintaxe usada
em toda a wiki: `#` para títulos, `[texto](link.md)` para links, `**negrito**`, tabelas, e as caixas
`!!! aviso "Título"` para os avisos coloridos. Mudar um título é só editar a linha que começa com
`#` dentro do texto.

!!! question "Em aberto"
    O painel ainda não valida a sintaxe antes de salvar. Depois de editar uma página por aqui, dê
    uma olhada nela no site (`http://127.0.0.1:8000`) para confirmar que ficou como você queria.

### Adicionar uma imagem

Com uma página aberta para edição, clique em **Adicionar uma imagem** para abrir o formulário de
envio. Escolha o arquivo (PNG, JPG, GIF, WEBP ou SVG) e a pasta de destino dentro de
`docs/assets/imagens/` (cidades, personagens, facções, eventos, geografia, mapas ou mundo) e clique
em **Enviar imagem**.

O painel salva o arquivo na pasta escolhida — criando um nome novo automaticamente se já existir um
arquivo com o mesmo nome, para nunca sobrescrever por engano — e insere sozinho o trecho
`![legenda](caminho/da/imagem.png)` no fim do texto, já com o caminho relativo certo a partir da
página que você está editando. Depois é só mover esse trecho para onde quiser dentro do texto e
salvar.
