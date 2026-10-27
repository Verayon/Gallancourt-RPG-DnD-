# Manutenção do projeto — guia técnico

Este é o manual de operação do projeto: como ligar e desligar as coisas, os comandos do dia a dia,
o que fazer quando algo dá errado, e o que cada pasta é. A ideia é que você consiga rodar tudo isso
sem precisar me perguntar. `README.md` é a instalação inicial; este arquivo é o "e agora, no
dia a dia".

## Sumário

1. [As três peças do projeto](#1-as-três-peças-do-projeto)
2. [Rotina do dia a dia](#2-rotina-do-dia-a-dia)
3. [Comandos de referência](#3-comandos-de-referência)
4. [Estrutura de pastas](#4-estrutura-de-pastas)
5. [Git: o essencial](#5-git-o-essencial)
6. [Solução de problemas comuns](#6-solução-de-problemas-comuns)
7. [Quando chamar o Claude Code](#7-quando-chamar-o-claude-code)
8. [Testar o site](#8-testar-o-site)
9. [Usar o Claude Code gastando menos](#9-usar-o-claude-code-gastando-menos)

---

## 1. As duas peças do projeto

| Peça | O que é | Onde roda | Precisa de internet? |
|---|---|---|---|
| **O servidor** (`admin/app.py`) | Um único processo que serve o site inteiro (wiki + formulários do Painel do Mestre, embutidos nas páginas certas) e escreve nos arquivos por você quando você usa um formulário | `http://127.0.0.1:5001` | Não |
| **O git** | Guarda o histórico de tudo e é a "cópia de segurança" | Sua pasta local + (se você configurar) o GitHub | Só para `git push`/`git pull` |

Não existem mais dois endereços nem dois comandos pra lembrar de ligar — `admin/app.py` já serve
tudo. Internamente ele guarda uma cópia já construída do site (pasta `site/`) e, a cada formulário
salvo, reconstrói e troca essa cópia sozinho antes de responder — então a próxima página que você
abrir já reflete a mudança, sem precisar de um segundo processo de "recarga automática" rodando.

Só editando arquivos `.md` direto no editor de código (sem usar nenhum formulário do Painel) que
vale abrir, **à parte**, o `mkdocs serve` (porta 8000) — ele recarrega a cada salvamento sem
esperar o build completo do `admin/app.py`. Para o uso normal do dia a dia (navegar, cadastrar
NPC/Lugar/Jogador, criar e tocar sessão), só o `admin/app.py` já basta.

Nada disso é publicado na internet até você decidir publicar (ver `README.md`, seção "Publicar o
site"). Enquanto isso, só quem está no seu computador acessa `127.0.0.1`.

---

## 2. Rotina do dia a dia

### Para começar a trabalhar

Abra um terminal na pasta do projeto (`gallancourt-rpg-dnd-`) e rode:

```powershell
.venv\Scripts\python admin\app.py
```

Ou dê duplo clique em `admin\iniciar-painel.bat` (abre sozinho numa janela). Deixe a janela aberta
enquanto usa o site — fechá-la desliga tudo.

Depois, abra no navegador:

- **http://127.0.0.1:5001** — o site inteiro, com os formulários do Painel embutidos

### Enquanto trabalha

- Usando um formulário embutido (Adicionar NPC/Lugar/Jogador, Nova sessão) ou o Painel direto: o
  próprio servidor reconstrói o site antes de responder — recarregue a página pra ver a mudança.
  Esses formulários só funcionam com o `admin/app.py` ligado neste computador; eles não existem
  numa cópia do site publicada só como arquivos estáticos (ver `README.md`, "Publicar o site").
- Editando **arquivos `.md` direto** (VS Code, Claude Code): a mudança só aparece no site servido
  por `admin/app.py` depois do próximo build (próxima vez que você salvar algo por um formulário,
  ou rodando `mkdocs build --strict` você mesmo). Pra ver o resultado instantaneamente a cada
  salvamento, abra `mkdocs serve` (porta 8000) à parte, só enquanto estiver editando Markdown à
  mão.

### Para terminar

Feche as janelas de terminal (ou `Ctrl+C` dentro de cada uma) e depois **salve no git**:

```powershell
git add -A
git commit -m "Descreve o que mudou"
git push          # só se você tiver configurado um repositório remoto
```

Fazer isso ao final de cada sessão de trabalho é o que faz a data "Última atualização" de cada
página (no rodapé do site) ficar correta, e é sua cópia de segurança de verdade.

---

## 3. Comandos de referência

Rode todos a partir da pasta `gallancourt-rpg-dnd-`, com o ambiente virtual já criado (ver
`README.md` se `.venv\` não existir ainda).

| O que você quer fazer | Comando |
|---|---|
| Ligar o site + Painel do Mestre (uso normal) | `.venv\Scripts\python admin\app.py` |
| Ligar só a recarga automática ao editar `.md` à mão | `.venv\Scripts\mkdocs serve` |
| Ligar essa recarga numa porta diferente | `.venv\Scripts\mkdocs serve -a 127.0.0.1:8001` |
| Conferir se o site está sem erros | `.venv\Scripts\mkdocs build --strict` |
| Rodar o teste completo do site | `.venv\Scripts\python scripts\testar_site.py` |
| Gerar o site como arquivos estáticos (pasta `site/`) | `.venv\Scripts\mkdocs build` |
| Regenerar as tabelas de relações/intrigas | `.venv\Scripts\python scripts\gerar_relacoes.py` |
| Instalar/atualizar as dependências | `.venv\Scripts\pip install -r requirements.txt` |
| Recriar o ambiente virtual do zero | `python -m venv .venv` (depois o comando acima) |
| Ver o que mudou desde o último commit | `git status` |
| Ver as diferenças linha a linha | `git diff` |
| Salvar tudo no histórico | `git add -A` seguido de `git commit -m "mensagem"` |
| Enviar para o GitHub (se configurado) | `git push` |
| Ver o histórico de commits | `git log --oneline -20` |
| Descartar mudanças não salvas num arquivo | `git checkout -- caminho\do\arquivo.md` |
| Ver quem editou uma página e quando | `git log --follow -- docs\caminho\pagina.md` |

`mkdocs build --strict` é o comando mais importante para confiar que nada quebrou: ele falha (com
uma mensagem clara) se algum link, âncora ou item do menu estiver errado. O Painel do Mestre já
roda esse comando sozinho depois de aplicar uma sessão ou uma ficha — mas se você editar arquivos
à mão, vale rodar você mesmo antes de um `git commit`.

---

## 4. Estrutura de pastas

```
gallancourt-rpg-dnd-/
├── docs/                A wiki em si — tudo o que aparece no site vem daqui
│   ├── index.md, lore/, wiki/   Início, Lore e o hub da Wiki
│   ├── cidades/ personagens/ faccoes/ eventos/ geografia/ mundo/   O conteúdo da Wiki
│   │                     (personagens/ aparece no site como "NPCs")
│   ├── diario/           O Diário de Sessões (uma página por sessão jogada)
│   ├── compendio/        Versão longa e anotada da história e das cidades
│   ├── mestre/           Mestre: sessões (mestre/sessoes/), referência rápida, e as páginas
│   │                     de Configurações, inclusive o guia do Painel (painel.md)
│   ├── configuracoes/    Página de entrada de Configurações
│   ├── javascripts/      Filtros e ordenação da tabela de NPCs
│   ├── assets/           Imagens do site: molduras provisórias, fundo da página inicial,
│   │                     e assets/imagens/ — onde você coloca arte de verdade
│   └── stylesheets/      O CSS do visual "high fantasy"
├── hooks/                Código que roda ao gerar o site: caixa e abas dos NPCs, tabela de
│                         NPCs, lista de sessões (gallancourt.py) e linha do tempo (linha_tempo.py)
├── dados/
│   └── linha-do-tempo.yml   Acontecimentos da campanha (escrito pela aba Linha do tempo do Painel)
├── admin/                O Painel do Mestre (app Flask), fora do site publicado
│   ├── app.py            As rotas (páginas) do painel
│   ├── wiki_data.py       Toda a lógica de ler/escrever os arquivos da wiki
│   ├── templates/, static/   O HTML e CSS do painel
│   └── iniciar-painel.bat    Atalho para abrir o painel no Windows
├── fontes/               Documentos originais do autor (PDFs, dossiê) — não editar
├── scripts/
│   └── gerar_relacoes.py    Gera as tabelas de relações entre cidades e intrigas da nobreza
├── mkdocs.yml            Configuração do site inteiro: tema, cores, e o menu (nav)
├── requirements.txt      As dependências Python do projeto
├── CLAUDE.md             Regras e convenções lidas pelo Claude Code a cada sessão
├── README.md             Passo a passo de instalação
└── MANUTENCAO.md         Este arquivo
```

Regra prática: se você quer saber **o que muda o conteúdo**, é `docs/`. Se quer saber **como o
site se comporta** (cores, menu, plugins), é `mkdocs.yml` e `docs/stylesheets/extra.css`. Se quer
saber **como o painel funciona por dentro**, é `admin/wiki_data.py`.

---

## 5. Git: o essencial

Você não precisa saber git a fundo, só este ciclo:

1. **`git status`** — mostra o que mudou desde o último commit. Rode isso sempre que tiver dúvida
   sobre o que você alterou.
2. **`git add -A`** — marca tudo que mudou para ser salvo no próximo commit.
3. **`git commit -m "mensagem"`** — salva esse "retrato" do projeto no histórico, com uma mensagem
   descrevendo o que mudou (ex.: `"Sessão 3 e ficha de Scyras"`).
4. **`git push`** — envia o histórico para o GitHub, se você tiver um repositório remoto
   configurado (o projeto já indica um em `git remote -v`).

Se alguma coisa der errado e você quiser **voltar atrás**:

- Mudou um arquivo e quer descartar a mudança (ainda não commitou): `git checkout -- arquivo.md`.
- Quer ver o que mudou num commit específico: `git show <hash-do-commit>`.
- Quer voltar o projeto inteiro para um commit anterior **sem perder o histórico**:
  `git revert <hash-do-commit>`.
- Quer apagar de vez commits recentes (cuidado, isso reescreve o histórico):
  `git reset --hard <hash-do-commit>` — só use se tiver certeza, e nunca depois de já ter dado
  `git push` desses commits para um repositório compartilhado.

Na dúvida antes de qualquer comando que "desfaz" coisa, rode `git status` e `git log --oneline -10`
primeiro para saber exatamente onde você está.

---

## 6. Solução de problemas comuns

**"Endereço já está em uso" ao ligar o site**
Já tem um processo rodando naquela porta (às vezes de uma sessão anterior que não foi fechada
direito). Descubra e feche:

```powershell
netstat -ano | findstr :5001        # troque 5001 por 8000 se for o mkdocs serve
taskkill /PID <numero-que-apareceu> /F
```

Ou simplesmente feche a janela de terminal onde o servidor antigo ficou aberto.

**O site abriu mas não mostra minhas mudanças**
Se a mudança veio de um formulário do Painel, confira se apareceu algum erro na tela de
resultado — se o build falhou, o site antigo continua no ar e nada foi atualizado. Se a mudança
foi num arquivo `.md` editado à mão, ela só aparece depois do próximo build: rode
`mkdocs build --strict` você mesmo, ou use `mkdocs serve` à parte enquanto estiver editando.
De qualquer forma, dê um "recarregar forçado" no navegador (`Ctrl+F5`) depois.

**`mkdocs build --strict` falhou**
A mensagem de erro sempre aponta o arquivo e o problema — os mais comuns são:

- *"contains a link ... but the doc ... does not contain an anchor"* — um link interno aponta para
  um título que não existe (ou o texto do título mudou). Corrija o link ou o título.
- *"is not included in the 'nav' configuration"* — você criou uma página `.md` nova mas esqueceu
  de listá-la no `nav:` do `mkdocs.yml`.
- Um aviso do plugin de data (`git_revision_date_localized`) sozinho não deveria travar o build no
  projeto real (só acontece em cópias de teste sem `.git`) — se acontecer aqui, me avise.

**O ambiente virtual sumiu ou dá erro de "mkdocs não é reconhecido"**
Recrie do zero:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

**Uma edição pelo Painel saiu errada**
Nada é destrutivo de forma irreversível enquanto você não der `git commit`: rode `git diff` para
ver exatamente o que mudou, e `git checkout -- caminho\do\arquivo.md` para desfazer a mudança
naquele arquivo específico.

**As fontes (letras) do site não carregam**
O visual usa duas fontes do Google Fonts, carregadas pela internet na primeira visita. Sem
internet, o navegador usa uma fonte parecida no lugar — o site continua funcionando, só o visual
fica levemente diferente.

---

## 7. Quando chamar o Claude Code

Você não precisa de mim para o dia a dia — registrar sessões, preencher fichas e editar texto já
dá para fazer pelo Painel ou direto no `.md`. Vale me chamar quando for:

- mudar a **estrutura** do site (menu, categorias novas, visual);
- mudar como o **Painel do Mestre** funciona (novos campos de ficha, nova automação);
- resolver um **erro de build** que a mensagem não deixou óbvio;
- **consolidar** um documento novo do autor (PDF, notas) na wiki;
- qualquer coisa que envolva editar `admin/wiki_data.py`, `mkdocs.yml` ou o CSS.

Para essas tarefas, use os **comandos do projeto** (digite no Claude Code):

| Comando | O que faz |
|---|---|
| `/testar-site` | Roda o teste fixo e diz o que passou e o que falhou (ver seção 8) |
| `/incorporar-documento caminho/do/arquivo` | Compara um texto novo seu com a wiki, pergunta sobre os conflitos e incorpora |
| `/nova-pagina tipo assunto` | Cria uma cidade, evento, facção, NPC ou lugar no padrão do site, com menu e links |

---

## 8. Testar o site

O teste é **fixo**: valida sempre as mesmas 21 coisas, na mesma ordem, numa **cópia temporária**
do projeto — ele nunca muda os seus arquivos.

| Grupo | O que confere |
|---|---|
| 1. Cálculos | Fórmulas da ficha de D&D 5e e ordem da linha do tempo |
| 2. Menu | As 6 categorias de topo e as subcategorias da Wiki, na ordem combinada; todo NPC no menu |
| 3. Relações | O gerador de relações não muda nada se rodado de novo |
| 4. Build | `mkdocs build --strict` sem erros nem links quebrados |
| 5. Páginas | Tabela de NPCs, caixa e abas de cada NPC, lista de sessões, botões, linha do tempo |
| 6. Navegador | Busca, ordenação e filtros da tabela, abas do NPC, menu no celular |
| 7. Painel | Criar NPC com ficha, criar sessão, registrar acontecimento e ver o efeito no site |

Há três formas de rodar, todas com o mesmo resultado:

1. **No terminal:** `.venv\Scripts\python scripts\testar_site.py` (cerca de 30 segundos). Opções:
   `--sem-navegador`, `--sem-painel`, `--manter` (guarda a cópia para investigar).
2. **No Claude Code:** digite `/testar-site`. O Claude roda o teste, lê só o resumo e explica o que
   falhou — mas **não corrige nada sem você pedir**.
3. **No GitHub, sem o Claude e sem gastar tokens:** aba **Actions** → **Testar o site** →
   **Run workflow** (funciona pelo app do GitHub no celular). O resultado, com ✅ e ❌, aparece no
   resumo da execução. Ele só roda quando você manda.

Os testes do grupo 6 abrem um navegador invisível. No seu computador, eles só rodam depois de
instalar uma vez:

```powershell
.venv\Scripts\pip install playwright
.venv\Scripts\python -m playwright install chromium
```

Sem isso, o grupo 6 aparece como ⏭️ **PULADO** (não é falha). No GitHub ele sempre roda.

Se uma mudança **combinada com você** fizer um teste falhar (por exemplo, um item novo no menu),
a lista do que é esperado fica no topo de `scripts/testar_site.py` (`MENU_TOPO`, `MENU_WIKI`,
`COLUNAS_NPC`) — peça ao Claude para atualizá-la.

---

## 9. Usar o Claude Code gastando menos

Cada mensagem reenvia toda a conversa anterior, e cada sessão começa lendo o `CLAUDE.md`. O que
mais economiza:

| Faça | Em vez de |
|---|---|
| **Painel do Mestre** para o rotineiro: NPC, ficha, sessão, morte, viagem | Pedir ao Claude para editar os arquivos |
| **Uma sessão por assunto**; para um assunto novo, abra uma sessão nova | Uma conversa longa que mistura tudo |
| **Pedido completo de uma vez**: "Crie o NPC X: título, cidade, afiliação, descrição…" | Várias mensagens curtas com idas e voltas |
| **Diga onde**: "Na página de Dodixie, seção Pontos de interesse, acrescente…" | "Coloca isso em algum lugar do site" |
| **Cole o texto pronto** e diga "incorpore como está" | Pedir que o Claude escreva ou reescreva |
| **Use os comandos** `/nova-pagina`, `/incorporar-documento`, `/testar-site` | Explicar o processo de novo a cada vez |
| **Modelo mais leve** (Sonnet ou Haiku, em `/model`) para correções pequenas | O modelo mais forte para tudo |
| `/testar-site` **só quando quiser validar**, ou o botão do GitHub (grátis) | Pedir para "testar tudo" a cada mudança |

O `CLAUDE.md` foi enxugado para o essencial (regras, decisões, onde fica cada coisa). Os detalhes
de cada área ficam em `.claude/contexto/`, e o Claude só os lê quando a tarefa envolve aquela área.
Ao tomar uma decisão nova sobre o mundo ou o site, peça para registrá-la no `CLAUDE.md` (se for
regra geral) ou no arquivo de contexto da área.

