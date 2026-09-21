from src.validator import validate_request


def test_valid_request_returns_no_errors():
    request = {
        "request_id": "REQ-001",
        "cnpj": "11.111.111/0001-11",
        "uf": "SC",
        "document_type": "NFE",
        "competence": "2026-08",
    }

    errors = validate_request(request)

    assert errors == []


def test_invalid_request_returns_all_errors():
    request = {
        "request_id": "   ",
        "cnpj": "123",
        "uf": "XX",
        "document_type": "PDF",
        "competence": "2026-13",
    }

    errors = validate_request(request)

    assert (errors) == [
        "request_id não pode estar vazio",
        "CNPJ deve conter 14 dígitos",
        "UF inválida: XX",
        "Tipo de documento inválido: PDF",
        "Competência deve estar no formato YYYY-MM",
    ]

def test_unformatted_cnpj_with_valid_length_is_accepted():
    request = {
        "request_id": "REQ-TEST",
        "cnpj": "11111111000111",
        "uf": "SC",
        "document_type": "NFE",
        "competence": "2026-08",
    }

    errors = validate_request(request)

    assert errors == []
