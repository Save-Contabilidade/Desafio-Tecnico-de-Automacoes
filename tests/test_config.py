from __future__ import annotations

import pytest

from src import config
from src.config import ConfigError, load_settings

ENV_VARS = ("API_BASE_URL", "API_TOKEN", "REQUEST_TIMEOUT", "MAX_ATTEMPTS", "RETRY_BACKOFF_SECONDS")


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    # Impede que o .env local interfira nos testes.
    monkeypatch.setattr(config, "load_dotenv", lambda **_: False)
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_token_obrigatorio():
    with pytest.raises(ConfigError, match="API_TOKEN"):
        load_settings()


def test_valores_padrao(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "abc")
    settings = load_settings()
    assert settings.api_base_url == "http://127.0.0.1:8000"
    assert (settings.request_timeout, settings.max_attempts) == (10.0, 3)


def test_le_variaveis(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "abc")
    monkeypatch.setenv("API_BASE_URL", "http://outra:9000/")
    monkeypatch.setenv("REQUEST_TIMEOUT", "2.5")
    monkeypatch.setenv("MAX_ATTEMPTS", "2")
    settings = load_settings()
    assert settings.api_base_url == "http://outra:9000"
    assert (settings.request_timeout, settings.max_attempts) == (2.5, 2)


def test_max_attempts_limitado_a_tres(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "abc")
    monkeypatch.setenv("MAX_ATTEMPTS", "10")
    assert load_settings().max_attempts == 3


@pytest.mark.parametrize("name,value", [("REQUEST_TIMEOUT", "x"), ("REQUEST_TIMEOUT", "0"),
                                        ("MAX_ATTEMPTS", "0"), ("MAX_ATTEMPTS", "1.5")])
def test_valores_invalidos(monkeypatch, name, value):
    monkeypatch.setenv("API_TOKEN", "abc")
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigError, match=name):
        load_settings()


def test_repr_nao_expoe_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "segredo-super-secreto")
    assert "segredo-super-secreto" not in repr(load_settings())


@pytest.mark.parametrize(
    "name,value",
    [
        ("REQUEST_TIMEOUT", "inf"), ("REQUEST_TIMEOUT", "nan"),
        ("RETRY_BACKOFF_SECONDS", "inf"), ("RETRY_BACKOFF_SECONDS", "nan"),
    ],
)
def test_valores_nao_finitos_sao_rejeitados(monkeypatch, name, value):
    monkeypatch.setenv("API_TOKEN", "abc")
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigError, match=name):
        load_settings()
