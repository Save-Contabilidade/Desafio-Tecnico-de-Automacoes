"""Normalização e validação das solicitações antes da chamada à API."""

from __future__ import annotations

import re
from dataclasses import replace

from .models import DocumentRequest, ValidationResult

VALID_UFS = frozenset(
    {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
        "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
        "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }
)

VALID_DOCUMENT_TYPES = frozenset({"NFE", "NFCE", "NFSE", "CTE", "MDFE"})

CNPJ_LENGTH = 14
CNPJ_PUNCTUATION = re.compile(r"[.\-/\s]")
# Aceita apenas meses de 01 a 12: "2026-13" é considerado inválido.
COMPETENCE_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def validate(request: DocumentRequest) -> ValidationResult:
    """Normaliza a solicitação e devolve a lista de problemas encontrados."""
    normalized = normalize(request)
    errors: list[str] = []

    if not normalized.request_id:
        errors.append("request_id vazio")

    if len(normalized.cnpj) != CNPJ_LENGTH or not normalized.cnpj.isdigit():
        errors.append(f"CNPJ inválido: {request.cnpj!r}")

    if normalized.uf not in VALID_UFS:
        errors.append(f"UF inexistente: {request.uf!r}")

    if normalized.document_type not in VALID_DOCUMENT_TYPES:
        errors.append(f"document_type inválido: {request.document_type!r}")

    if not COMPETENCE_PATTERN.match(normalized.competence):
        errors.append(f"competência fora do padrão YYYY-MM: {request.competence!r}")

    return ValidationResult(request=normalized, errors=errors)


def normalize(request: DocumentRequest) -> DocumentRequest:
    """Padroniza os campos antes da validação e do envio para a API.

    A API espera o CNPJ apenas com dígitos e UF/tipo de documento em maiúsculas.
    """
    return replace(
        request,
        request_id=request.request_id.strip(),
        cnpj=strip_cnpj_punctuation(request.cnpj),
        uf=request.uf.strip().upper(),
        document_type=request.document_type.strip().upper(),
        competence=request.competence.strip(),
    )


def strip_cnpj_punctuation(cnpj: str) -> str:
    """Remove a pontuação do CNPJ, preservando qualquer outro caractere.

    Caracteres não numéricos que não sejam pontuação (letras, por exemplo)
    são mantidos de propósito, para que o CNPJ seja reprovado na validação.
    """
    return CNPJ_PUNCTUATION.sub("", cnpj.strip())
