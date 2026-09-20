import argparse

from src.reader import read_requests
from src.validator import validate_request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)

    args = parser.parse_args()

    requests = read_requests(args.input)

    valid_requests = []
    invalid_requests = []

    for request in requests:
        errors = validate_request(request)

        if errors:
            invalid_requests.append((request, errors))
        else:
            valid_requests.append(request)

    print(f"Solicitações carregadas: {len(requests)}")
    print(f"Solicitações válidas: {len(valid_requests)}")
    print(f"Solicitações inválidas: {len(invalid_requests)}")


if __name__ == "__main__":
    main()
