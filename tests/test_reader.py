"""Testes da leitura do arquivo de entrada."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.reader import InputFileError, read_requests

CABECALHO = "request_id,company_name,cnpj,uf,document_type,competence\n"


def escrever_csv(tmp_path: Path, conteudo: str, encoding: str = "utf-8") -> Path:
    caminho = tmp_path / "solicitacoes.csv"
    caminho.write_text(conteudo, encoding=encoding)
    return caminho


def test_le_solicitacoes_na_ordem_do_arquivo(tmp_path: Path) -> None:
    caminho = escrever_csv(
        tmp_path,
        CABECALHO
        + "REQ-001,Empresa Alpha,11.111.111/0001-11,SC,NFE,2026-08\n"
        + "REQ-002,Empresa Beta,22.222.222/0001-22,SP,NFCE,2026-08\n",
    )

    solicitacoes = read_requests(caminho)

    assert [s.request_id for s in solicitacoes] == ["REQ-001", "REQ-002"]
    assert solicitacoes[0].line_number == 2
    assert solicitacoes[1].line_number == 3


def test_remove_espacos_em_branco_dos_campos(tmp_path: Path) -> None:
    caminho = escrever_csv(
        tmp_path,
        CABECALHO + "  REQ-001 ,Empresa Alpha, 11.111.111/0001-11 , SC , NFE , 2026-08 \n",
    )

    solicitacao = read_requests(caminho)[0]

    assert solicitacao.request_id == "REQ-001"
    assert solicitacao.uf == "SC"


def test_le_arquivo_salvo_com_bom(tmp_path: Path) -> None:
    caminho = escrever_csv(
        tmp_path,
        CABECALHO + "REQ-001,Empresa Alpha,11.111.111/0001-11,SC,NFE,2026-08\n",
        encoding="utf-8-sig",
    )

    solicitacoes = read_requests(caminho)

    assert solicitacoes[0].request_id == "REQ-001"


def test_arquivo_sem_linhas_de_dados(tmp_path: Path) -> None:
    caminho = escrever_csv(tmp_path, CABECALHO)

    assert read_requests(caminho) == []


def test_arquivo_inexistente(tmp_path: Path) -> None:
    with pytest.raises(InputFileError):
        read_requests(tmp_path / "nao_existe.csv")


def test_coluna_obrigatoria_ausente(tmp_path: Path) -> None:
    caminho = escrever_csv(tmp_path, "request_id,cnpj,uf\nREQ-001,11111111000111,SC\n")

    with pytest.raises(InputFileError) as exc:
        read_requests(caminho)

    assert "document_type" in str(exc.value)
