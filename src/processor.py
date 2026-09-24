"""Orquestração: valida cada solicitação, consulta a API e consolida os resultados."""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime

from src.models import ApiResult, DocumentRequest, ProcessingResult, ResultStatus
from src.validator import normalize, validate

logger = logging.getLogger(__name__)

QueryFunction = Callable[[DocumentRequest], ApiResult]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class Summary:
    total: int
    success: int
    not_found: int
    invalid: int
    error: int

    @classmethod
    def from_results(cls, results: Iterable[ProcessingResult]) -> Summary:
        results = list(results)
        counts = Counter(result.status for result in results)
        return cls(
            total=len(results),
            success=counts[ResultStatus.SUCCESS],
            not_found=counts[ResultStatus.NOT_FOUND],
            invalid=counts[ResultStatus.INVALID],
            error=counts[ResultStatus.ERROR],
        )

    def render(self) -> str:
        return "\n".join(
            [
                "Processamento concluído",
                f"Total: {self.total}",
                f"Sucesso: {self.success}",
                f"Não encontrados: {self.not_found}",
                f"Inválidos: {self.invalid}",
                f"Erros: {self.error}",
            ]
        )


def process_requests(
    requests: Iterable[DocumentRequest],
    query: QueryFunction,
    clock: Callable[[], str] = now_iso,
) -> list[ProcessingResult]:
    """Processa as solicitações na ordem do arquivo.

    ``query`` é injetado para desacoplar a orquestração do cliente HTTP (facilita testes).
    Registros inválidos e ``request_id`` repetidos não chegam a chamar a API.
    """
    results: list[ProcessingResult] = []
    seen_ids: set[str] = set()

    for raw in requests:
        request = normalize(raw)
        errors = validate(request)
        if request.request_id:
            if request.request_id in seen_ids:
                errors.append("request_id duplicado no arquivo de entrada")
            # Registrado mesmo se o registro for inválido: o id já apareceu no arquivo.
            seen_ids.add(request.request_id)

        if errors:
            message = "; ".join(errors)
            logger.warning(
                "%s: registro inválido, API não consultada (%s)",
                request.request_id or "<sem id>", message,
            )
            results.append(
                ProcessingResult(
                    request_id=request.request_id,
                    status=ResultStatus.INVALID,
                    http_status=None,
                    attempts=0,
                    message=message,
                    document_count=None,
                    processed_at=clock(),
                )
            )
            continue

        logger.info(
            "%s: consultando %s de %s (UF %s, competência %s)",
            request.request_id, request.document_type, request.company_name or request.cnpj,
            request.uf, request.competence,
        )
        try:
            api_result = query(request)
        except Exception as exc:  # proteção final: um registro não pode derrubar o lote
            logger.exception("%s: erro inesperado ao consultar a API", request.request_id)
            api_result = ApiResult(ResultStatus.ERROR, f"Erro inesperado: {exc}", attempts=1)

        # not_found é um desfecho de negócio esperado; só erros merecem destaque.
        log_level = logging.WARNING if api_result.status is ResultStatus.ERROR else logging.INFO
        logger.log(
            log_level,
            "%s: %s (HTTP %s, %d tentativa(s)) - %s",
            request.request_id, api_result.status.value, api_result.http_status or "-",
            api_result.attempts, api_result.message,
        )
        results.append(
            ProcessingResult(
                request_id=request.request_id,
                status=api_result.status,
                http_status=api_result.http_status,
                attempts=api_result.attempts,
                message=api_result.message,
                document_count=api_result.document_count,
                processed_at=clock(),
            )
        )

    return results
