"""Testes do cliente da API, com foco em retentativas e tratamento de erros."""

from __future__ import annotations

import requests

from src.api_client import DocumentApiClient
from src.config import Settings
from src.models import DocumentRequest, ResultStatus
from tests.fakes import FakeResponse, FakeSession, SleepSpy, success_payload

SOLICITACAO = DocumentRequest(
    request_id="REQ-001",
    company_name="Empresa Alpha",
    cnpj="11111111000111",
    uf="SC",
    document_type="NFE",
    competence="2026-08",
)


def build_client(settings: Settings, respostas: list, sleep: SleepSpy) -> tuple:
    session = FakeSession(respostas)
    return DocumentApiClient(settings, session=session, sleep=sleep), session


def test_sucesso_na_primeira_tentativa(settings: Settings, sleep_spy: SleepSpy) -> None:
    client, session = build_client(settings, [FakeResponse(200, success_payload())], sleep_spy)

    resultado = client.query(SOLICITACAO)

    assert resultado.status is ResultStatus.SUCCESS
    assert resultado.attempts == 1
    assert resultado.document_count == 2
    assert resultado.http_status == 200
    assert sleep_spy.delays == []
    assert session.calls[0]["headers"]["Authorization"] == "Bearer token-de-teste"
    assert session.calls[0]["timeout"] == settings.request_timeout


def test_envia_payload_esperado_pela_api(settings: Settings, sleep_spy: SleepSpy) -> None:
    client, session = build_client(settings, [FakeResponse(200, success_payload())], sleep_spy)

    client.query(SOLICITACAO)

    assert session.calls[0]["json"] == {
        "request_id": "REQ-001",
        "cnpj": "11111111000111",
        "uf": "SC",
        "document_type": "NFE",
        "competence": "2026-08",
    }
    assert session.calls[0]["url"] == "http://api.local/v1/documents/query"


def test_429_seguido_de_sucesso_usa_tres_tentativas(
    settings: Settings, sleep_spy: SleepSpy
) -> None:
    respostas = [
        FakeResponse(429, {"detail": "Limite temporario de requisicoes"}),
        FakeResponse(429, {"detail": "Limite temporario de requisicoes"}),
        FakeResponse(200, success_payload(document_count=1)),
    ]
    client, _ = build_client(settings, respostas, sleep_spy)

    resultado = client.query(SOLICITACAO)

    assert resultado.status is ResultStatus.SUCCESS
    assert resultado.attempts == 3
    assert len(sleep_spy.delays) == 2


def test_erro_500_persistente_para_no_limite_de_tentativas(
    settings: Settings, sleep_spy: SleepSpy
) -> None:
    respostas = [FakeResponse(500, {"detail": "Erro temporario do servidor"}) for _ in range(3)]
    client, session = build_client(settings, respostas, sleep_spy)

    resultado = client.query(SOLICITACAO)

    assert resultado.status is ResultStatus.ERROR
    assert resultado.attempts == settings.max_attempts
    assert len(session.calls) == settings.max_attempts
    assert "500" in resultado.message


def test_404_vira_not_found_sem_retentativa(settings: Settings, sleep_spy: SleepSpy) -> None:
    respostas = [FakeResponse(404, {"detail": "Nenhum documento encontrado"})]
    client, session = build_client(settings, respostas, sleep_spy)

    resultado = client.query(SOLICITACAO)

    assert resultado.status is ResultStatus.NOT_FOUND
    assert resultado.attempts == 1
    assert len(session.calls) == 1
    assert sleep_spy.delays == []


def test_401_nao_gera_retentativa(settings: Settings, sleep_spy: SleepSpy) -> None:
    client, session = build_client(settings, [FakeResponse(401, {"detail": "Token invalido"})], sleep_spy)

    resultado = client.query(SOLICITACAO)

    assert resultado.status is ResultStatus.ERROR
    assert resultado.http_status == 401
    assert len(session.calls) == 1


def test_400_nao_gera_retentativa(settings: Settings, sleep_spy: SleepSpy) -> None:
    client, session = build_client(settings, [FakeResponse(400, {"detail": "Payload invalido"})], sleep_spy)

    resultado = client.query(SOLICITACAO)

    assert resultado.status is ResultStatus.ERROR
    assert len(session.calls) == 1


def test_timeout_e_tratado_como_erro_temporario(settings: Settings, sleep_spy: SleepSpy) -> None:
    respostas = [
        requests.Timeout("tempo esgotado"),
        FakeResponse(200, success_payload()),
    ]
    client, _ = build_client(settings, respostas, sleep_spy)

    resultado = client.query(SOLICITACAO)

    assert resultado.status is ResultStatus.SUCCESS
    assert resultado.attempts == 2
    assert len(sleep_spy.delays) == 1


def test_falha_de_conexao_esgota_as_tentativas(settings: Settings, sleep_spy: SleepSpy) -> None:
    respostas = [requests.ConnectionError("API indisponível") for _ in range(3)]
    client, _ = build_client(settings, respostas, sleep_spy)

    resultado = client.query(SOLICITACAO)

    assert resultado.status is ResultStatus.ERROR
    assert resultado.attempts == 3
    assert resultado.http_status is None
    assert "conexão" in resultado.message


def test_json_invalido_vira_erro_sem_retentativa(settings: Settings, sleep_spy: SleepSpy) -> None:
    client, session = build_client(settings, [FakeResponse(200, None, text="<html>")], sleep_spy)

    resultado = client.query(SOLICITACAO)

    assert resultado.status is ResultStatus.ERROR
    assert len(session.calls) == 1
    assert "JSON" in resultado.message


def test_resposta_com_status_inesperado(settings: Settings, sleep_spy: SleepSpy) -> None:
    payload = {"request_id": "REQ-001", "status": "processando"}
    client, _ = build_client(settings, [FakeResponse(200, payload)], sleep_spy)

    resultado = client.query(SOLICITACAO)

    assert resultado.status is ResultStatus.ERROR
    assert "inesperada" in resultado.message


def test_sucesso_sem_document_count_vira_erro(settings: Settings, sleep_spy: SleepSpy) -> None:
    payload = {"request_id": "REQ-001", "status": "success"}
    client, _ = build_client(settings, [FakeResponse(200, payload)], sleep_spy)

    resultado = client.query(SOLICITACAO)

    assert resultado.status is ResultStatus.ERROR
    assert "document_count" in resultado.message


def test_backoff_exponencial_entre_as_tentativas(settings: Settings, sleep_spy: SleepSpy) -> None:
    settings_com_backoff = Settings(
        api_base_url=settings.api_base_url,
        api_token=settings.api_token,
        request_timeout=settings.request_timeout,
        max_attempts=3,
        retry_backoff_seconds=0.5,
        log_file=settings.log_file,
    )
    respostas = [FakeResponse(500, {"detail": "erro"}) for _ in range(3)]
    client, _ = build_client(settings_com_backoff, respostas, sleep_spy)

    client.query(SOLICITACAO)

    assert sleep_spy.delays == [0.5, 1.0]


def test_respeita_header_retry_after(settings: Settings, sleep_spy: SleepSpy) -> None:
    respostas = [
        FakeResponse(429, {"detail": "limite"}, headers={"Retry-After": "2"}),
        FakeResponse(200, success_payload()),
    ]
    client, _ = build_client(settings, respostas, sleep_spy)

    client.query(SOLICITACAO)

    assert sleep_spy.delays == [2.0]
