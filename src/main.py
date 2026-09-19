import argparse

from src.reader import read_requests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)

    args = parser.parse_args()

    requests = read_requests(args.input)

    print(f"Solicitações carregadas: {len(requests)}")


if __name__ == "__main__":
    main()
