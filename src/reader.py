import csv


def read_requests(file_path: str) -> list[dict[str, str]]:
    with open(file_path, mode="r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)
