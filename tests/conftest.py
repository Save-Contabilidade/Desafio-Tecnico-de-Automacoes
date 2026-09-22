"""Fixtures compartilhadas pelos testes."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config import Settings
from tests.fakes import SleepSpy


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        api_base_url="http://api.local",
        api_token="token-de-teste",
        request_timeout=1.0,
        max_attempts=3,
        retry_backoff_seconds=0.0,
        log_file=tmp_path / "automation.log",
    )


@pytest.fixture
def sleep_spy() -> SleepSpy:
    return SleepSpy()
