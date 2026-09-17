from collections import defaultdict
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Mock API - Desafio de Automacoes", version="1.0.0")

EXPECTED_TOKEN = "desafio-local-token"
attempts_by_request: dict[str, int] = defaultdict(int)


class QueryRequest(BaseModel):
    request_id: str = Field(min_length=1)
    cnpj: str = Field(min_length=14, max_length=14)
    uf: str = Field(min_length=2, max_length=2)
    document_type: Literal["NFE", "NFCE", "NFSE", "CTE", "MDFE"]
    competence: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/documents/query")
def query_documents(
    payload: QueryRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    if authorization != f"Bearer {EXPECTED_TOKEN}":
        raise HTTPException(status_code=401, detail="Token invalido")

    attempts_by_request[payload.request_id] += 1
    attempt = attempts_by_request[payload.request_id]

    try:
        suffix = int(payload.request_id.rsplit("-", 1)[-1])
    except ValueError:
        suffix = sum(ord(char) for char in payload.request_id)

    scenario = suffix % 4

    if scenario == 2:
        raise HTTPException(status_code=404, detail="Nenhum documento encontrado")

    if scenario == 3 and attempt <= 2:
        raise HTTPException(status_code=429, detail="Limite temporario de requisicoes")

    if scenario == 0 and attempt == 1:
        raise HTTPException(status_code=500, detail="Erro temporario do servidor")

    document_count = (suffix % 3) + 1

    # Reinicia o estado deste request apos sucesso para que uma nova execucao
    # do desafio reproduza os mesmos cenarios sem reiniciar a API.
    attempts_by_request.pop(payload.request_id, None)

    return {
        "request_id": payload.request_id,
        "status": "success",
        "document_count": document_count,
        "message": "Consulta concluida",
    }
