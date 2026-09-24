"""Escrita do CSV consolidado."""

from __future__ import annotations

import csv
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

from src.models import ProcessingResult

OUTPUT_COLUMNS = (
    "request_id",
    "status",
    "http_status",
    "attempts",
    "message",
    "document_count",
    "processed_at",
)


def _apply_default_permissions(name: str) -> None:
    """Aplica ``0666 & ~umask`` ao arquivo, como faria um ``open()`` comum.

    Não há como ler o umask sem trocá-lo, então o valor é restaurado em seguida.
    No Windows o ``chmod`` só controla o atributo somente-leitura e nada muda.
    """
    umask = os.umask(0)
    os.umask(umask)
    try:
        os.chmod(name, 0o666 & ~umask)
    except OSError:  # sistemas de arquivos sem suporte a permissões
        pass


def write_results(path: Path, results: Iterable[ProcessingResult]) -> None:
    """Grava o CSV de forma atômica: escreve em um arquivo temporário e o renomeia.

    Assim uma execução interrompida nunca deixa um ``resultado.csv`` pela metade, e
    executar novamente sobrescreve o arquivo anterior (idempotência).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        # mkstemp cria o arquivo com 0600, e esse modo sobreviveria ao os.replace.
        # O CSV de saída não é sigiloso: vale o padrão do sistema (0666 menos o umask).
        _apply_default_permissions(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        "request_id": result.request_id,
                        "status": result.status.value,
                        "http_status": "" if result.http_status is None else result.http_status,
                        "attempts": result.attempts,
                        "message": result.message,
                        "document_count": "" if result.document_count is None else result.document_count,
                        "processed_at": result.processed_at,
                    }
                )
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
