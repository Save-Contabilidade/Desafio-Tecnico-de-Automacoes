"""Ponto de entrada da automação.

Uso:
    python -m src.main --input input/solicitacoes.csv --output output/resultado.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from src.api_client import DocumentApiClient
from src.config import ConfigError, load_settings
from src.logging_config import setup_logging
from src.processor import Summary, process_requests
from src.reader import InputFileError, read_requests
from src.writer import write_results

logger = logging.getLogger("src.main")

EXIT_OK = 0
EXIT_FAILURE = 1

LOG_FILE_NAME = "automation.log"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Consulta documentos fiscais a partir de um CSV de solicitações.",
    )
    parser.add_argument("--input", type=Path, default=Path("input/solicitacoes.csv"),
                        help="CSV de solicitações (padrão: %(default)s)")
    parser.add_argument("--output", type=Path, default=Path("output/resultado.csv"),
                        help="CSV consolidado de saída (padrão: %(default)s)")
    parser.add_argument("--log-file", type=Path, default=None,
                        help=f"arquivo de log (padrão: {LOG_FILE_NAME} na pasta do --output)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="exibe também logs informativos no console")
    return parser.parse_args(argv)


def run(input_path: Path, output_path: Path) -> Summary:
    settings = load_settings()
    logger.info("Configuração carregada: %r", settings)

    requests = read_requests(input_path)
    logger.info("%d solicitação(ões) lidas de %s", len(requests), input_path)

    with DocumentApiClient(settings) as client:
        results = process_requests(requests, client.query)

    write_results(output_path, results)
    logger.info("Resultado gravado em %s", output_path)
    return Summary.from_results(results)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    log_file = args.log_file or args.output.parent / LOG_FILE_NAME
    setup_logging(log_file, verbose=args.verbose)
    logger.info("=== Início da execução (input=%s, output=%s) ===", args.input, args.output)

    try:
        summary = run(args.input, args.output)
    except (ConfigError, InputFileError) as exc:
        logger.error("%s", exc)
        return EXIT_FAILURE
    except OSError as exc:
        logger.error("Falha de E/S: %s", exc)
        return EXIT_FAILURE
    except Exception:
        logger.exception("Erro inesperado; execução abortada")
        return EXIT_FAILURE

    logger.info("Resumo: %s", summary)
    print(summary.render())
    print(f"Resultado: {args.output}")
    print(f"Log: {log_file}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
