"""Modelos de dados usados em toda a automação."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Iterable


class ResultStatus(str, Enum):
    """Status final de uma solicitação."""

    SUCCESS = "success"
    NOT_FOUND = "not_found"
    INVALID = "invalid"
    ERROR = "error"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DocumentRequest:
    """Uma linha do CSV de entrada."""

    request_id: str
    company_name: str
    cnpj: str
    uf: str
    document_type: str
    competence: str
    line_number: int = 0

    def to_payload(self) -> dict[str, str]:
        """Payload enviado para a API de consulta."""
        return {
            "request_id": self.request_id,
            "cnpj": self.cnpj,
            "uf": self.uf,
            "document_type": self.document_type,
            "competence": self.competence,
        }


@dataclass(frozen=True)
class QueryOutcome:
    """Resultado da consulta à API para uma solicitação."""

    status: ResultStatus
    message: str
    attempts: int
    http_status: int | None = None
    document_count: int | None = None


@dataclass(frozen=True)
class ProcessingResult:
    """Resultado final de uma solicitação, pronto para virar linha do CSV."""

    request_id: str
    status: ResultStatus
    message: str
    processed_at: datetime
    attempts: int = 0
    http_status: int | None = None
    document_count: int | None = None

    @classmethod
    def from_outcome(
        cls,
        request: DocumentRequest,
        outcome: QueryOutcome,
        processed_at: datetime,
    ) -> "ProcessingResult":
        """Cria o resultado final a partir da resposta da API."""
        return cls(
            request_id=request.request_id,
            status=outcome.status,
            message=outcome.message,
            processed_at=processed_at,
            attempts=outcome.attempts,
            http_status=outcome.http_status,
            document_count=outcome.document_count,
        )

    def to_row(self) -> dict[str, Any]:
        """Converte o resultado em uma linha do CSV de saída."""
        return {
            "request_id": self.request_id,
            "status": str(self.status),
            "http_status": "" if self.http_status is None else self.http_status,
            "attempts": self.attempts,
            "message": self.message,
            "document_count": "" if self.document_count is None else self.document_count,
            "processed_at": self.processed_at.isoformat(timespec="seconds"),
        }


@dataclass(frozen=True)
class Summary:
    """Contagem dos resultados da execução."""

    total: int = 0
    success: int = 0
    not_found: int = 0
    invalid: int = 0
    errors: int = 0
    documents: int = 0

    @classmethod
    def from_results(cls, results: Iterable[ProcessingResult]) -> "Summary":
        counters: dict[ResultStatus, int] = {status: 0 for status in ResultStatus}
        total = 0
        documents = 0
        for result in results:
            total += 1
            counters[result.status] += 1
            documents += result.document_count or 0
        return cls(
            total=total,
            success=counters[ResultStatus.SUCCESS],
            not_found=counters[ResultStatus.NOT_FOUND],
            invalid=counters[ResultStatus.INVALID],
            errors=counters[ResultStatus.ERROR],
            documents=documents,
        )

    def as_text(self) -> str:
        """Resumo formatado para exibição no terminal."""
        linhas = [
            "Processamento concluído",
            f"Total: {self.total}",
            f"Sucesso: {self.success}",
            f"Não encontrados: {self.not_found}",
            f"Inválidos: {self.invalid}",
            f"Erros: {self.errors}",
            f"Documentos retornados: {self.documents}",
        ]
        return "\n".join(linhas)


@dataclass(frozen=True)
class ValidationResult:
    """Solicitação normalizada e a lista de problemas encontrados."""

    request: DocumentRequest
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def message(self) -> str:
        return "; ".join(self.errors)
