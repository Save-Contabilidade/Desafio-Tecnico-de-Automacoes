import pytest

from src.reader import InputFileError, read_requests


HEADER = "request_id,company_name,cnpj,uf,document_type,competence"
ROW = "REQ-001,Empresa Alpha,11.111.111/0001-11,SC,NFE,2026-08"


def test_valid_csv_accepts_extra_columns(tmp_path):
    csv_path = tmp_path / "requests.csv"
    csv_path.write_text(
        f"{HEADER},extra\n{ROW},valor extra\n",
        encoding="utf-8",
    )

    assert read_requests(csv_path) == [
        {
            "request_id": "REQ-001",
            "company_name": "Empresa Alpha",
            "cnpj": "11.111.111/0001-11",
            "uf": "SC",
            "document_type": "NFE",
            "competence": "2026-08",
            "extra": "valor extra",
        }
    ]


def test_missing_file_raises_input_file_error(tmp_path):
    with pytest.raises(InputFileError, match="Arquivo de entrada não encontrado"):
        read_requests(tmp_path / "missing.csv")


def test_csv_without_header_raises_input_file_error(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")

    with pytest.raises(InputFileError, match="sem cabeçalho"):
        read_requests(csv_path)


def test_csv_missing_required_column_raises_input_file_error(tmp_path):
    csv_path = tmp_path / "missing-column.csv"
    csv_path.write_text(
        "request_id,cnpj,uf,document_type,competence\n"
        "REQ-001,11.111.111/0001-11,SC,NFE,2026-08\n",
        encoding="utf-8",
    )

    with pytest.raises(InputFileError, match="colunas obrigatórias: company_name"):
        read_requests(csv_path)


def test_utf8_csv_with_bom_is_accepted(tmp_path):
    csv_path = tmp_path / "bom.csv"
    csv_path.write_text(f"\ufeff{HEADER}\n{ROW}\n", encoding="utf-8")

    result = read_requests(str(csv_path))

    assert len(result) == 1
    assert result[0]["request_id"] == "REQ-001"


def test_directory_is_not_accepted_as_input_file(tmp_path):
    with pytest.raises(InputFileError, match="não é um arquivo"):
        read_requests(tmp_path)


def test_invalid_utf8_raises_input_file_error(tmp_path):
    csv_path = tmp_path / "invalid-encoding.csv"
    csv_path.write_bytes(b"\xff" + HEADER.encode("utf-8"))

    with pytest.raises(InputFileError, match="UTF-8"):
        read_requests(csv_path)


def test_malformed_csv_raises_input_file_error(tmp_path):
    csv_path = tmp_path / "malformed.csv"
    csv_path.write_text(f"{HEADER}\nREQ-001,\"unterminated\n", encoding="utf-8")

    with pytest.raises(InputFileError, match="CSV de entrada inválido"):
        read_requests(csv_path)
