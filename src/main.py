import argparse
from collections import Counter

from src.config import load_config
from src.processor import process_requests
from src.reader import read_requests
from src.writer import write_results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    config = load_config()
    requests = read_requests(args.input)
    results = process_requests(requests, config)
    write_results(args.output, results)

    status_counts = Counter(result["status"] for result in results)

    print("Processamento concluído")
    print(f"Total processado: {len(results)}")
    print(f"success: {status_counts['success']}")
    print(f"not_found: {status_counts['not_found']}")
    print(f"invalid: {status_counts['invalid']}")
    print(f"error: {status_counts['error']}")


if __name__ == "__main__":
    main()
