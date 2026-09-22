"""Orquestração: validação, consulta à API e montagem dos resultados."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, Sequence

from . import validator
from .api_client import DocumentApiClient
from .models import DocumentRequest, ProcessingResult, ResultStatus

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now().astimezone()


class RequestProcessor:
    """Processa as solicitações lidas do CSV, uma a uma e na ordem original."""

    def __init__(
        self,
        client: DocumentApiClient,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._client = client
        self._clock = clock

    def process_all(self, requests: Sequence[DocumentRequest]) -> list[ProcessingResult]:
        """Processa todas as solicitações e devolve um resultado por linha."""
        seen_request_ids: set[str] = set()
        results: list[ProcessingResult] = []

        for position, request in enumerate(requests, start=1):
            logger.info(
                "Processando %d/%d (linha %d): %s",
                position,
                len(requests),
                request.line_number,
                request.request_id or "<sem request_id>",
            )
            results.append(self._process_one(request, seen_request_ids))

        return results

    def _process_one(
        self, request: DocumentRequest, seen_request_ids: set[str]
    ) -> ProcessingResult:
        validation = validator.validate(request)
        normalized = validation.request

        if not validation.is_valid:
            logger.warning(
                "%s: registro inválido — %s",
                normalized.request_id or f"linha {request.line_number}",
                validation.message,
            )
            return self._invalid(normalized, validation.message)

        if normalized.request_id in seen_request_ids:
            message = "request_id duplicado no arquivo de entrada"
            logger.warning("%s: %s", normalized.request_id, message)
            return self._invalid(normalized, message)

        seen_request_ids.add(normalized.request_id)

        outcome = self._client.query(normalized)
        result = ProcessingResult.from_outcome(normalized, outcome, self._clock())

        log = logger.info if result.status is ResultStatus.SUCCESS else logger.warning
        log(
            "%s: %s (tentativas=%d, http=%s) — %s",
            result.request_id,
            result.status,
            result.attempts,
            result.http_status if result.http_status is not None else "-",
            result.message,
        )
        return result

    def _invalid(self, request: DocumentRequest, message: str) -> ProcessingResult:
        return ProcessingResult(
            request_id=request.request_id,
            status=ResultStatus.INVALID,
            message=message,
            processed_at=self._clock(),
            attempts=0,
        )
