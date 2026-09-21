from __future__ import annotations

import csv

import pytest

from src.models import ProcessingResult, ResultStatus
from src.reader import InputFileError, read_requests
from src.writer import OUTPUT_COLUMNS, write_results

HEADER = "request_id,company_name,cnpj,uf,document_type,competence\n"


def test_le_csv_removendo_espacos_bom_e_linhas_vazias(tmp_path):
    path = tmp_path / "entrada.csv"
    path.write_text(
        "﻿" + HEADER + " REQ-1 , Empresa ,11.111.111/0001-11, SC ,NFE,2026-08\n,,,,,\n",
        encoding="utf-8",
    )
    requests = read_requests(path)

    assert len(requests) == 1
    assert requests[0].request_id == "REQ-1"
    assert requests[0].uf == "SC"
    assert requests[0].cnpj == "11.111.111/0001-11"  # normalização fica no validador


def test_linha_com_colunas_faltando_e_sinalizada(tmp_path):
    path = tmp_path / "entrada.csv"
    path.write_text(HEADER + "REQ-1,Empresa\n", encoding="utf-8")
    request = read_requests(path)[0]
    assert request.competence == ""
    assert request.format_error == "linha com 2 colunas, esperado 6"


def test_virgula_sem_aspas_e_sinalizada(tmp_path):
    path = tmp_path / "entrada.csv"
    path.write_text(HEADER + "REQ-1,Empresa, Filial,11111111000111,SP,NFE,2026-08\n", encoding="utf-8")
    assert read_requests(path)[0].format_error.startswith("linha com 7 colunas, esperado 6")


def test_virgula_entre_aspas_e_aceita(tmp_path):
    path = tmp_path / "entrada.csv"
    path.write_text(HEADER + 'REQ-1,"Empresa, Filial",11111111000111,SP,NFE,2026-08\n', encoding="utf-8")
    request = read_requests(path)[0]
    assert (request.company_name, request.format_error) == ("Empresa, Filial", "")


def test_guarda_numero_da_linha(tmp_path):
    path = tmp_path / "entrada.csv"
    path.write_text(HEADER + "\nREQ-1,A,1,SP,NFE,2026-08\nREQ-2,B,1,SP,NFE,2026-08\n", encoding="utf-8")
    assert [r.line_number for r in read_requests(path)] == [3, 4]


def test_arquivo_inexistente(tmp_path):
    with pytest.raises(InputFileError, match="não encontrado"):
        read_requests(tmp_path / "nao_existe.csv")


def test_colunas_obrigatorias_ausentes(tmp_path):
    path = tmp_path / "entrada.csv"
    path.write_text("request_id,cnpj\nREQ-1,1\n", encoding="utf-8")
    with pytest.raises(InputFileError, match="company_name"):
        read_requests(path)


def test_escreve_csv_com_colunas_obrigatorias(tmp_path):
    path = tmp_path / "sub" / "resultado.csv"
    results = [
        ProcessingResult("REQ-1", ResultStatus.SUCCESS, 200, 2, "ok", 3, "2026-08-01T10:00:00"),
        ProcessingResult("REQ-2", ResultStatus.INVALID, None, 0, "UF inexistente: XX", None, "2026-08-01T10:00:00"),
    ]
    write_results(path, results)
    write_results(path, results)  # reexecução sobrescreve em vez de duplicar

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert tuple(rows[0].keys()) == OUTPUT_COLUMNS
    assert len(rows) == 2
    assert rows[0]["status"] == "success" and rows[0]["document_count"] == "3"
    assert rows[1]["http_status"] == "" and rows[1]["attempts"] == "0"
    assert list(path.parent.glob("*.tmp")) == []
