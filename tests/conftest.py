from __future__ import annotations

import pytest

from src.config import Settings
from src.models import DocumentRequest


@pytest.fixture
def settings() -> Settings:
    return Settings(
        api_base_url="http://api.test",
        api_token="token-de-teste",
        request_timeout=5,
        max_attempts=3,
        backoff_seconds=0.5,
    )


@pytest.fixture
def make_request():
    def factory(**overrides: str) -> DocumentRequest:
        fields = {
            "request_id": "REQ-001",
            "company_name": "Empresa Alpha",
            "cnpj": "11111111000111",
            "uf": "SC",
            "document_type": "NFE",
            "competence": "2026-08",
        }
        fields.update(overrides)
        return DocumentRequest(**fields)

    return factory
