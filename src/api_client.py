import re
import time
from typing import TypedDict

import requests


class QueryResult(TypedDict):
    status: str
    http_status: int | None
    attempts: int
    message: str
    document_count: int | None


def _error_message(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"

    if isinstance(body, dict):
        for field in ("detail", "message"):
            message = body.get(field)
            if isinstance(message, str) and message.strip():
                return message.strip()

    return f"HTTP {response.status_code}"


def query_documents(
    request: dict[str, str],
    base_url: str,
    token: str,
    timeout: float,
    max_attempts: int = 3,
) -> QueryResult:
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("max_attempts deve ser um inteiro positivo")

    url = f"{base_url.rstrip('/')}/v1/documents/query"
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "request_id": request["request_id"].strip(),
        "cnpj": re.sub(r"[./-]", "", request["cnpj"].strip()),
        "uf": request["uf"].strip(),
        "document_type": request["document_type"].strip(),
        "competence": request["competence"].strip(),
    }

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "http_status": None,
                "attempts": attempt,
                "message": "Tempo limite da API excedido",
                "document_count": None,
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "http_status": None,
                "attempts": attempt,
                "message": "Falha de conexão com a API",
                "document_count": None,
            }
        except requests.exceptions.RequestException:
            return {
                "status": "error",
                "http_status": None,
                "attempts": attempt,
                "message": "Falha na requisição à API",
                "document_count": None,
            }

        http_status = response.status_code
        if http_status == 429 or 500 <= http_status <= 599:
            if attempt < max_attempts:
                time.sleep(min(0.2 * 2 ** (attempt - 1), 2.0))
                continue

        if http_status == 404:
            return {
                "status": "not_found",
                "http_status": http_status,
                "attempts": attempt,
                "message": _error_message(response),
                "document_count": None,
            }

        if not 200 <= http_status <= 299:
            return {
                "status": "error",
                "http_status": http_status,
                "attempts": attempt,
                "message": _error_message(response),
                "document_count": None,
            }

        try:
            body = response.json()
        except ValueError:
            return {
                "status": "error",
                "http_status": http_status,
                "attempts": attempt,
                "message": "JSON inválido na resposta da API",
                "document_count": None,
            }

        if (
            not isinstance(body, dict)
            or body.get("request_id") != payload["request_id"]
            or body.get("status") != "success"
            or not isinstance(body.get("document_count"), int)
            or isinstance(body["document_count"], bool)
            or body["document_count"] < 0
            or not isinstance(body.get("message"), str)
        ):
            return {
                "status": "error",
                "http_status": http_status,
                "attempts": attempt,
                "message": "Resposta inesperada da API",
                "document_count": None,
            }

        return {
            "status": "success",
            "http_status": http_status,
            "attempts": attempt,
            "message": body["message"],
            "document_count": body["document_count"],
        }

    raise RuntimeError("Nenhuma tentativa de consulta foi realizada")
