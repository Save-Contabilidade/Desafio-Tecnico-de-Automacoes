"""Integração com a API de consulta de documentos.

Regras de retentativa (`docs/DESAFIO.md`):

* HTTP 429 e HTTP 5xx são temporários e podem ser repetidos;
* timeout e falha de conexão também são tratados como temporários;
* HTTP 400, 401, 403 e 404 nunca são repetidos;
* o limite é de `MAX_ATTEMPTS` tentativas no total (3 por padrão),
  contando a primeira chamada.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Callable

import requests

from .config import Settings
from .models import DocumentRequest, QueryOutcome, ResultStatus

logger = logging.getLogger(__name__)

MAX_RETRY_DELAY_SECONDS = 30.0
MAX_ERROR_MESSAGE_LENGTH = 200


@dataclass(frozen=True)
class _Attempt:
    """Resultado de uma única tentativa, com a indicação de repetir ou não."""

    outcome: QueryOutcome
    retryable: bool
    retry_after: float | None = None


class DocumentApiClient:
    """Cliente do endpoint `POST /v1/documents/query`."""

    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._session = session if session is not None else requests.Session()
        self._sleep = sleep

    def query(self, request: DocumentRequest) -> QueryOutcome:
        """Consulta a API, repetindo a chamada em caso de erro temporário."""
        max_attempts = self._settings.max_attempts
        outcome = QueryOutcome(
            status=ResultStatus.ERROR,
            message="Nenhuma tentativa realizada",
            attempts=0,
        )

        for attempt in range(1, max_attempts + 1):
            result = self._run_attempt(request, attempt)
            outcome = result.outcome

            if not result.retryable:
                return outcome

            if attempt >= max_attempts:
                logger.error(
                    "%s: limite de %d tentativas atingido. %s",
                    request.request_id,
                    max_attempts,
                    outcome.message,
                )
                return outcome

            delay = self._delay_for(attempt, result.retry_after)
            logger.warning(
                "%s: erro temporário na tentativa %d/%d (%s). Nova tentativa em %.1fs",
                request.request_id,
                attempt,
                max_attempts,
                outcome.message,
                delay,
            )
            self._sleep(delay)

        return outcome

    def _run_attempt(self, request: DocumentRequest, attempt: int) -> _Attempt:
        try:
            response = self._session.post(
                self._settings.query_url,
                json=request.to_payload(),
                headers=self._headers(),
                timeout=self._settings.request_timeout,
            )
        except requests.Timeout as exc:
            return _Attempt(
                outcome=self._error(f"Timeout ao consultar a API: {_shorten(exc)}", attempt),
                retryable=True,
            )
        except requests.RequestException as exc:
            return _Attempt(
                outcome=self._error(f"Falha de conexão com a API: {_shorten(exc)}", attempt),
                retryable=True,
            )

        return self._handle_response(response, attempt)

    def _handle_response(self, response: requests.Response, attempt: int) -> _Attempt:
        status_code = response.status_code

        if status_code == HTTPStatus.OK:
            return _Attempt(outcome=self._parse_success(response, attempt), retryable=False)

        message = f"HTTP {status_code}: {self._extract_error_message(response)}"

        if status_code == HTTPStatus.NOT_FOUND:
            return _Attempt(
                outcome=QueryOutcome(
                    status=ResultStatus.NOT_FOUND,
                    message=self._extract_error_message(response),
                    attempts=attempt,
                    http_status=status_code,
                ),
                retryable=False,
            )

        if status_code == HTTPStatus.TOO_MANY_REQUESTS or status_code >= 500:
            return _Attempt(
                outcome=self._error(message, attempt, http_status=status_code),
                retryable=True,
                retry_after=self._retry_after(response),
            )

        return _Attempt(
            outcome=self._error(message, attempt, http_status=status_code),
            retryable=False,
        )

    def _parse_success(self, response: requests.Response, attempt: int) -> QueryOutcome:
        try:
            body: Any = response.json()
        except ValueError:
            return self._error(
                "Resposta da API não é um JSON válido", attempt, http_status=response.status_code
            )

        if not isinstance(body, dict):
            return self._error(
                "Resposta da API em formato inesperado", attempt, http_status=response.status_code
            )

        status = str(body.get("status", "")).strip().lower()
        message = str(body.get("message") or "").strip()

        if status == ResultStatus.SUCCESS.value:
            document_count = _to_int(body.get("document_count"))
            if document_count is None:
                return self._error(
                    "Campo document_count ausente ou inválido na resposta",
                    attempt,
                    http_status=response.status_code,
                )
            return QueryOutcome(
                status=ResultStatus.SUCCESS,
                message=message or "Consulta concluída",
                attempts=attempt,
                http_status=response.status_code,
                document_count=document_count,
            )

        if status == ResultStatus.NOT_FOUND.value:
            return QueryOutcome(
                status=ResultStatus.NOT_FOUND,
                message=message or "Nenhum documento encontrado",
                attempts=attempt,
                http_status=response.status_code,
            )

        return self._error(
            f"Resposta inesperada da API (status={status!r})",
            attempt,
            http_status=response.status_code,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _delay_for(self, attempt: int, retry_after: float | None) -> float:
        """Backoff exponencial, respeitando o header `Retry-After` quando houver."""
        if retry_after is not None:
            return min(retry_after, MAX_RETRY_DELAY_SECONDS)
        backoff = self._settings.retry_backoff_seconds * (2 ** (attempt - 1))
        return min(backoff, MAX_RETRY_DELAY_SECONDS)

    @staticmethod
    def _retry_after(response: requests.Response) -> float | None:
        raw = (response.headers or {}).get("Retry-After")
        if raw is None:
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        return value if value >= 0 else None

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        try:
            body: Any = response.json()
        except ValueError:
            body = None

        if isinstance(body, dict):
            detail = body.get("detail") or body.get("message")
            if detail:
                return str(detail)[:MAX_ERROR_MESSAGE_LENGTH]

        text = (response.text or "").strip()
        return text[:MAX_ERROR_MESSAGE_LENGTH] or "sem detalhes na resposta"

    @staticmethod
    def _error(message: str, attempt: int, http_status: int | None = None) -> QueryOutcome:
        return QueryOutcome(
            status=ResultStatus.ERROR,
            message=message,
            attempts=attempt,
            http_status=http_status,
        )


def _shorten(value: object) -> str:
    """Encurta mensagens longas de exceção para caberem no CSV e nos logs."""
    texto = " ".join(str(value).split())
    if len(texto) <= MAX_ERROR_MESSAGE_LENGTH:
        return texto
    return f"{texto[:MAX_ERROR_MESSAGE_LENGTH]}..."


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
