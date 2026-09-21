"""Leitura do CSV de solicitações."""

from __future__ import annotations

import csv
from pathlib import Path

from src.models import DocumentRequest

REQUIRED_COLUMNS = ("request_id", "company_name", "cnpj", "uf", "document_type", "competence")


class InputFileError(Exception):
    """Arquivo de entrada inexistente ou com estrutura inválida."""


def read_requests(path: Path) -> list[DocumentRequest]:
    """Lê o CSV e devolve as linhas com os espaços das bordas removidos.

    Nenhuma regra de negócio é aplicada aqui: a validação fica em ``validator``.
    """
    if not path.is_file():
        raise InputFileError(f"Arquivo de entrada não encontrado: {path}")

    try:
        # utf-8-sig ignora o BOM que o Excel costuma gravar.
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            header = [name.strip() for name in (reader.fieldnames or [])]
            missing = [column for column in REQUIRED_COLUMNS if column not in header]
            if missing:
                raise InputFileError(
                    f"Colunas obrigatórias ausentes em {path}: {', '.join(missing)}"
                )
            reader.fieldnames = header

            requests: list[DocumentRequest] = []
            for row in reader:
                values = {column: (row.get(column) or "").strip() for column in REQUIRED_COLUMNS}
                if not any(values.values()):
                    continue  # linha em branco
                requests.append(
                    DocumentRequest(
                        **values,
                        line_number=reader.line_num,
                        format_error=_column_count_error(row, len(header)),
                    )
                )
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise InputFileError(f"Não foi possível ler {path}: {exc}") from exc

    return requests


def _column_count_error(row: dict[str | None, object], expected: int) -> str:
    """Detecta linhas com colunas a mais ou a menos que o cabeçalho.

    O ``DictReader`` guarda valores excedentes na chave ``None`` e preenche colunas
    faltantes com ``None``. Nesses casos os campos ficam deslocados, então validar
    UF, CNPJ etc. geraria mensagens enganosas; é melhor apontar a causa real.
    """
    extra = row.get(None)
    if isinstance(extra, list) and extra:
        return (
            f"linha com {expected + len(extra)} colunas, esperado {expected} "
            "(vírgula sem aspas em algum campo?)"
        )
    missing = sum(1 for key, value in row.items() if key is not None and value is None)
    if missing:
        return f"linha com {expected - missing} colunas, esperado {expected}"
    return ""
