import re


VALID_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

VALID_DOCUMENT_TYPES = {"NFE", "NFCE", "NFSE", "CTE", "MDFE"}


def validate_request(request: dict[str, str]) -> list[str]:
    errors = []

    request_id = (request.get("request_id") or "").strip()
    cnpj = (request.get("cnpj") or "").strip()
    uf = (request.get("uf") or "").strip()
    document_type = (request.get("document_type") or "").strip()
    competence = (request.get("competence") or "").strip()

    if not request_id:
        errors.append("request_id não pode estar vazio")

    normalized_cnpj = re.sub(r"[./-]", "", cnpj)

    if len(normalized_cnpj) != 14 or not normalized_cnpj.isdigit():
        errors.append("CNPJ deve conter 14 dígitos")

    if uf not in VALID_UFS:
        errors.append(f"UF inválida: {uf}")

    if document_type not in VALID_DOCUMENT_TYPES:
        errors.append(f"Tipo de documento inválido: {document_type}")

    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", competence):
        errors.append("Competência deve estar no formato YYYY-MM")

    return errors
