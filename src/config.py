"""Leitura e validação das configurações da automação.

Todas as configurações (inclusive o token da API) vêm de variáveis de
ambiente, carregadas a partir do arquivo `.env` quando ele existir.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_REQUEST_TIMEOUT = 10.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 0.5
DEFAULT_LOG_FILE = "output/automation.log"

QUERY_ENDPOINT = "/v1/documents/query"


class ConfigError(RuntimeError):
    """Configuração obrigatória ausente ou com valor inválido."""


@dataclass(frozen=True)
class Settings:
    """Configurações usadas pela automação."""

    api_base_url: str
    api_token: str
    request_timeout: float
    max_attempts: int
    retry_backoff_seconds: float
    log_file: Path

    @property
    def query_url(self) -> str:
        """URL completa do endpoint de consulta de documentos."""
        return f"{self.api_base_url.rstrip('/')}{QUERY_ENDPOINT}"


def load_settings(env_file: Path | None = None) -> Settings:
    """Carrega as configurações do ambiente.

    Variáveis já definidas no ambiente têm prioridade sobre o arquivo `.env`.
    """
    if env_file is None:
        load_dotenv(override=False)
    else:
        if not env_file.is_file():
            raise ConfigError(f"Arquivo de variáveis de ambiente não encontrado: {env_file}")
        load_dotenv(dotenv_path=env_file, override=False)

    token = _read_text("API_TOKEN", default="")
    if not token:
        raise ConfigError(
            "API_TOKEN não definido. Copie o arquivo .env.example para .env "
            "e informe o token da API."
        )

    return Settings(
        api_base_url=_read_text("API_BASE_URL", DEFAULT_API_BASE_URL),
        api_token=token,
        request_timeout=_read_float("REQUEST_TIMEOUT", DEFAULT_REQUEST_TIMEOUT, minimum=0.1),
        max_attempts=_read_int("MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS, minimum=1),
        retry_backoff_seconds=_read_float(
            "RETRY_BACKOFF_SECONDS", DEFAULT_RETRY_BACKOFF_SECONDS, minimum=0.0
        ),
        log_file=Path(_read_text("LOG_FILE", DEFAULT_LOG_FILE)),
    )


def _read_text(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _read_int(name: str, default: int, minimum: int) -> int:
    raw = _read_text(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} deve ser um número inteiro. Valor recebido: {raw!r}") from exc
    if value < minimum:
        raise ConfigError(f"{name} deve ser maior ou igual a {minimum}. Valor recebido: {value}")
    return value


def _read_float(name: str, default: float, minimum: float) -> float:
    raw = _read_text(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} deve ser um número. Valor recebido: {raw!r}") from exc
    if value < minimum:
        raise ConfigError(f"{name} deve ser maior ou igual a {minimum}. Valor recebido: {value}")
    return value
