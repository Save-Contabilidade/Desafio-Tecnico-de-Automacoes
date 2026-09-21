"""Estruturas de dados compartilhadas entre as etapas da automação."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ResultStatus(StrEnum):
    """Status final de uma solicitação no CSV de saída."""

    SUCCESS = "success"
    NOT_FOUND = "not_found"
    INVALID = "invalid"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class DocumentRequest:
    """Linha do CSV de entrada, com espaços das bordas já removidos."""

    request_id: str
    company_name: str
    cnpj: str
    uf: str
    document_type: str
    competence: str

    def to_payload(self) -> dict[str, str]:
        """Monta o corpo esperado pelo endpoint ``POST /v1/documents/query``."""
        return {
            "request_id": self.request_id,
            "cnpj": self.cnpj,
            "uf": self.uf,
            "document_type": self.document_type,
            "competence": self.competence,
        }


@dataclass(frozen=True, slots=True)
class ApiResult:
    """Resultado final de uma consulta à API, já considerando as retentativas."""

    status: ResultStatus
    message: str
    attempts: int
    http_status: int | None = None
    document_count: int | None = None


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    """Linha do CSV de saída."""

    request_id: str
    status: ResultStatus
    http_status: int | None
    attempts: int
    message: str
    document_count: int | None
    processed_at: str
