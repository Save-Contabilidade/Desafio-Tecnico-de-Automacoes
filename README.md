# Desafio Técnico de Automações

Este repositório contém a solução do desafio técnico para a vaga de **Desenvolvedor de Automações** da Save Contabilidade.

## Documentação do desafio

Os requisitos e critérios oficiais estão disponíveis em:

- [docs/DESAFIO.md](docs/DESAFIO.md)
- [docs/CRITERIOS_AVALIACAO.md](docs/CRITERIOS_AVALIACAO.md)

## Solução implementada

A aplicação lê solicitações de um arquivo CSV, valida cada registro, consulta a API simulada para os registros válidos e gera um CSV consolidado. A execução também cria um arquivo de log e apresenta um resumo no terminal.

Os resultados são classificados como `success`, `not_found`, `invalid` ou `error`.

## Arquitetura

| Módulo | Responsabilidade |
|---|---|
| `src/reader.py` | Leitura das solicitações do arquivo CSV. |
| `src/validator.py` | Validação dos campos de cada registro. |
| `src/config.py` | Carregamento e validação das variáveis de ambiente. |
| `src/api_client.py` | Integração HTTP, retentativas e tratamento das respostas da API. |
| `src/processor.py` | Coordenação da validação dos registros e das consultas à API. |
| `src/writer.py` | Escrita do CSV consolidado de resultados. |
| `src/logger.py` | Configuração do arquivo de log da aplicação. |
| `src/main.py` | Orquestração do fluxo e definição da interface de linha de comando. |

## Instalação

É necessário ter Python 3.11 ou superior.

Crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente no Linux ou macOS:

```bash
source .venv/bin/activate
```

No Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Crie o arquivo local de variáveis de ambiente:

```bash
cp .env.example .env
```

No Windows, o comando equivalente é:

```powershell
copy .env.example .env
```

O arquivo `.env` contém configurações e credenciais locais e não deve ser commitado.

## Configuração

As configurações usadas pela aplicação são:

| Variável | Descrição |
|---|---|
| `API_BASE_URL` | URL base da API consultada. Deve usar HTTP ou HTTPS. |
| `API_TOKEN` | Token enviado na autenticação das chamadas à API. |
| `REQUEST_TIMEOUT` | Tempo limite de cada chamada HTTP, em segundos. Deve ser maior que zero. |
| `MAX_ATTEMPTS` | Número máximo de tentativas para erros temporários. Deve ser um inteiro entre 1 e 3. |

Use os valores adequados ao seu ambiente. Não publique tokens ou outras credenciais.

## API simulada

Com o ambiente virtual ativo, inicie a API simulada em outro terminal:

```bash
uvicorn mock_api.app:app --host 127.0.0.1 --port 8000
```

Também é possível usar os scripts disponíveis em `scripts/`. Mais detalhes estão em [mock_api/README.md](mock_api/README.md).

## Execução

Na raiz do projeto, execute:

```bash
python -m src.main --input input/solicitacoes.csv --output output/resultado.csv
```

A execução gera:

- `output/resultado.csv`, com os resultados consolidados;
- `output/automation.log`, com os eventos do processamento;
- um resumo no terminal com o total e as quantidades por status.

O arquivo de log é criado no mesmo diretório do arquivo informado em `--output`.

## Validação e tratamento de erros

- Registros inválidos recebem o status `invalid` e não chamam a API.
- Respostas HTTP `429` e `5xx` recebem novas tentativas até o limite definido por `MAX_ATTEMPTS`.
- Respostas HTTP `400`, `401`, `403` e `404` não recebem novas tentativas.
- O status HTTP `404` gera o resultado `not_found`.
- Timeout, falha de conexão, JSON inválido e estrutura de resposta inesperada são tratados como resultados controlados.

## Testes

Execute a suíte automatizada com:

```bash
python -m pytest -v
```

Os testes usam mocks nas chamadas HTTP e não dependem da API simulada em execução.

## Entrega

O desenvolvimento deve ser feito em uma branch própria, seguindo o padrão:

```bash
git checkout -b candidate/seu-nome-sobrenome
```

Envie a branch e abra um Pull Request para a branch `main`. Não faça merge do Pull Request nem inclua o arquivo `.env` no repositório.
