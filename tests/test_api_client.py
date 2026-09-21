from unittest.mock import Mock, call, patch

import pytest
import requests

from src.api_client import query_documents


REQUEST = {
    "request_id": " REQ-003 ",
    "cnpj": " 33.333.333/0001-33 ",
    "uf": " PR ",
    "document_type": " NFSE ",
    "competence": " 2026-08 ",
}
SUCCESS_BODY = {
    "request_id": "REQ-003",
    "status": "success",
    "document_count": 2,
    "message": "Consulta concluída",
}


def make_response(status_code: int, body: object) -> Mock:
    response = Mock(spec=requests.Response)
    response.status_code = status_code
    response.json.return_value = body
    return response


def query(max_attempts: int = 3) -> dict:
    return query_documents(
        REQUEST,
        base_url="http://localhost:8000/",
        token="test-token",
        timeout=4,
        max_attempts=max_attempts,
    )


@pytest.fixture
def mocked_http():
    with patch("src.api_client.requests.post") as post, patch(
        "src.api_client.time.sleep"
    ) as sleep:
        yield post, sleep


def test_success_on_first_attempt_sends_normalized_payload(mocked_http):
    post, sleep = mocked_http
    post.return_value = make_response(200, SUCCESS_BODY)

    result = query()

    assert result == {
        "status": "success",
        "http_status": 200,
        "attempts": 1,
        "message": "Consulta concluída",
        "document_count": 2,
    }
    post.assert_called_once_with(
        "http://localhost:8000/v1/documents/query",
        headers={"Authorization": "Bearer test-token"},
        json={
            "request_id": "REQ-003",
            "cnpj": "33333333000133",
            "uf": "PR",
            "document_type": "NFSE",
            "competence": "2026-08",
        },
        timeout=4,
    )
    sleep.assert_not_called()


def test_404_returns_not_found_without_retry(mocked_http):
    post, sleep = mocked_http
    post.return_value = make_response(404, {"detail": "Nenhum documento encontrado"})

    result = query()

    assert result == {
        "status": "not_found",
        "http_status": 404,
        "attempts": 1,
        "message": "Nenhum documento encontrado",
        "document_count": None,
    }
    post.assert_called_once()
    sleep.assert_not_called()


def test_401_returns_error_without_retry(mocked_http):
    post, sleep = mocked_http
    post.return_value = make_response(401, {"detail": "Token inválido"})

    result = query()

    assert result == {
        "status": "error",
        "http_status": 401,
        "attempts": 1,
        "message": "Token inválido",
        "document_count": None,
    }
    post.assert_called_once()
    sleep.assert_not_called()


def test_429_twice_then_success_uses_three_attempts(mocked_http):
    post, sleep = mocked_http
    post.side_effect = [
        make_response(429, {"detail": "Limite de requisições"}),
        make_response(429, {"detail": "Limite de requisições"}),
        make_response(200, SUCCESS_BODY),
    ]

    result = query()

    assert result["status"] == "success"
    assert result["http_status"] == 200
    assert result["attempts"] == 3
    assert result["document_count"] == 2
    assert post.call_count == 3
    assert sleep.call_args_list == [call(0.2), call(0.4)]


def test_500_then_success_uses_two_attempts(mocked_http):
    post, sleep = mocked_http
    post.side_effect = [
        make_response(500, {"detail": "Erro temporário"}),
        make_response(200, SUCCESS_BODY),
    ]

    result = query()

    assert result["status"] == "success"
    assert result["http_status"] == 200
    assert result["attempts"] == 2
    assert post.call_count == 2
    sleep.assert_called_once_with(0.2)


def test_5xx_stops_at_max_attempts(mocked_http):
    post, sleep = mocked_http
    post.side_effect = [
        make_response(500, {"detail": "Erro temporário"}),
        make_response(503, {"detail": "Serviço indisponível"}),
        make_response(599, {"detail": "Falha persistente"}),
    ]

    result = query(max_attempts=3)

    assert result == {
        "status": "error",
        "http_status": 599,
        "attempts": 3,
        "message": "Falha persistente",
        "document_count": None,
    }
    assert post.call_count == 3
    assert sleep.call_args_list == [call(0.2), call(0.4)]


def test_timeout_returns_controlled_error(mocked_http):
    post, sleep = mocked_http
    post.side_effect = requests.exceptions.Timeout("tempo esgotado")

    result = query()

    assert result == {
        "status": "error",
        "http_status": None,
        "attempts": 1,
        "message": "Tempo limite da API excedido",
        "document_count": None,
    }
    post.assert_called_once()
    sleep.assert_not_called()


def test_connection_error_returns_controlled_error(mocked_http):
    post, sleep = mocked_http
    post.side_effect = requests.exceptions.ConnectionError("sem conexão")

    result = query()

    assert result == {
        "status": "error",
        "http_status": None,
        "attempts": 1,
        "message": "Falha de conexão com a API",
        "document_count": None,
    }
    post.assert_called_once()
    sleep.assert_not_called()


def test_invalid_json_in_2xx_returns_error(mocked_http):
    post, sleep = mocked_http
    response = make_response(200, None)
    response.json.side_effect = ValueError("JSON inválido")
    post.return_value = response

    result = query()

    assert result == {
        "status": "error",
        "http_status": 200,
        "attempts": 1,
        "message": "JSON inválido na resposta da API",
        "document_count": None,
    }
    post.assert_called_once()
    sleep.assert_not_called()


def test_unexpected_2xx_body_returns_error(mocked_http):
    post, sleep = mocked_http
    post.return_value = make_response(200, {"status": "success", "document_count": 2})

    result = query()

    assert result == {
        "status": "error",
        "http_status": 200,
        "attempts": 1,
        "message": "Resposta inesperada da API",
        "document_count": None,
    }
    post.assert_called_once()
    sleep.assert_not_called()
