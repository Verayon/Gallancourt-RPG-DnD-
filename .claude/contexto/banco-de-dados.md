# Banco de dados (SQLite + SQLAlchemy + Alembic)

> Detalhes de referência, separados do `CLAUDE.md` para economizar contexto.
> Leia este arquivo antes de mexer em `admin/banco.py`, `alembic/`, `tests/` ou decidir se algo
> deve virar dado de banco.

## Por que existe

Fundação implementada na Etapa B do pedido de rearquitetura do autor (ver `ARQUITETURA.md` pro
diagnóstico completo e a decisão de **não** reescrever o projeto para Next.js/Postgres/Prisma).
Markdown/YAML continuam sendo a fonte única de verdade de tudo que já funciona hoje — lore,
fichas de combate, NPCs, Changelog, Roadmap, linha do tempo. O banco existe só para dado
operacional **novo**, que precisa de consulta relacional de verdade (algo que `rglob("*.md")` +
regex não resolve bem) e que **não** precisa do versionamento em git que o Markdown/YAML já dão de
graça.

## O que existe hoje

- `admin/banco.py`: isolado do Flask de propósito (mesmo padrão de `wiki_data.py`/
  `sessao_viva.py`). `criar_engine(root)` aponta pra `root/dados/gallancourt.db`. Dois modelos:
  `Campanha` (registro único — há uma campanha, Gallancourt) e `Fonte` (livros de referência:
  PHB, DMG, SRD…). Funções simples (`obter_ou_criar_campanha`, `listar_fontes`,
  `adicionar_fonte`, `apagar_fonte`, `semear`) recebem uma `Session` já aberta — não abrem/fecham
  conexão sozinhas.
- `alembic/` + `alembic.ini` (raiz do projeto): migrações versionadas. `alembic/env.py` importa
  `admin/banco.py` (via `sys.path.insert`, mesmo truque de `wiki_data.py` para importar `hooks/`)
  e usa sempre `banco.caminho_banco(ROOT)` como URL do banco — nunca lê um caminho fixo de
  `alembic.ini`, pra não divergir do caminho real usado pelo Flask.
- `admin/app.py`: `ENGINE_BANCO`/`SessaoBanco` criados na inicialização; rota `/fontes` (GET lista
  + formulário, POST salva, POST `/fontes/apagar`) — **não chama `publicar_build()`**, ponto
  central da fundação (escrita no banco não mexe em `docs/`, não precisa reconstruir o site). O
  `context_processor` (`_globais_template`) expõe `campanha` pra todo template — é por isso que o
  cabeçalho do Painel (`base.html`) mostra "— Crônicas de Gallancourt · D&D 2014".
- `dados/gallancourt.db`: **gitignorado** (ver `.gitignore`), reproduzível via
  `alembic upgrade head` + `banco.semear(sessao)` — nunca precisa ir pro git, ao contrário dos
  YAML de campanha (`dados/*.yml`), que continuam versionados de propósito.
- `tests/test_banco.py` (`pytest`, `pytest.ini` na raiz): primeira infraestrutura de teste de
  domínio do projeto — cada teste cria um banco SQLite temporário (`tmp_path`) via
  `Base.metadata.create_all`, nunca o banco real do autor.

## Rotina

```bash
alembic upgrade head        # cria/atualiza o schema — rodar uma vez após clonar, ou após puxar
                             # uma migração nova
pytest                       # roda os testes do banco
alembic revision --autogenerate -m "descrição"   # ao mudar os modelos em admin/banco.py
```

`scripts/testar_site.py::IGNORAR_NA_COPIA` já exclui `gallancourt.db`/`gallancourt.db-journal` ao
copiar o projeto pra uma cópia de teste (mesmo motivo do `painel_local.env`, corrigido antes desta
fundação: a cópia de teste não deve herdar segredos nem estado do autor).

## O que NÃO está migrado (de propósito — ver `ARQUITETURA.md` §"Fora de escopo")

- Changelog, Roadmap, linha do tempo (`dados/*.yml`) — continuam YAML, versionados em git.
- Fichas de combate, NPCs, jogadores (JSON embutido em Markdown) — maior ganho real (reuso de
  monstro em vários encontros), mas é a próxima fatia grande, não esta fundação.
- Qualquer motor de regras (`calcular_ataque`, `aplicar_dano`…) — não existe ainda; só faz sentido
  depois de ter Actor estruturado no banco.

Antes de propor migrar algo pra cá, confira se o ganho (consulta relacional, sem duplicação) supera
o custo de perder o versionamento em git que o arquivo atual já tem — e pergunte ao autor.
