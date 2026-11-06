# Conversor de PDF para Markdown

Converte os livros de D&D 5e guardados em `referencias/pdfs/` para Markdown, para que eu (Claude
Code) possa ler o conteúdo e importar magias, monstros, classes etc. para a wiki sem depender de
abrir o PDF original a cada consulta.

Usa o [Docling](https://docling-project.github.io/docling/) (IBM) — reconstrói títulos, texto
corrido e tabelas com alta fidelidade. Como todos os PDFs desta pasta já têm texto selecionável
(não são scans de imagem), não é necessário OCR: o trabalho do Docling é só reorganizar o layout
(colunas, tabelas, stat-blocks), não decifrar caracteres.

## 1. Instalação (uma vez só)

O Docling traz uma stack pesada (torch, transformers, modelos de layout/tabela — alguns GB). Por
isso ele vive num ambiente **separado** do `.venv` do Painel, pra não inflar nem arriscar o
ambiente do site.

```
python -m venv .venv-pdf
.venv-pdf\Scripts\pip install -r scripts\requisitos_conversor_pdf.txt
```

Isso baixa e instala o Docling e suas dependências — pode levar vários minutos e alguns GB de
disco na primeira vez. É esperado.

## 2. Ver quais PDFs existem

```
.venv-pdf\Scripts\python.exe scripts\converter_pdfs.py --listar
```

## 3. Converter um arquivo

Por número (da lista acima):

```
.venv-pdf\Scripts\python.exe scripts\converter_pdfs.py 6
```

Ou por nome (ou parte dele, sem se preocupar com acento/maiúscula):

```
.venv-pdf\Scripts\python.exe scripts\converter_pdfs.py "Manual dos Monstros"
```

Sem nenhum argumento, o script mostra a lista e pergunta o número interativamente:

```
.venv-pdf\Scripts\python.exe scripts\converter_pdfs.py
```

## 4. Converter todos de uma vez

```
.venv-pdf\Scripts\python.exe scripts\converter_pdfs.py todos
```

Os livros grandes (Manual dos Monstros, Guia do Volo, Guia de Xanathar) podem levar bastante tempo
— a prioridade aqui é fidelidade, não velocidade.

## 5. Onde o resultado aparece

Cada PDF gera um arquivo correspondente em `referencias/pdfs/md/<mesmo-nome>.md`. Nem os PDFs
originais nem os `.md` gerados entram no git (ver `.gitignore`) — ficam só na sua máquina.

## Fidelidade e revisão

O Docling resolve a maior parte do trabalho de reconstrução automaticamente, mas tabelas muito
densas ou stat-blocks com formatação incomum podem sair levemente desalinhados. Isso é esperado:
ao importar algo específico pra wiki (uma magia, um monstro), vale conferir o trecho relevante do
`.md` contra o PDF original antes de cadastrar, em vez de confiar 100% no automático.

## Alternativa (se a qualidade do Docling desapontar em algum livro)

O [Marker](https://github.com/datalab-to/marker) é outra opção de alta fidelidade, mas a versão
atual tem um conflito de dependência conhecido no Python 3.14 (o Python deste projeto): o pacote
`surya-ocr`, usado pelo Marker, trava num pin de versão do `Pillow` incompatível. Se quiser testar
o Marker mesmo assim, provavelmente vai precisar de um `.venv-pdf` com um Python mais antigo
(3.11/3.12) só para ele.
