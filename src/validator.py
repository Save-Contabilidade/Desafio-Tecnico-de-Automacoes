"""Regras de validação aplicadas antes de chamar a API."""

from __future__ import annotations

import re
from dataclasses import replace

from src.models import DocumentRequest

VALID_UFS = frozenset(
    {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
        "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }
)
VALID_DOCUMENT_TYPES = frozenset({"NFE", "NFCE", "NFSE", "CTE", "MDFE"})

_COMPETENCE_PATTERN = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
_CNPJ_PUNCTUATION = re.compile(r"[.\-/\s]")


def normalize_cnpj(cnpj: str) -> str:
    """Remove a pontuação usual do CNPJ (``.``, ``/``, ``-`` e espaços)."""
    return _CNPJ_PUNCTUATION.sub("", cnpj)


def normalize(request: DocumentRequest) -> DocumentRequest:
    """Padroniza os campos para o formato enviado à API."""
    return replace(
        request,
        cnpj=normalize_cnpj(request.cnpj),
        uf=request.uf.upper(),
        document_type=request.document_type.upper(),
    )


def validate(request: DocumentRequest) -> list[str]:
    """Devolve os problemas encontrados; lista vazia significa registro válido.

    Espera um registro já normalizado por :func:`normalize`.
    """
    if request.format_error:
        # Com as colunas deslocadas, as demais regras só produziriam mensagens enganosas.
        return [request.format_error]

    errors: list[str] = []

    if not request.request_id:
        location = f" (linha {request.line_number})" if request.line_number else ""
        errors.append(f"request_id vazio{location}")

    if not (len(request.cnpj) == 14 and request.cnpj.isascii() and request.cnpj.isdigit()):
        errors.append("CNPJ deve conter 14 dígitos numéricos")

    if request.uf not in VALID_UFS:
        errors.append(f"UF inexistente: {request.uf or '(vazia)'}")

    if request.document_type not in VALID_DOCUMENT_TYPES:
        errors.append(f"Tipo de documento não permitido: {request.document_type or '(vazio)'}")

    if not _COMPETENCE_PATTERN.fullmatch(request.competence):
        errors.append(f"Competência fora do padrão YYYY-MM: {request.competence or '(vazia)'}")

    return errors
