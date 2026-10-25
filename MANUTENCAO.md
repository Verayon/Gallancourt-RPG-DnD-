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

---

## 1. As três peças do projeto

| Peça | O que é | Onde roda | Precisa de internet? |
|---|---|---|---|
| **O site** (`mkdocs serve`) | Gera e serve a wiki a partir dos arquivos `.md` em `docs/` | `http://127.0.0.1:8000` | Não (só as fontes do Google, na primeira vez que o navegador carrega a página) |
| **O Painel do Mestre** (`admin/app.py`) | App separado que escreve nos arquivos por você (sessões, fichas, edição) | `http://127.0.0.1:5001` | Não |
| **O git** | Guarda o histórico de tudo e é a "cópia de segurança" | Sua pasta local + (se você configurar) o GitHub | Só para `git push`/`git pull` |

As três são **independentes**: o Painel pode estar fechado enquanto você só lê o site; o site pode
estar fechado enquanto você só edita no Painel (mas você não vê o resultado até abrir o site). O
Painel só faz sentido junto com o site aberto, porque é o `mkdocs serve` que atualiza a página
sozinho quando o Painel salva um arquivo.

Nenhuma das duas é publicada na internet até você decidir publicar (ver `README.md`, seção
"Publicar o site"). Enquanto isso, só quem está no seu computador acessa `127.0.0.1`.

---

## 2. Rotina do dia a dia

### Para começar a trabalhar

Abra um terminal na pasta do projeto (`gallancourt-rpg-dnd-`) e rode, em **duas janelas de
terminal separadas** (cada comando abaixo bloqueia o terminal enquanto roda):

```powershell
# Janela 1 — o site
.venv\Scripts\mkdocs serve

# Janela 2 — o painel (só se for registrar sessão, ficha ou editar por lá)
.venv\Scripts\python admin\app.py
```

Ou, para o painel, dê duplo clique em `admin\iniciar-painel.bat` (abre sozinho numa janela).

Depois, abra no navegador:

- **http://127.0.0.1:8000** — o site
- **http://127.0.0.1:5001** — o painel (se estiver usando)

### Enquanto trabalha

- Editando pelo **Painel**: marque as sessões/fichas, salve. O site recarrega sozinho.
- Os botões **Adicionar NPC** (página NPCs) e **Nova sessão** (Mestre → Sessões) do site abrem o
  Painel. Eles só funcionam com o Painel ligado neste computador; no site publicado na internet,
  o botão abre uma página em branco se o Painel estiver desligado.
- Editando **arquivos `.md` direto** (VS Code, Claude Code): salve o arquivo. O site recarrega
  sozinho também — o `mkdocs serve` observa a pasta `docs/` inteira.
- Se mudar `mkdocs.yml` (o menu do site), o `mkdocs serve` também detecta e recarrega.

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
| Ligar o site | `.venv\Scripts\mkdocs serve` |
| Ligar o site numa porta diferente | `.venv\Scripts\mkdocs serve -a 127.0.0.1:8001` |
| Ligar o Painel do Mestre | `.venv\Scripts\python admin\app.py` |
| Conferir se o site está sem erros | `.venv\Scripts\mkdocs build --strict` |
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
│                         NPCs e lista de sessões (gallancourt.py)
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

**"Endereço já está em uso" ao ligar o site ou o painel**
Já tem um processo rodando naquela porta (às vezes de uma sessão anterior que não foi fechada
direito). Descubra e feche:

```powershell
netstat -ano | findstr :8000        # troque 8000 por 5001 para o painel
taskkill /PID <numero-que-apareceu> /F
```

Ou simplesmente feche a janela de terminal onde o servidor antigo ficou aberto.

**O site abriu mas não mostra minhas mudanças**
Confira se o terminal do `mkdocs serve` ainda está aberto e sem mensagens de erro em vermelho. Dê
um "recarregar forçado" no navegador (`Ctrl+F5`). Se editou `mkdocs.yml`, espere alguns segundos —
ele reconstrói o site inteiro, que demora um pouco mais que uma página só.

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
