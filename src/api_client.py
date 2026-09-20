import re

import requests


def query_documents(
    request: dict[str, str],
    base_url: str,
    token: str,
    timeout: float,
) -> requests.Response:
    url = f"{base_url}/v1/documents/query"

    headers = {
        "Authorization": f"Bearer {token}",
    }

    payload = {
        "request_id": request["request_id"],
        "cnpj": re.sub(r"[./-]", "", request["cnpj"]),
        "uf": request["uf"],
        "document_type": request["document_type"],
        "competence": request["competence"],
    }

    return requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
    )
