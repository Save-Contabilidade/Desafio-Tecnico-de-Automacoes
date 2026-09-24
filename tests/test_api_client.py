from __future__ import annotations

import json
from typing import Any

import pytest
import requests

from src.api_client import DocumentApiClient
from src.models import ResultStatus


def make_response(status: int, body: Any = None, *, raw: str | None = None,
                  headers: dict[str, str] | None = None) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = (raw if raw is not None else json.dumps(body)).encode()
    response.headers.update(headers or {})
    return response


class FakeSession:
    """Substitui ``requests.Session`` devolvendo respostas (ou exceções) pré-definidas."""

    def __init__(self, *outcomes: requests.Response | Exception) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        self.calls.append({"url": url, **kwargs})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self) -> None:
        pass


def success(request_id: str = "REQ-001", count: int = 2) -> requests.Response:
    return make_response(200, {"request_id": request_id, "status": "success",
                               "document_count": count, "message": "Consulta concluida"})


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def client_for(settings, sleeps):
    def factory(*outcomes):
        session = FakeSession(*outcomes)
        return DocumentApiClient(settings, session=session, sleep=sleeps.append), session

    return factory


def test_sucesso_envia_payload_token_e_timeout(client_for, make_request):
    client, session = client_for(success())
    result = client.query(make_request())

    assert result.status is ResultStatus.SUCCESS
    assert (result.http_status, result.attempts, result.document_count) == (200, 1, 2)
    call = session.calls[0]
    assert call["url"] == "http://api.test/v1/documents/query"
    assert call["headers"] == {"Authorization": "Bearer token-de-teste"}
    assert call["timeout"] == 5
    assert call["json"] == {"request_id": "REQ-001", "cnpj": "11111111000111", "uf": "SC",
                            "document_type": "NFE", "competence": "2026-08"}


def test_404_vira_not_found_sem_retentativa(client_for, make_request, sleeps):
    client, session = client_for(make_response(404, {"detail": "Nenhum documento encontrado"}))
    result = client.query(make_request())

    assert result.status is ResultStatus.NOT_FOUND
    assert (result.http_status, result.attempts) == (404, 1)
    assert result.message == "Nenhum documento encontrado"
    assert len(session.calls) == 1 and sleeps == []


@pytest.mark.parametrize("status", [400, 401, 403, 422])
def test_4xx_definitivo_nao_repete(client_for, make_request, sleeps, status):
    client, session = client_for(make_response(status, {"detail": "falha"}))
    result = client.query(make_request())

    assert result.status is ResultStatus.ERROR
    assert (result.http_status, result.attempts) == (status, 1)
    assert len(session.calls) == 1 and sleeps == []


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_erro_temporario_recupera_na_segunda_tentativa(client_for, make_request, sleeps, status):
    client, session = client_for(make_response(status, {"detail": "tente depois"}), success())
    result = client.query(make_request())

    assert result.status is ResultStatus.SUCCESS
    assert result.attempts == 2
    assert sleeps == [0.5]


def test_para_apos_tres_tentativas_com_backoff_exponencial(client_for, make_request, sleeps):
    client, session = client_for(*(make_response(503, {"detail": "indisponivel"}) for _ in range(5)))
    result = client.query(make_request())

    assert result.status is ResultStatus.ERROR
    assert (result.http_status, result.attempts) == (503, 3)
    assert len(session.calls) == 3
    assert sleeps == [0.5, 1.0]  # não espera depois da última tentativa
    assert "3 tentativa" in result.message


def test_retry_after_e_respeitado(client_for, make_request, sleeps):
    client, _ = client_for(make_response(429, {"detail": "x"}, headers={"Retry-After": "4"}), success())
    client.query(make_request())
    assert sleeps == [4.0]


def test_timeout_e_repetido_e_reportado(client_for, make_request, sleeps):
    client, session = client_for(*(requests.Timeout("lento") for _ in range(3)))
    result = client.query(make_request())

    assert result.status is ResultStatus.ERROR
    assert result.http_status is None
    assert result.attempts == 3
    assert "Timeout" in result.message


def test_falha_de_conexao_seguida_de_sucesso(client_for, make_request):
    client, _ = client_for(requests.ConnectionError("recusada"), success())
    result = client.query(make_request())
    assert (result.status, result.attempts) == (ResultStatus.SUCCESS, 2)


@pytest.mark.parametrize(
    "response",
    [
        make_response(200, raw="<html>não é json</html>"),
        make_response(200, [1, 2, 3]),
        make_response(200, {"request_id": "REQ-001", "status": "success"}),
        make_response(200, {"request_id": "REQ-001", "status": "success", "document_count": "2"}),
        make_response(200, {"request_id": "REQ-001", "status": "success", "document_count": -1}),
        make_response(200, {"request_id": "REQ-001", "status": "success", "document_count": True}),
        make_response(200, {"request_id": "REQ-001", "status": "failed", "document_count": 1}),
        make_response(200, {"request_id": "REQ-999", "status": "success", "document_count": 1}),
    ],
    ids=["nao-json", "lista", "sem-count", "count-texto", "count-negativo", "count-bool",
         "status-errado", "id-divergente"],
)
def test_resposta_inesperada_vira_erro_sem_retentativa(client_for, make_request, sleeps, response):
    client, session = client_for(response)
    result = client.query(make_request())

    assert result.status is ResultStatus.ERROR
    assert result.http_status == 200
    assert result.attempts == 1
    assert result.message.startswith("Resposta inválida da API")
    assert len(session.calls) == 1 and sleeps == []


def test_resposta_de_erro_sem_json(client_for, make_request):
    client, _ = client_for(make_response(400, raw="Bad Request puro"))
    result = client.query(make_request())
    assert result.message == "HTTP 400: Bad Request puro"


def test_respeita_max_attempts_configurado(settings, make_request, sleeps):
    from dataclasses import replace

    session = FakeSession(make_response(500, {}), make_response(500, {}))
    client = DocumentApiClient(replace(settings, max_attempts=1), session=session, sleep=sleeps.append)
    result = client.query(make_request())
    assert (result.status, result.attempts, len(session.calls)) == (ResultStatus.ERROR, 1, 1)
