"""Escrita do CSV consolidado com os resultados."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Sequence

from .models import ProcessingResult

logger = logging.getLogger(__name__)

CSV_COLUMNS = (
    "request_id",
    "status",
    "http_status",
    "attempts",
    "message",
    "document_count",
    "processed_at",
)


def write_results(path: Path, results: Sequence[ProcessingResult]) -> None:
    """Grava o arquivo de saída, sobrescrevendo o conteúdo anterior.

    O arquivo é sempre reescrito por completo, então executar a automação
    novamente com a mesma entrada produz o mesmo resultado.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for result in results:
            writer.writerow(result.to_row())

    logger.info("Arquivo de saída gerado: %s (%d linhas)", path, len(results))
