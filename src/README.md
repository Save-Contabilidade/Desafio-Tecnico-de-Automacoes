# Solução — Automação de Consulta de Documentos

Lê `input/solicitacoes.csv`, valida cada registro, consulta a API simulada com
retentativas e gera `output/resultado.csv`, `output/automation.log` e um resumo no terminal.

## Como executar (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Terminal 1 — API simulada:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn mock_api.app:app --host 127.0.0.1 --port 8000
```

Terminal 2 — automação:

```powershell
.\.venv\Scripts\Activate.ps1
python -m src.main --input input/solicitacoes.csv --output output/resultado.csv
```

Linux/macOS: troque a ativação por `source .venv/bin/activate` e `copy` por `cp`.

Saída esperada:

```text
Processamento concluído
Total: 6
Sucesso: 3
Não encontrados: 2
Inválidos: 1
Erros: 0
```

Opções extras: `--log-file <caminho>` (padrão: `automation.log` na pasta do `--output`)
e `-v/--verbose` (mostra logs informativos também no console).

O código de saída é `0` quando o lote é processado (mesmo que algumas solicitações
terminem em `error`) e `1` em falhas fatais: configuração ausente, arquivo de entrada
inexistente ou sem as colunas obrigatórias.

## Testes

```powershell
pytest
```

Os testes de ponta a ponta sobem a própria API simulada em uma porta livre, portanto não
é preciso iniciá-la antes.

## Configuração (variáveis de ambiente / `.env`)

| Variável | Padrão | Descrição |
|---|---|---|
| `API_BASE_URL` | `http://127.0.0.1:8000` | URL base da API |
| `API_TOKEN` | — (obrigatória) | Token enviado em `Authorization: Bearer` |
| `REQUEST_TIMEOUT` | `10` | Timeout de cada chamada HTTP, em segundos |
| `MAX_ATTEMPTS` | `3` | Tentativas no total (limitado a 3, conforme o desafio) |
| `RETRY_BACKOFF_SECONDS` | `1` | Base do backoff exponencial (1s, 2s, ...) |

Variáveis já definidas no ambiente têm precedência sobre o `.env`. O token nunca é
gravado em log (`Settings.__repr__` o mascara).

## Organização

| Módulo | Responsabilidade |
|---|---|
| `main.py` | CLI, configuração de logs, tratamento de falhas fatais e resumo |
| `config.py` | Leitura e validação das variáveis de ambiente |
| `reader.py` | Leitura do CSV (BOM, espaços, linhas vazias, colunas obrigatórias) |
| `validator.py` | Normalização (CNPJ sem pontuação, UF/tipo em maiúsculas) e regras de validação |
| `api_client.py` | Chamada HTTP, classificação das respostas e retentativas |
| `processor.py` | Orquestra validação → API → resultado; contabiliza o resumo |
| `writer.py` | Grava o CSV de saída de forma atômica |
| `models.py` | Dataclasses e enum de status compartilhados |

## Regras de validação

Um registro é `invalid` (e **não** chama a API) quando:

- `request_id` está vazio ou já apareceu antes no arquivo;
- o CNPJ não tem 14 dígitos numéricos após remover `.`, `/`, `-` e espaços;
- a UF não é uma das 27 unidades federativas;
- `document_type` não é `NFE`, `NFCE`, `NFSE`, `CTE` ou `MDFE`;
- a competência não segue `YYYY-MM` com mês de 01 a 12.

Todos os problemas do registro são listados na coluna `message`.

## Tratamento de erros e retentativas

| Situação | Status | Retentativa |
|---|---|---|
| HTTP 2xx com JSON válido | `success` | — |
| HTTP 404 | `not_found` | não |
| HTTP 400, 401, 403, 422 e demais 4xx | `error` | não |
| HTTP 429 ou 5xx | `error` se persistir | sim |
| Timeout ou falha de conexão | `error` se persistir | sim |
| HTTP 2xx com JSON inválido/inesperado | `error` | não |

- No máximo **3 tentativas no total**, com backoff exponencial (`1s`, `2s`). Se a API
  enviar `Retry-After`, ele é respeitado (limitado a 30s).
- Uma resposta de sucesso só é aceita se for um objeto JSON com `status == "success"`,
  `request_id` igual ao enviado e `document_count` inteiro não negativo.
- Timeout e falha de conexão também são tratados como temporários, pois tendem a se
  resolver sozinhos; entram no mesmo limite de 3 tentativas.
- Uma exceção inesperada em um registro é logada com traceback e vira `error`, sem
  interromper o restante do lote.

## Saída

`output/resultado.csv` mantém a ordem do arquivo de entrada, com as colunas
`request_id, status, http_status, attempts, message, document_count, processed_at`.
`http_status` e `document_count` ficam vazios quando não se aplicam; registros inválidos
têm `attempts = 0`. `processed_at` é ISO 8601 com fuso horário.

**Idempotência:** o CSV é escrito em um arquivo temporário e renomeado ao final, então
reexecutar sobrescreve o resultado anterior e uma execução interrompida nunca deixa um
arquivo pela metade. O `automation.log` é aberto em modo append para preservar o
histórico, com um marcador de início por execução.

## Decisões e melhorias futuras

- **Execução sequencial:** o volume é pequeno e a ordem sequencial deixa o log fácil de
  ler. Para lotes grandes, dá para usar `ThreadPoolExecutor` (a chamada é I/O-bound) com
  uma sessão HTTP por thread e um limite de concorrência para não provocar mais `429`.
- `query` é injetado no `processor`, então a orquestração é testada sem HTTP.
- Validação do dígito verificador do CNPJ, relatório de reprocessamento só dos `error`,
  e logs estruturados (JSON) seriam os próximos passos.
