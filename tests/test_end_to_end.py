"""Executa ``python -m src.main`` contra a API simulada real, em um processo separado."""

from __future__ import annotations

import csv
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import requests
import uvicorn

from mock_api.app import app

ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "input" / "solicitacoes.csv"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def mock_api_url():
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            requests.get(f"{url}/health", timeout=0.5)
            break
        except requests.ConnectionError:
            time.sleep(0.05)
    yield url
    server.should_exit = True
    thread.join(timeout=5)


def run_cli(tmp_path: Path, base_url: str, token: str = "desafio-local-token") -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "API_BASE_URL": base_url,
        "API_TOKEN": token,
        "RETRY_BACKOFF_SECONDS": "0.01",
        "REQUEST_TIMEOUT": "2",
        "PYTHONIOENCODING": "utf-8",
    }
    return subprocess.run(
        [sys.executable, "-m", "src.main", "--input", str(INPUT_FILE), "--output", str(tmp_path / "resultado.csv")],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60,
    )


def read_output(tmp_path: Path) -> dict[str, dict[str, str]]:
    with (tmp_path / "resultado.csv").open(encoding="utf-8", newline="") as file:
        return {row["request_id"]: row for row in csv.DictReader(file)}


def test_fluxo_completo(tmp_path, mock_api_url):
    completed = run_cli(tmp_path, mock_api_url)
    assert completed.returncode == 0, completed.stderr

    rows = read_output(tmp_path)
    assert {rid: row["status"] for rid, row in rows.items()} == {
        "REQ-001": "success",
        "REQ-002": "not_found",
        "REQ-003": "success",   # 429, 429, sucesso
        "REQ-004": "success",   # 500, sucesso
        "REQ-005": "invalid",   # UF XX
        "REQ-006": "not_found",
    }
    assert [rows[rid]["attempts"] for rid in sorted(rows)] == ["1", "1", "3", "2", "0", "1"]
    assert rows["REQ-001"]["document_count"] == "2"
    assert rows["REQ-005"]["http_status"] == ""

    for line in ("Total: 6", "Sucesso: 3", "Inválidos: 1", "Erros: 0"):
        assert line in completed.stdout

    log = (tmp_path / "automation.log").read_text(encoding="utf-8")
    assert "REQ-003" in log and "429" in log
    assert "desafio-local-token" not in log


def test_execucao_e_idempotente(tmp_path, mock_api_url):
    run_cli(tmp_path, mock_api_url)
    first = {rid: (r["status"], r["attempts"]) for rid, r in read_output(tmp_path).items()}
    run_cli(tmp_path, mock_api_url)
    second = {rid: (r["status"], r["attempts"]) for rid, r in read_output(tmp_path).items()}
    assert first == second


def test_token_invalido_gera_erro_401_sem_retentativa(tmp_path, mock_api_url):
    completed = run_cli(tmp_path, mock_api_url, token="errado")
    assert completed.returncode == 0

    rows = read_output(tmp_path)
    called = [row for row in rows.values() if row["status"] != "invalid"]
    assert called and all(row["status"] == "error" and row["http_status"] == "401"
                          and row["attempts"] == "1" for row in called)


def test_api_fora_do_ar_gera_erro_apos_tres_tentativas(tmp_path):
    completed = run_cli(tmp_path, f"http://127.0.0.1:{free_port()}")
    assert completed.returncode == 0

    rows = read_output(tmp_path)
    assert rows["REQ-001"]["status"] == "error"
    assert rows["REQ-001"]["attempts"] == "3"
    assert "Erros: 5" in completed.stdout
