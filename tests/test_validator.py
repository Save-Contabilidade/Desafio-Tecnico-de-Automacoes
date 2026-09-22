"""Testes das regras de validação."""

from __future__ import annotations

import pytest

from src.models import DocumentRequest
from src.validator import validate


def build_request(**overrides: str) -> DocumentRequest:
    campos: dict[str, str] = {
        "request_id": "REQ-001",
        "company_name": "Empresa Alpha",
        "cnpj": "11.111.111/0001-11",
        "uf": "SC",
        "document_type": "NFE",
        "competence": "2026-08",
    }
    campos.update(overrides)
    return DocumentRequest(**campos)


def test_registro_valido_nao_tem_erros() -> None:
    resultado = validate(build_request())

    assert resultado.is_valid
    assert resultado.errors == []


def test_cnpj_normalizado_para_apenas_digitos() -> None:
    resultado = validate(build_request())

    assert resultado.request.cnpj == "11111111000111"


def test_uf_e_tipo_de_documento_sao_normalizados_para_maiusculas() -> None:
    resultado = validate(build_request(uf=" sc ", document_type="nfe"))

    assert resultado.is_valid
    assert resultado.request.uf == "SC"
    assert resultado.request.document_type == "NFE"


def test_request_id_vazio_e_invalido() -> None:
    resultado = validate(build_request(request_id="   "))

    assert not resultado.is_valid
    assert "request_id vazio" in resultado.message


@pytest.mark.parametrize(
    "cnpj",
    [
        "11.111.111/0001-1",  # 13 dígitos
        "111111110001111",  # 15 dígitos
        "1111111100011A",  # contém letra
        "",
    ],
)
def test_cnpj_invalido(cnpj: str) -> None:
    resultado = validate(build_request(cnpj=cnpj))

    assert not resultado.is_valid
    assert any("CNPJ" in erro for erro in resultado.errors)


def test_uf_inexistente() -> None:
    resultado = validate(build_request(uf="XX"))

    assert not resultado.is_valid
    assert any("UF" in erro for erro in resultado.errors)


def test_document_type_nao_permitido() -> None:
    resultado = validate(build_request(document_type="NF"))

    assert not resultado.is_valid
    assert any("document_type" in erro for erro in resultado.errors)


@pytest.mark.parametrize("competence", ["2026-13", "2026-00", "2026-8", "26-08", "08/2026", ""])
def test_competencia_fora_do_padrao(competence: str) -> None:
    resultado = validate(build_request(competence=competence))

    assert not resultado.is_valid
    assert any("competência" in erro for erro in resultado.errors)


def test_registro_pode_acumular_varios_erros() -> None:
    resultado = validate(build_request(request_id="", uf="XX", competence="2026-13"))

    assert len(resultado.errors) == 3
