"""Ponto de entrada da automação.

Execução:

    python -m src.main --input input/solicitacoes.csv --output output/resultado.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

import requests

from .api_client import DocumentApiClient
from .config import ConfigError, Settings, load_settings
from .logging_config import setup_logging
from .models import DocumentRequest, ProcessingResult, Summary
from .processor import RequestProcessor
from .reader import InputFileError, read_requests
from .writer import write_results

logger = logging.getLogger(__name__)

DEFAULT_INPUT = Path("input/solicitacoes.csv")
DEFAULT_OUTPUT = Path("output/resultado.csv")

EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Consulta documentos fiscais a partir de um CSV de solicitações.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"CSV de entrada (padrão: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"CSV de saída (padrão: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Arquivo .env alternativo (padrão: .env da raiz do projeto)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibe logs em nível DEBUG",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    """Executa a automação e devolve o código de saída do processo."""
    args = build_parser().parse_args(argv)

    try:
        settings = load_settings(args.env_file)
    except ConfigError as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    setup_logging(settings.log_file, verbose=args.verbose)
    logger.info("Iniciando automação (entrada=%s, saída=%s)", args.input, args.output)

    try:
        requests_to_process = read_requests(args.input)
    except InputFileError as exc:
        logger.error("%s", exc)
        return EXIT_CONFIG_ERROR

    results = _process(settings, requests_to_process)
    write_results(args.output, results)

    summary = Summary.from_results(results)
    logger.info(
        "Resumo: total=%d sucesso=%d não encontrados=%d inválidos=%d erros=%d",
        summary.total,
        summary.success,
        summary.not_found,
        summary.invalid,
        summary.errors,
    )
    print()
    print(summary.as_text())
    return EXIT_SUCCESS


def _process(
    settings: Settings, requests_to_process: Sequence[DocumentRequest]
) -> list[ProcessingResult]:
    """Cria a sessão HTTP e processa as solicitações."""
    with requests.Session() as session:
        client = DocumentApiClient(settings, session=session)
        processor = RequestProcessor(client)
        return processor.process_all(requests_to_process)


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
