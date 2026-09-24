from __future__ import annotations

from src.models import ApiResult, ResultStatus
from src.processor import Summary, process_requests


def fixed_clock() -> str:
    return "2026-08-01T10:00:00-03:00"


def test_invalidos_nao_chamam_api(make_request):
    calls = []

    def query(request):
        calls.append(request.request_id)
        return ApiResult(ResultStatus.SUCCESS, "ok", attempts=1, http_status=200, document_count=1)

    results = process_requests(
        [make_request(request_id="REQ-001"), make_request(request_id="REQ-002", uf="XX")],
        query,
        clock=fixed_clock,
    )

    assert calls == ["REQ-001"]
    invalid = results[1]
    assert invalid.status is ResultStatus.INVALID
    assert (invalid.attempts, invalid.http_status, invalid.document_count) == (0, None, None)
    assert "UF inexistente" in invalid.message


def test_envia_dados_normalizados_para_api(make_request):
    received = []

    def query(request):
        received.append(request)
        return ApiResult(ResultStatus.SUCCESS, "ok", attempts=1, http_status=200, document_count=1)

    process_requests([make_request(cnpj="11.111.111/0001-11", uf="sc")], query, clock=fixed_clock)
    assert (received[0].cnpj, received[0].uf) == ("11111111000111", "SC")


def test_request_id_duplicado_e_invalido(make_request):
    calls = []

    def query(request):
        calls.append(request.request_id)
        return ApiResult(ResultStatus.SUCCESS, "ok", attempts=1, http_status=200, document_count=1)

    results = process_requests([make_request(), make_request()], query, clock=fixed_clock)

    assert calls == ["REQ-001"]
    assert [r.status for r in results] == [ResultStatus.SUCCESS, ResultStatus.INVALID]
    assert "duplicado" in results[1].message


def test_excecao_inesperada_nao_interrompe_o_lote(make_request):
    def query(request):
        if request.request_id == "REQ-001":
            raise RuntimeError("bug")
        return ApiResult(ResultStatus.SUCCESS, "ok", attempts=1, http_status=200, document_count=3)

    results = process_requests(
        [make_request(request_id="REQ-001"), make_request(request_id="REQ-002")], query, clock=fixed_clock
    )

    assert [r.status for r in results] == [ResultStatus.ERROR, ResultStatus.SUCCESS]
    assert "bug" in results[0].message


def test_resumo(make_request):
    outcomes = {
        "REQ-001": ApiResult(ResultStatus.SUCCESS, "ok", 1, 200, 2),
        "REQ-002": ApiResult(ResultStatus.NOT_FOUND, "nada", 1, 404),
        "REQ-003": ApiResult(ResultStatus.ERROR, "falhou", 3, 503),
    }
    requests = [make_request(request_id=rid) for rid in outcomes] + [make_request(request_id="REQ-004", cnpj="1")]
    results = process_requests(requests, lambda r: outcomes[r.request_id], clock=fixed_clock)

    summary = Summary.from_results(results)
    assert summary == Summary(total=4, success=1, not_found=1, invalid=1, error=1)
    assert summary.render().splitlines() == [
        "Processamento concluído", "Total: 4", "Sucesso: 1", "Não encontrados: 1", "Inválidos: 1", "Erros: 1",
    ]


def test_duplicado_apos_registro_invalido_e_detectado(make_request):
    # O primeiro REQ-001 é inválido (UF), mas o id já apareceu: o segundo é duplicata.
    calls = []

    def query(request):
        calls.append(request.request_id)
        return ApiResult(ResultStatus.SUCCESS, "ok", attempts=1, http_status=200, document_count=1)

    results = process_requests([make_request(uf="XX"), make_request()], query, clock=fixed_clock)

    assert calls == []
    assert [r.status for r in results] == [ResultStatus.INVALID, ResultStatus.INVALID]
    assert "duplicado" in results[1].message
