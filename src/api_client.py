"""Integração com a API de consulta de documentos, incluindo retentativas."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import requests

from src.config import Settings
from src.models import ApiResult, DocumentRequest, ResultStatus

logger = logging.getLogger(__name__)

QUERY_PATH = "/v1/documents/query"
MAX_RETRY_AFTER_SECONDS = 30.0


class _TransientError(Exception):
    """Falha temporária que justifica uma nova tentativa."""

    def __init__(self, message: str, http_status: int | None = None, retry_after: float | None = None):
        super().__init__(message)
        self.http_status = http_status
        self.retry_after = retry_after


def is_retryable_status(http_status: int) -> bool:
    """HTTP 429 (rate limit) e 5xx são temporários; os demais 4xx são definitivos."""
    return http_status == 429 or 500 <= http_status <= 599


class DocumentApiClient:
    """Cliente do endpoint ``POST /v1/documents/query``.

    Política de retentativa:
      * HTTP 429, HTTP 5xx, timeout e falha de conexão -> nova tentativa com backoff
        exponencial (``backoff * 2 ** (tentativa - 1)``), até ``max_attempts`` no total;
      * HTTP 404 -> ``not_found``, sem retentativa;
      * demais 4xx (400, 401, 403, 422...) -> ``error``, sem retentativa;
      * 2xx com JSON inválido ou inesperado -> ``error``, sem retentativa.
    """

    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._session = session or requests.Session()
        self._sleep = sleep
        self._url = f"{settings.api_base_url}{QUERY_PATH}"

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> DocumentApiClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def query(self, request: DocumentRequest) -> ApiResult:
        max_attempts = self._settings.max_attempts
        last_error: _TransientError | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                return self._attempt(request, attempt)
            except _TransientError as error:
                last_error = error
                logger.warning(
                    "%s: falha temporária na tentativa %d/%d: %s",
                    request.request_id, attempt, max_attempts, error,
                )
                if attempt < max_attempts:
                    delay = self._retry_delay(attempt, error.retry_after)
                    logger.info("%s: nova tentativa em %.2fs", request.request_id, delay)
                    self._sleep(delay)

        assert last_error is not None  # o laço só termina sem retorno após falhas temporárias
        return ApiResult(
            status=ResultStatus.ERROR,
            message=f"Falha após {max_attempts} tentativa(s): {last_error}",
            attempts=max_attempts,
            http_status=last_error.http_status,
        )

    def _attempt(self, request: DocumentRequest, attempt: int) -> ApiResult:
        """Executa uma única chamada HTTP.

        Devolve o resultado definitivo ou levanta ``_TransientError`` se valer a pena repetir.
        """
        logger.debug("%s: tentativa %d -> POST %s", request.request_id, attempt, self._url)
        try:
            response = self._session.post(
                self._url,
                json=request.to_payload(),
                headers={"Authorization": f"Bearer {self._settings.api_token}"},
                timeout=self._settings.request_timeout,
            )
        except requests.Timeout as exc:
            raise _TransientError(f"Timeout após {self._settings.request_timeout}s") from exc
        except requests.ConnectionError as exc:
            raise _TransientError(f"Falha de conexão com a API: {exc.__class__.__name__}") from exc
        except requests.RequestException as exc:
            # Erros de requisição não relacionados à rede (ex.: URL inválida) não melhoram
            # com retentativa.
            return ApiResult(ResultStatus.ERROR, f"Erro na requisição: {exc}", attempt)

        http_status = response.status_code
        if is_retryable_status(http_status):
            raise _TransientError(
                f"HTTP {http_status}: {_error_detail(response)}",
                http_status=http_status,
                retry_after=_parse_retry_after(response),
            )
        if http_status == 404:
            return ApiResult(
                ResultStatus.NOT_FOUND, _error_detail(response), attempt, http_status=http_status
            )
        if not 200 <= http_status <= 299:
            return ApiResult(
                ResultStatus.ERROR,
                f"HTTP {http_status}: {_error_detail(response)}",
                attempt,
                http_status=http_status,
            )
        return _parse_success(request, response, attempt)

    def _retry_delay(self, attempt: int, retry_after: float | None) -> float:
        backoff = self._settings.backoff_seconds * (2 ** (attempt - 1))
        if retry_after is not None:
            return max(backoff, min(retry_after, MAX_RETRY_AFTER_SECONDS))
        return backoff


def _parse_success(request: DocumentRequest, response: requests.Response, attempt: int) -> ApiResult:
    http_status = response.status_code

    def invalid(reason: str) -> ApiResult:
        logger.error("%s: resposta inesperada da API (%s)", request.request_id, reason)
        return ApiResult(
            ResultStatus.ERROR, f"Resposta inválida da API: {reason}", attempt, http_status=http_status
        )

    try:
        body: Any = response.json()
    except ValueError:
        return invalid("corpo não é um JSON válido")

    if not isinstance(body, dict):
        return invalid("JSON não é um objeto")
    if body.get("status") != "success":
        return invalid(f"status inesperado {body.get('status')!r}")
    if body.get("request_id") != request.request_id:
        return invalid(f"request_id divergente {body.get('request_id')!r}")

    document_count = body.get("document_count")
    # bool é subclasse de int em Python; True não é uma contagem válida.
    if isinstance(document_count, bool) or not isinstance(document_count, int) or document_count < 0:
        return invalid(f"document_count inválido {document_count!r}")

    message = body.get("message")
    return ApiResult(
        status=ResultStatus.SUCCESS,
        message=message if isinstance(message, str) and message else "Consulta concluída",
        attempts=attempt,
        http_status=http_status,
        document_count=document_count,
    )


def _error_detail(response: requests.Response) -> str:
    """Extrai a mensagem de erro (campo ``detail`` do FastAPI) sem depender do formato."""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        detail = body.get("detail") or body.get("message")
        if isinstance(detail, str) and detail:
            return detail
        if detail:
            return str(detail)[:200]
    text = (response.text or "").strip()
    return text[:200] if text else (response.reason or "sem detalhes")


def _parse_retry_after(response: requests.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(float(raw), 0.0)
    except ValueError:
        return None  # formato de data HTTP não é suportado; usa apenas o backoff
