"""Leitura do arquivo CSV de solicitações."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from .models import DocumentRequest

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = (
    "request_id",
    "company_name",
    "cnpj",
    "uf",
    "document_type",
    "competence",
)

FIRST_DATA_LINE = 2  # a linha 1 é o cabeçalho


class InputFileError(RuntimeError):
    """O arquivo de entrada não existe ou não está no formato esperado."""


def read_requests(path: Path) -> list[DocumentRequest]:
    """Lê o CSV de entrada e devolve as solicitações na ordem original.

    O arquivo é lido como `utf-8-sig` para suportar CSVs salvos pelo Excel,
    que incluem BOM no início do arquivo.
    """
    if not path.is_file():
        raise InputFileError(f"Arquivo de entrada não encontrado: {path}")

    try:
        with path.open(encoding="utf-8-sig", newline="") as arquivo:
            reader = csv.DictReader(arquivo)
            _ensure_required_columns(path, reader.fieldnames)
            requests = [
                _build_request(row, line_number)
                for line_number, row in enumerate(reader, start=FIRST_DATA_LINE)
            ]
    except UnicodeDecodeError as exc:
        raise InputFileError(f"Não foi possível ler o arquivo {path}: {exc}") from exc

    logger.info("Arquivo de entrada lido: %s (%d solicitações)", path, len(requests))
    return requests


def _ensure_required_columns(path: Path, fieldnames: list[str] | None) -> None:
    columns = {name.strip() for name in fieldnames or [] if name}
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing:
        raise InputFileError(
            f"Colunas obrigatórias ausentes em {path}: {', '.join(missing)}"
        )


def _build_request(row: dict[str, str | None], line_number: int) -> DocumentRequest:
    return DocumentRequest(
        request_id=_clean(row.get("request_id")),
        company_name=_clean(row.get("company_name")),
        cnpj=_clean(row.get("cnpj")),
        uf=_clean(row.get("uf")),
        document_type=_clean(row.get("document_type")),
        competence=_clean(row.get("competence")),
        line_number=line_number,
    )


def _clean(value: str | None) -> str:
    return (value or "").strip()
