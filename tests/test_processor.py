"""Testes da orquestração: validação, duplicidade e resumo."""

from __future__ import annotations

from datetime import datetime, timezone

from src.models import DocumentRequest, QueryOutcome, ResultStatus, Summary
from src.processor import RequestProcessor

MOMENTO_FIXO = datetime(2026, 9, 22, 10, 30, tzinfo=timezone.utc)


class ClientSpy:
    """Cliente falso que registra as solicitações consultadas."""

    def __init__(self, outcome: QueryOutcome | None = None) -> None:
        self.consultas: list[DocumentRequest] = []
        self._outcome = outcome or QueryOutcome(
            status=ResultStatus.SUCCESS,
            message="Consulta concluida",
            attempts=1,
            http_status=200,
            document_count=2,
        )

    def query(self, request: DocumentRequest) -> QueryOutcome:
        self.consultas.append(request)
        return self._outcome


def build_request(request_id: str = "REQ-001", **overrides: str) -> DocumentRequest:
    campos: dict[str, str] = {
        "request_id": request_id,
        "company_name": "Empresa Alpha",
        "cnpj": "11.111.111/0001-11",
        "uf": "SC",
        "document_type": "NFE",
        "competence": "2026-08",
    }
    campos.update(overrides)
    return DocumentRequest(**campos)


def build_processor(client: ClientSpy) -> RequestProcessor:
    return RequestProcessor(client, clock=lambda: MOMENTO_FIXO)  # type: ignore[arg-type]


def test_registro_invalido_nao_chama_a_api() -> None:
    client = ClientSpy()
    processor = build_processor(client)

    resultados = processor.process_all([build_request(uf="XX")])

    assert client.consultas == []
    assert resultados[0].status is ResultStatus.INVALID
    assert resultados[0].attempts == 0
    assert resultados[0].http_status is None


def test_api_recebe_a_solicitacao_normalizada() -> None:
    client = ClientSpy()
    processor = build_processor(client)

    processor.process_all([build_request(uf="sc", document_type="nfe")])

    consultada = client.consultas[0]
    assert consultada.cnpj == "11111111000111"
    assert consultada.uf == "SC"
    assert consultada.document_type == "NFE"


def test_request_id_duplicado_e_consultado_uma_unica_vez() -> None:
    client = ClientSpy()
    processor = build_processor(client)

    resultados = processor.process_all([build_request(), build_request()])

    assert len(client.consultas) == 1
    assert resultados[0].status is ResultStatus.SUCCESS
    assert resultados[1].status is ResultStatus.INVALID
    assert "duplicado" in resultados[1].message


def test_resultados_mantem_a_ordem_da_entrada() -> None:
    processor = build_processor(ClientSpy())

    resultados = processor.process_all(
        [build_request("REQ-001"), build_request("REQ-002"), build_request("REQ-003")]
    )

    assert [r.request_id for r in resultados] == ["REQ-001", "REQ-002", "REQ-003"]


def test_resumo_conta_cada_status() -> None:
    client = ClientSpy()
    processor = build_processor(client)

    resultados = processor.process_all(
        [build_request("REQ-001"), build_request("REQ-002"), build_request("REQ-003", uf="XX")]
    )
    resumo = Summary.from_results(resultados)

    assert resumo.total == 3
    assert resumo.success == 2
    assert resumo.invalid == 1
    assert resumo.errors == 0
    assert resumo.documents == 4
