#!/usr/bin/env python3
"""Converte PDFs de referencias/pdfs/ em Markdown de alta fidelidade.

Usa o Docling (IBM) para reconstruir texto, títulos e tabelas dos livros de D&D 5e
guardados em `referencias/pdfs/`. Exige o ambiente dedicado `.venv-pdf` (ver
PDF_CONVERTER.md na raiz do projeto) — não usa o `.venv` do Painel, pois o Docling
traz uma stack pesada (torch, transformers, modelos de layout/tabela).

Uso:
    .venv-pdf\\Scripts\\python.exe scripts\\converter_pdfs.py --listar
    .venv-pdf\\Scripts\\python.exe scripts\\converter_pdfs.py 3
    .venv-pdf\\Scripts\\python.exe scripts\\converter_pdfs.py "Manual dos Monstros"
    .venv-pdf\\Scripts\\python.exe scripts\\converter_pdfs.py todos

O resultado vai para referencias/pdfs/md/<mesmo-nome>.md.
"""

from __future__ import annotations

import sys
import time
import unicodedata
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

RAIZ = Path(__file__).resolve().parent.parent
PASTA_PDFS = RAIZ / "referencias" / "pdfs"
PASTA_SAIDA = PASTA_PDFS / "md"


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()


def listar_pdfs() -> list[Path]:
    if not PASTA_PDFS.is_dir():
        raise SystemExit(f"Pasta não encontrada: {PASTA_PDFS}")
    return sorted(
        (p for p in PASTA_PDFS.iterdir() if p.suffix.lower() == ".pdf"),
        key=lambda p: p.name.lower(),
    )


def imprimir_lista(pdfs: list[Path]) -> None:
    for i, pdf in enumerate(pdfs, start=1):
        tamanho_mb = pdf.stat().st_size / (1024 * 1024)
        print(f"  {i:2d}. {pdf.name}  ({tamanho_mb:.1f} MB)")


def escolher_arquivos(argumento: str | None, pdfs: list[Path]) -> list[Path]:
    if argumento is None:
        print("PDFs disponíveis em referencias/pdfs/:\n")
        imprimir_lista(pdfs)
        escolha = input("\nDigite o número do arquivo a converter (ou 'todos'): ").strip()
    else:
        escolha = argumento.strip()

    if escolha.lower() == "todos":
        return pdfs

    if escolha.isdigit():
        indice = int(escolha)
        if 1 <= indice <= len(pdfs):
            return [pdfs[indice - 1]]
        raise SystemExit(f"Número fora do intervalo (1 a {len(pdfs)}): {indice}")

    alvo = _normalizar(escolha)
    correspondencias = [p for p in pdfs if alvo in _normalizar(p.stem)]
    if not correspondencias:
        raise SystemExit(f"Nenhum PDF corresponde a {escolha!r}.")
    if len(correspondencias) > 1:
        nomes = "\n".join(f"  - {p.name}" for p in correspondencias)
        raise SystemExit(f"Mais de um PDF corresponde a {escolha!r}:\n{nomes}\nSeja mais específico.")
    return correspondencias


def converter(caminho_pdf: Path) -> Path:
    try:
        from docling.document_converter import DocumentConverter
    except ImportError as exc:
        raise SystemExit(
            "O pacote 'docling' não está instalado neste ambiente. "
            "Veja PDF_CONVERTER.md na raiz do projeto para criar o .venv-pdf."
        ) from exc

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    destino = PASTA_SAIDA / f"{caminho_pdf.stem}.md"

    print(f"Convertendo: {caminho_pdf.name}")
    inicio = time.monotonic()
    conversor = DocumentConverter()
    resultado = conversor.convert(str(caminho_pdf))
    markdown = resultado.document.export_to_markdown()
    destino.write_text(markdown, encoding="utf-8")
    decorrido = time.monotonic() - inicio

    print(f"  -> {destino.relative_to(RAIZ)}  ({decorrido:.1f}s)")
    return destino


def main() -> None:
    argumentos = sys.argv[1:]
    pdfs = listar_pdfs()

    if not pdfs:
        raise SystemExit(f"Nenhum PDF encontrado em {PASTA_PDFS}")

    if argumentos and argumentos[0] in ("-h", "--help"):
        print(__doc__)
        return

    if argumentos and argumentos[0] == "--listar":
        print("PDFs disponíveis em referencias/pdfs/:\n")
        imprimir_lista(pdfs)
        return

    argumento = argumentos[0] if argumentos else None
    alvos = escolher_arquivos(argumento, pdfs)

    for pdf in alvos:
        converter(pdf)


if __name__ == "__main__":
    main()
