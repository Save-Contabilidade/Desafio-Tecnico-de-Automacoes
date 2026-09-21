import csv
from pathlib import Path


FIELDNAMES = (
    "request_id",
    "status",
    "http_status",
    "attempts",
    "message",
    "document_count",
    "processed_at",
)


def write_results(
    output_path: str | Path,
    results: list[dict[str, object]],
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(mode="w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(
            {
                field: "" if result.get(field) is None else result.get(field, "")
                for field in FIELDNAMES
            }
            for result in results
        )
