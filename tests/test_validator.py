from __future__ import annotations

import pytest

from src.validator import normalize, normalize_cnpj, validate


def test_registro_valido_nao_tem_erros(make_request):
    assert validate(normalize(make_request(cnpj="11.111.111/0001-11"))) == []


def test_normaliza_cnpj_uf_e_tipo(make_request):
    request = normalize(make_request(cnpj="11.111.111/0001-11", uf="sc", document_type="nfe"))
    assert (request.cnpj, request.uf, request.document_type) == ("11111111000111", "SC", "NFE")


def test_normalize_cnpj_remove_pontuacao():
    assert normalize_cnpj(" 22.222.222/0001-22 ") == "22222222000122"


def test_request_id_vazio(make_request):
    assert validate(normalize(make_request(request_id=""))) == ["request_id vazio"]


@pytest.mark.parametrize(
    "cnpj",
    ["", "1111111100011", "111111110001111", "11.111.111/0001-1A", "11111111000١١١", "abc"],
)
def test_cnpj_invalido(make_request, cnpj):
    errors = validate(normalize(make_request(cnpj=cnpj)))
    assert errors == ["CNPJ deve conter 14 dígitos numéricos"]


@pytest.mark.parametrize("uf", ["XX", "", "S", "SCC", "BR"])
def test_uf_inexistente(make_request, uf):
    errors = validate(normalize(make_request(uf=uf)))
    assert len(errors) == 1 and errors[0].startswith("UF inexistente")


@pytest.mark.parametrize("uf", ["AC", "DF", "SP", "TO", "RS"])
def test_ufs_validas(make_request, uf):
    assert validate(normalize(make_request(uf=uf))) == []


@pytest.mark.parametrize("document_type", ["NFE", "NFCE", "NFSE", "CTE", "MDFE"])
def test_tipos_permitidos(make_request, document_type):
    assert validate(normalize(make_request(document_type=document_type))) == []


@pytest.mark.parametrize("document_type", ["", "NF", "BOLETO", "NFE "])
def test_tipo_nao_permitido(make_request, document_type):
    # "NFE " com espaço chega aqui sem strip, pois o strip é feito pelo leitor do CSV.
    errors = validate(normalize(make_request(document_type=document_type)))
    assert len(errors) == 1 and errors[0].startswith("Tipo de documento")


@pytest.mark.parametrize(
    "competence", ["", "2026-8", "2026-13", "2026-00", "08/2026", "2026-08-01", "26-08", "2026/08"]
)
def test_competencia_invalida(make_request, competence):
    errors = validate(normalize(make_request(competence=competence)))
    assert len(errors) == 1 and errors[0].startswith("Competência")


def test_acumula_todos_os_erros(make_request):
    request = make_request(request_id="", cnpj="123", uf="XX", document_type="X", competence="x")
    assert len(validate(normalize(request))) == 5


def test_erro_de_formato_substitui_as_demais_regras(make_request):
    request = make_request(uf="11111111000111", document_type="SP", format_error="linha com 7 colunas, esperado 6")
    assert validate(normalize(request)) == ["linha com 7 colunas, esperado 6"]


def test_request_id_vazio_informa_a_linha(make_request):
    assert validate(normalize(make_request(request_id="", line_number=3))) == ["request_id vazio (linha 3)"]


@pytest.mark.parametrize("competence", ["٢٠٢٦-08", "2026-٠8"])
def test_competencia_com_digitos_nao_ascii_e_invalida(make_request, competence):
    errors = validate(normalize(make_request(competence=competence)))
    assert len(errors) == 1 and errors[0].startswith("Competência")
