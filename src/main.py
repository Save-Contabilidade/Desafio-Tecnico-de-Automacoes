import argparse
import sys
from collections import Counter
from pathlib import Path

from src.config import load_config
from src.logger import setup_logger
from src.processor import process_requests
from src.reader import InputFileError, read_requests
from src.writer import write_results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    log_path = Path(args.output).parent / "automation.log"
    logger = setup_logger(log_path)
    logger.info("Início do processamento")

    config = load_config()
    try:
        requests = read_requests(args.input)
    except InputFileError as exc:
        logger.error("Erro de entrada: %s", exc)
        print(f"Erro de entrada: {exc}", file=sys.stderr)
        raise SystemExit(1) from None

    results = process_requests(requests, config)
    write_results(args.output, results)

    for result in results:
        logger.info(
            "request_id=%s status=%s http_status=%s attempts=%s message=%s",
            result["request_id"],
            result["status"],
            result["http_status"],
            result["attempts"],
            result["message"],
        )

    status_counts = Counter(result["status"] for result in results)
    logger.info(
        "Resumo: total=%s success=%s not_found=%s invalid=%s error=%s",
        len(results),
        status_counts["success"],
        status_counts["not_found"],
        status_counts["invalid"],
        status_counts["error"],
    )

    print("Processamento concluído")
    print(f"Total processado: {len(results)}")
    print(f"success: {status_counts['success']}")
    print(f"not_found: {status_counts['not_found']}")
    print(f"invalid: {status_counts['invalid']}")
    print(f"error: {status_counts['error']}")


if __name__ == "__main__":
    main()
