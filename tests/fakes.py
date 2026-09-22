"""Dublês de teste para simular a sessão HTTP e o `time.sleep`."""

from __future__ import annotations

import json
from typing import Any, Iterable


class FakeResponse:
    """Resposta HTTP mínima, com a mesma interface usada pelo cliente."""

    def __init__(
        self,
        status_code: int,
        payload: Any = None,
        text: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text if text is not None else json.dumps(payload or {})

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("resposta sem JSON válido")
        return self._payload


class FakeSession:
    """Sessão que devolve respostas pré-programadas (ou levanta exceções)."""

    def __init__(self, responses: Iterable[Any]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        if not self._responses:
            raise AssertionError("A sessão recebeu mais chamadas do que o esperado")
        resposta = self._responses.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


class SleepSpy:
    """Substitui `time.sleep` nos testes e registra os intervalos usados."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


def success_payload(request_id: str = "REQ-001", document_count: int = 2) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "status": "success",
        "document_count": document_count,
        "message": "Consulta concluida",
    }
