"""Testes do arquivo de saída e da execução completa pela linha de comando."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src import main as main_module
from src.models import DocumentRequest, ProcessingResult, QueryOutcome, ResultStatus
from src.writer import CSV_COLUMNS, write_results

CSV_ENTRADA = (
    "request_id,company_name,cnpj,uf,document_type,competence\n"
    "REQ-001,Empresa Alpha,11.111.111/0001-11,SC,NFE,2026-08\n"
    "REQ-002,Empresa Beta,22.222.222/0001-22,SP,NFCE,2026-08\n"
    "REQ-005,Empresa Epsilon,55.555.555/0001-55,XX,NFE,2026-08\n"
)


class FakeClient:
    """Responde sucesso para REQ-001 e 404 para os demais."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.consultas: list[str] = []

    def query(self, request: DocumentRequest) -> QueryOutcome:
        self.consultas.append(request.request_id)
        if request.request_id == "REQ-001":
            return QueryOutcome(
                status=ResultStatus.SUCCESS,
                message="Consulta concluida",
                attempts=1,
                http_status=200,
                document_count=2,
            )
        return QueryOutcome(
            status=ResultStatus.NOT_FOUND,
            message="Nenhum documento encontrado",
            attempts=1,
            http_status=404,
        )


@pytest.fixture
def ambiente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("API_TOKEN", "token-de-teste")
    monkeypatch.setenv("API_BASE_URL", "http://api.local")
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "automation.log"))
    monkeypatch.setattr(main_module, "DocumentApiClient", FakeClient)
    return tmp_path


def test_write_results_gera_colunas_esperadas(tmp_path: Path) -> None:
    resultado = ProcessingResult(
        request_id="REQ-001",
        status=ResultStatus.SUCCESS,
        message="Consulta concluida",
        processed_at=datetime(2026, 9, 22, 10, 30, tzinfo=timezone.utc),
        attempts=1,
        http_status=200,
        document_count=2,
    )
    saida = tmp_path / "sub" / "resultado.csv"

    write_results(saida, [resultado])

    linhas = list(csv.DictReader(saida.open(encoding="utf-8")))
    assert list(linhas[0].keys()) == list(CSV_COLUMNS)
    assert linhas[0]["status"] == "success"
    assert linhas[0]["document_count"] == "2"


def test_write_results_deixa_campos_vazios_quando_nao_se_aplicam(tmp_path: Path) -> None:
    resultado = ProcessingResult(
        request_id="REQ-005",
        status=ResultStatus.INVALID,
        message="UF inexistente: 'XX'",
        processed_at=datetime(2026, 9, 22, 10, 30, tzinfo=timezone.utc),
    )
    saida = tmp_path / "resultado.csv"

    write_results(saida, [resultado])

    linha = list(csv.DictReader(saida.open(encoding="utf-8")))[0]
    assert linha["http_status"] == ""
    assert linha["document_count"] == ""
    assert linha["attempts"] == "0"


def test_execucao_completa_gera_saida_e_log(ambiente: Path, capsys: pytest.CaptureFixture) -> None:
    entrada = ambiente / "solicitacoes.csv"
    entrada.write_text(CSV_ENTRADA, encoding="utf-8")
    saida = ambiente / "output" / "resultado.csv"

    codigo = main_module.run(["--input", str(entrada), "--output", str(saida)])

    assert codigo == 0
    linhas = list(csv.DictReader(saida.open(encoding="utf-8")))
    assert [linha["status"] for linha in linhas] == ["success", "not_found", "invalid"]
    assert (ambiente / "automation.log").exists()

    resumo = capsys.readouterr().out
    assert "Total: 3" in resumo
    assert "Sucesso: 1" in resumo


def test_execucao_repetida_produz_o_mesmo_arquivo(ambiente: Path) -> None:
    entrada = ambiente / "solicitacoes.csv"
    entrada.write_text(CSV_ENTRADA, encoding="utf-8")
    saida = ambiente / "resultado.csv"
    argumentos = ["--input", str(entrada), "--output", str(saida)]

    main_module.run(argumentos)
    primeira = _linhas_sem_data(saida)
    main_module.run(argumentos)
    segunda = _linhas_sem_data(saida)

    assert primeira == segunda


def test_entrada_inexistente_retorna_codigo_de_erro(ambiente: Path) -> None:
    codigo = main_module.run(
        ["--input", str(ambiente / "nao_existe.csv"), "--output", str(ambiente / "saida.csv")]
    )

    assert codigo == main_module.EXIT_CONFIG_ERROR


def test_sem_api_token_retorna_codigo_de_erro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.delenv("API_TOKEN", raising=False)
    vazio = tmp_path / ".env"
    vazio.write_text("", encoding="utf-8")

    codigo = main_module.run(
        [
            "--input",
            str(tmp_path / "entrada.csv"),
            "--output",
            str(tmp_path / "saida.csv"),
            "--env-file",
            str(vazio),
        ]
    )

    assert codigo == main_module.EXIT_CONFIG_ERROR
    assert "API_TOKEN" in capsys.readouterr().err


def _linhas_sem_data(caminho: Path) -> list[dict[str, str]]:
    linhas = list(csv.DictReader(caminho.open(encoding="utf-8")))
    for linha in linhas:
        linha.pop("processed_at", None)
    return linhas
