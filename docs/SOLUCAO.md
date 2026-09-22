# Solução — Automação de Consulta de Documentos

Lê `input/solicitacoes.csv`, valida cada registro, consulta a API com
retentativas para erros temporários e gera `output/resultado.csv` +
`output/automation.log` + resumo no terminal.

## Execução

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                                 # Windows: copy .env.example .env
uvicorn mock_api.app:app --host 127.0.0.1 --port 8000  # outro terminal
python -m src.main --input input/solicitacoes.csv --output output/resultado.csv
```

| Argumento | Padrão | Descrição |
|---|---|---|
| `--input` | `input/solicitacoes.csv` | CSV de entrada |
| `--output` | `output/resultado.csv` | CSV de saída |
| `--env-file` | `.env` | Arquivo de variáveis de ambiente alternativo |
| `--verbose` | desligado | Logs em nível DEBUG |

Saída `0` ao final do processamento (mesmo com linhas `invalid`/`error`);
`2` para falha que impede a execução (token ausente, entrada inexistente).

## Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `API_TOKEN` | — | Obrigatória. Enviada em `Authorization: Bearer` |
| `API_BASE_URL` | `http://127.0.0.1:8000` | Endereço base da API |
| `REQUEST_TIMEOUT` | `10` | Timeout por requisição (s) |
| `MAX_ATTEMPTS` | `3` | Tentativas no total por solicitação |
| `RETRY_BACKOFF_SECONDS` | `0.5` | Base do backoff exponencial |
| `LOG_FILE` | `output/automation.log` | Caminho do log |

Sem `API_TOKEN` a execução para antes de qualquer chamada à API.

## Estrutura

```text
src/
  main.py            CLI, fluxo e resumo
  config.py          variáveis de ambiente
  models.py          dataclasses (solicitação, resultado, resumo)
  reader.py          leitura do CSV
  validator.py       normalização + validação
  api_client.py      chamada HTTP + retentativas
  processor.py        orquestração (validação → consulta)
  writer.py           escrita do CSV de saída
  logging_config.py   logs (arquivo + terminal)
tests/                 pytest
```

Módulos não se conhecem entre si — leitura, validação, integração e escrita
são testáveis isoladamente.

## Validação

Registro vira `invalid` (não chama a API) se:

- `request_id` vazio ou já usado em outra linha do arquivo;
- CNPJ sem 14 dígitos após remover pontuação;
- UF fora das 27 unidades federativas;
- `document_type` fora de `NFE, NFCE, NFSE, CTE, MDFE`;
- `competence` fora de `YYYY-MM` (mês 01–12).

Antes de validar: espaços removidos, UF/`document_type` em maiúsculas, CNPJ
reduzido a dígitos. Todos os erros da linha vão na mesma mensagem.

## Erros e retentativas

| Situação | Status | Repete |
|---|---|---|
| 200 + `status: success` | `success` | — |
| 404 | `not_found` | não |
| 429 / 5xx / timeout / falha de conexão | `error` (após esgotar tentativas) | sim |
| 400 / 401 / 403 / demais 4xx | `error` | não |
| JSON inválido ou resposta inesperada | `error` | não |

`MAX_ATTEMPTS` conta a primeira chamada (padrão 3, não 3 retentativas).
Backoff exponencial a partir de `RETRY_BACKOFF_SECONDS`, respeitando
`Retry-After` quando presente. Nenhuma falha de API interrompe o lote.

## Saída

`output/resultado.csv` — uma linha por linha de entrada, na mesma ordem,
reescrito por completo a cada execução (idempotente):

```text
request_id,status,http_status,attempts,message,document_count,processed_at
REQ-001,success,200,1,Consulta concluida,2,2026-09-22T14:31:07-03:00
```

Campos que não se aplicam ficam vazios. `output/automation.log` registra
cada solicitação, cada retentativa e o resumo final.

## Testes

```bash
pytest
```

48 testes, sem depender da API simulada (HTTP e `time.sleep` mockados):

- `test_validator.py` — regras e normalização;
- `test_reader.py` — CSV com espaços, BOM, coluna ausente, arquivo inexistente;
- `test_api_client.py` — sucesso, 404, 401, 400, 429→200, 500 persistente,
  timeout, falha de conexão, JSON inválido, backoff, `Retry-After`;
- `test_processor.py` — inválido não chama API, duplicidade, ordem, resumo;
- `test_main.py` — CSV final, idempotência, códigos de saída via CLI.

## Decisões técnicas

- Processamento sequencial: volume pequeno e a API tem rate limit por
  solicitação; concorrência só aumentaria os 429.
- `request_id` duplicado vira `invalid` na segunda ocorrência.
- Timeout/falha de conexão entram na retentativa (não exigido, mas é o
  caso típico de instabilidade transitória).
- Sem dependências novas além de `pytest`.

## Melhorias futuras

- `--dry-run` (valida sem chamar a API);
- processamento concorrente com limite de requisições/segundo;
- retomada de execução (reprocessar só o que não teve status final).
