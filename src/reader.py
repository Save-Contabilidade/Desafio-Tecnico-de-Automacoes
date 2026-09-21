import csv
from pathlib import Path


REQUIRED_COLUMNS = {
    "request_id",
    "company_name",
    "cnpj",
    "uf",
    "document_type",
    "competence",
}


class InputFileError(Exception):
    """Erro ao acessar ou ler o CSV de entrada."""


def read_requests(file_path: str | Path) -> list[dict[str, str]]:
    path = Path(file_path)

    try:
        if not path.is_file():
            if not path.exists():
                raise InputFileError(f"Arquivo de entrada não encontrado: {path}")
            raise InputFileError(f"Caminho de entrada não é um arquivo: {path}")

        with path.open(mode="r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file, strict=True)
            header = reader.fieldnames
            if not header or not any(column.strip() for column in header):
                raise InputFileError(f"CSV de entrada sem cabeçalho: {path}")

            missing = REQUIRED_COLUMNS.difference(header)
            if missing:
                raise InputFileError(
                    f"CSV de entrada sem colunas obrigatórias: {', '.join(sorted(missing))}"
                )

            return list(reader)
    except UnicodeDecodeError as exc:
        raise InputFileError(f"CSV de entrada não está codificado em UTF-8: {path}") from exc
    except csv.Error as exc:
        raise InputFileError(f"CSV de entrada inválido: {path}: {exc}") from exc
    except OSError as exc:
        raise InputFileError(f"Não foi possível acessar o arquivo de entrada: {path}: {exc}") from exc
