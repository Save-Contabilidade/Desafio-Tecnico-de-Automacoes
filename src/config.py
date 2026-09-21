import math
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    api_base_url: str
    api_token: str
    request_timeout: float
    max_attempts: int


def _required(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"{name} é obrigatório e não pode estar vazio")
    return value.strip()


def load_config(dotenv_path: str | Path | None = None) -> Config:
    env_file = Path(dotenv_path) if dotenv_path is not None else Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_file)

    api_base_url = _required("API_BASE_URL")
    try:
        parsed_url = urlsplit(api_base_url)
        valid_url = (
            parsed_url.scheme in {"http", "https"}
            and parsed_url.hostname is not None
            and not parsed_url.query
            and not parsed_url.fragment
        )
        parsed_url.port
    except ValueError as exc:
        raise ValueError("API_BASE_URL deve ser uma URL HTTP ou HTTPS válida") from exc
    if not valid_url:
        raise ValueError("API_BASE_URL deve ser uma URL HTTP ou HTTPS válida")

    api_token = _required("API_TOKEN")

    timeout_value = _required("REQUEST_TIMEOUT")
    try:
        request_timeout = float(timeout_value)
    except ValueError as exc:
        raise ValueError("REQUEST_TIMEOUT deve ser um número maior que zero") from exc
    if not math.isfinite(request_timeout) or request_timeout <= 0:
        raise ValueError("REQUEST_TIMEOUT deve ser um número maior que zero")

    attempts_value = _required("MAX_ATTEMPTS")
    try:
        max_attempts = int(attempts_value)
    except ValueError as exc:
        raise ValueError("MAX_ATTEMPTS deve ser um inteiro maior ou igual a 1") from exc
    if max_attempts < 1:
        raise ValueError("MAX_ATTEMPTS deve ser um inteiro maior ou igual a 1")

    return Config(
        api_base_url=api_base_url,
        api_token=api_token,
        request_timeout=request_timeout,
        max_attempts=max_attempts,
    )
