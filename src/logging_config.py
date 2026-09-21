"""Configuração de logs: arquivo detalhado + console resumido."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(log_file: Path, verbose: bool = False) -> None:
    """Grava tudo (DEBUG) no arquivo e mostra apenas avisos/erros no console.

    O arquivo é aberto em modo append para manter o histórico entre execuções.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO if verbose else logging.WARNING)
    console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console_handler)

    # Bibliotecas de terceiros só poluiriam o log com detalhes de conexão.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
