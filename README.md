# Crônicas de Gallancourt

Wiki de lore da campanha de RPG (D&D) ambientada em **Gallancourt**, um reino partido entre a
Aliança dos Lordes e a teocracia de L'Ordre de Célestien.

O site é gerado com [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) a partir de
arquivos Markdown, com busca, tags, modo escuro e navegação por categorias.

Este arquivo é a instalação inicial. Para o dia a dia — ligar/desligar os servidores, comandos de
git, solução de problemas — veja **[MANUTENCAO.md](MANUTENCAO.md)**.

## Estrutura do conteúdo

```
docs/
├── index.md, lore/, wiki/   Início, Lore e o hub da Wiki
├── historia/       A crônica em capítulos + cronologia
├── eventos/        Batalhas, decretos e períodos (uma página por evento)
├── geografia/      Península, cordilheira, Cicatriz, ilhas, divisão territorial, mapas
├── cidades/        As 5 cidades da Aliança e as 3 de L'Ordre
├── faccoes/        Estados, as cinco casas, outras casas e organizações
├── personagens/    Uma página por NPC (no site: Wiki → NPCs)
├── mundo/          Conflitos, teia política, relações, intrigas, religião, economia, calendário
├── diario/         O Diário de Sessões — uma página por sessão jogada
├── compendio/      Leitura consolidada e anotada: história completa, cidades, política
├── mestre/         Sessões, referência rápida e as páginas de Configurações
├── configuracoes/  Entrada de Configurações (Painel, cânone, lacunas, fontes)
└── assets/         Imagens do site e o repositório de arte da campanha (assets/imagens/)
admin/              Painel do Mestre (app Flask local) — ver docs/mestre/painel.md
hooks/              Código que monta partes do site: NPCs, ficha de D&D 5e, linha do tempo
dados/              linha-do-tempo.yml — acontecimentos da campanha
fontes/             Acervo do autor (textos/, imagens/, videos/) — ver fontes/README.md
scripts/            gerar_relacoes.py (relações e intrigas) e testar_site.py (teste fixo do site)
.claude/            Comandos do projeto (/testar-site, /incorporar-documento, /nova-pagina) e contexto do Claude
.github/workflows/  Botão "Testar o site" no GitHub (só roda quando acionado)
CLAUDE.md           Regras e decisões do projeto, lidas pelo Claude Code em cada sessão
MANUTENCAO.md       Guia técnico: comandos, rotina do dia a dia, solução de problemas
```

## Trabalhando no computador com o Claude Code

### 1. Pré-requisitos

| Ferramenta | Para quê | Como obter |
|---|---|---|
| Git | Baixar e enviar o projeto | https://git-scm.com/downloads |
| Python 3.9+ | Gerar o site e rodar o script de relações | https://www.python.org/downloads/ (no Windows, marque "Add Python to PATH") |
| Claude Code | Editar a wiki com o Claude | https://code.claude.com/docs (terminal, app desktop ou extensão VS Code/JetBrains) |

### 2. Baixar o projeto

```bash
git clone https://github.com/verayon/gallancourt-rpg-dnd-.git
cd gallancourt-rpg-dnd-
```

Se o trabalho ainda não foi juntado ao `main` por um pull request, use o branch em que ele foi
feito:

```bash
git checkout claude/rpg-campaign-lore-wiki-c0sjy4
```

### 3. Instalar as dependências do site

Recomenda-se um ambiente virtual do Python:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Ver o site

```bash
mkdocs serve          # http://127.0.0.1:8000, com recarga automática a cada edição
mkdocs build --strict # gera ./site e falha se houver links ou âncoras quebrados
```

Para registrar uma sessão jogada ou editar uma página sem mexer em arquivo nenhum, abra também o
**Painel do Mestre** (com o `mkdocs serve` acima já rodando):

```bash
.venv\Scripts\python admin\app.py   # http://127.0.0.1:5001
```

Ou dê duplo clique em `admin/iniciar-painel.bat`. Guia completo em `docs/mestre/painel.md`.

### 5. Abrir o Claude Code no projeto

```bash
claude
```

O Claude Code lê o arquivo [`CLAUDE.md`](CLAUDE.md) automaticamente em toda sessão. Ele contém as
regras do projeto (só conteúdo pré-campanha, precedência das fontes, marcas de cânone), as decisões
já tomadas e as convenções das páginas — é o que substitui o contexto das conversas anteriores.
Mantenha-o atualizado quando tomar decisões novas; você pode pedir ao próprio Claude que faça isso.

Exemplos de pedidos:

- "Leia `fontes/` e me diga quais lacunas de `docs/mestre/lacunas.md` ainda estão abertas."
- "Crie a página do Coliseu do Herói em Valynesse; ele é …"
- "Mude a relação entre Dodixie e Saint-Armand para Tenso, porque …"
- "Incorpore este novo documento: …" (o Claude segue o checklist do `CLAUDE.md`)

### 6. Salvar e enviar as mudanças

```bash
git add -A
git commit -m "Descreve o que mudou"
git push
```

Ou peça ao Claude Code para fazer o commit e o push.

## Relações e intrigas

As páginas de relações entre cidades e de intrigas da nobreza, e as tabelas de relações dentro
das páginas de cidades e personagens, são geradas por `scripts/gerar_relacoes.py`. Para alterá-las,
edite as listas `PARES` e `INTRIGAS` no script e rode:

```bash
python3 scripts/gerar_relacoes.py
```

Não edite à mão o conteúdo entre `<!-- inicio:gerado -->` e `<!-- fim:gerado -->`.

## Publicar o site (opcional)

`mkdocs gh-deploy` publica o site no GitHub Pages do repositório. **Atenção:** o conteúdo marcado
como `SEGREDO` ficaria visível para qualquer pessoa com o link, inclusive os jogadores.

## Adicionando conteúdo

Veja `docs/mestre/manutencao-do-canone.md`: categorias de informação (cânone, leitura
cartográfica, inferência, em aberto), marcas de estado (`CANON`, `SEGREDO` …), modelo de ficha
de NPC e o passo a passo para criar uma página nova.
