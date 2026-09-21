"""Leitura de configurações a partir de variáveis de ambiente (e do ``.env``)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = 1.0


class ConfigError(Exception):
    """Configuração ausente ou inválida."""


@dataclass(frozen=True, slots=True)
class Settings:
    api_base_url: str
    api_token: str
    request_timeout: float = DEFAULT_TIMEOUT_SECONDS
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS

    def __repr__(self) -> str:
        # Evita que o token apareça em logs ou tracebacks.
        return (
            f"Settings(api_base_url={self.api_base_url!r}, api_token='***', "
            f"request_timeout={self.request_timeout}, max_attempts={self.max_attempts}, "
            f"backoff_seconds={self.backoff_seconds})"
        )


def _read_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} deve ser numérico (valor atual: {raw!r})") from exc
    if value < 0:
        raise ConfigError(f"{name} não pode ser negativo")
    return value


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} deve ser um número inteiro (valor atual: {raw!r})") from exc
    if value < 1:
        raise ConfigError(f"{name} deve ser maior ou igual a 1")
    return value


def load_settings() -> Settings:
    """Carrega o ``.env`` (sem sobrescrever variáveis já definidas) e valida os valores."""
    load_dotenv(override=False)

    token = os.getenv("API_TOKEN", "").strip()
    if not token:
        raise ConfigError(
            "API_TOKEN não definido. Copie .env.example para .env ou defina a variável de ambiente."
        )

    base_url = os.getenv("API_BASE_URL", "").strip() or DEFAULT_BASE_URL

    request_timeout = _read_float("REQUEST_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)
    if request_timeout == 0:
        raise ConfigError("REQUEST_TIMEOUT deve ser maior que zero")

    return Settings(
        api_base_url=base_url.rstrip("/"),
        api_token=token,
        request_timeout=request_timeout,
        # O desafio limita a 3 tentativas no total; valores maiores são rebaixados.
        max_attempts=min(_read_int("MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS), DEFAULT_MAX_ATTEMPTS),
        backoff_seconds=_read_float("RETRY_BACKOFF_SECONDS", DEFAULT_BACKOFF_SECONDS),
    )
