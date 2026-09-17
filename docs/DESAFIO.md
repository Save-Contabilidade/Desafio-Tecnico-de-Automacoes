# Desafio Técnico — Automação de Consulta de Documentos

## Cenário

A Save Contabilidade precisa processar uma fila de solicitações de consulta de documentos fiscais.

Cada solicitação contém dados de uma empresa, UF, tipo de documento e competência. Sua tarefa é criar uma automação em Python que leia essas solicitações, valide os dados, consulte uma API e gere um arquivo consolidado com o resultado.

A API utilizada neste desafio é simulada e está disponível na pasta `mock_api`.

---

## Entrada

O arquivo de entrada está em:

```text
input/solicitacoes.csv
```

Colunas disponíveis:

| Campo | Descrição |
|---|---|
| `request_id` | Identificador único da solicitação |
| `company_name` | Nome da empresa |
| `cnpj` | CNPJ da empresa |
| `uf` | UF da consulta |
| `document_type` | Tipo do documento |
| `competence` | Competência no formato `YYYY-MM` |

Tipos de documento aceitos:

```text
NFE
NFCE
NFSE
CTE
MDFE
```

---

## Objetivo

Crie uma aplicação em Python que:

1. Leia `input/solicitacoes.csv`.
2. Valide os registros antes de chamar a API.
3. Consulte a API para cada registro válido.
4. Trate respostas de sucesso e erro.
5. Implemente retentativas para erros temporários.
6. Gere um CSV consolidado com os resultados.
7. Gere logs da execução.
8. Apresente um resumo ao final da execução.

---

## Validações mínimas

Considere inválido um registro que apresente pelo menos uma das condições abaixo:

- `request_id` vazio;
- CNPJ sem 14 dígitos numéricos após remover pontuação;
- UF inexistente;
- `document_type` diferente dos tipos permitidos;
- competência fora do padrão `YYYY-MM`.

Registros inválidos **não devem chamar a API**.

Não é obrigatório validar o dígito verificador real do CNPJ.

---

## API

Configure a URL e o token através de variáveis de ambiente:

```env
API_BASE_URL=http://127.0.0.1:8000
API_TOKEN=desafio-local-token
```

Endpoint:

```text
POST /v1/documents/query
```

Header obrigatório:

```text
Authorization: Bearer <API_TOKEN>
```

Payload esperado:

```json
{
  "request_id": "REQ-001",
  "cnpj": "11111111000111",
  "uf": "SC",
  "document_type": "NFE",
  "competence": "2026-08"
}
```

Exemplo de sucesso:

```json
{
  "request_id": "REQ-001",
  "status": "success",
  "document_count": 2,
  "message": "Consulta concluída"
}
```

---

## Tratamento de erros

Sua solução deve lidar corretamente com:

- timeout de conexão;
- HTTP `429`;
- HTTP `5xx`;
- HTTP `4xx` não temporário;
- resposta JSON inválida ou inesperada.

### Retentativas

Para HTTP `429` ou HTTP `5xx`, realize no máximo **3 tentativas no total**.

Utilize algum intervalo entre as tentativas. Backoff exponencial é recomendado, mas não obrigatório.

Não faça retentativa para `400`, `401`, `403` ou `404`.

---

## Saída

A aplicação deverá gerar:

```text
output/resultado.csv
```

Com, no mínimo, as seguintes colunas:

| Campo | Descrição |
|---|---|
| `request_id` | Identificador da solicitação |
| `status` | Resultado final |
| `http_status` | Status HTTP, quando aplicável |
| `attempts` | Quantidade de tentativas realizadas |
| `message` | Mensagem descritiva |
| `document_count` | Quantidade retornada pela API, quando aplicável |
| `processed_at` | Data/hora do processamento |

Status sugeridos:

```text
success
not_found
invalid
error
```

A automação também deverá gerar:

```text
output/automation.log
```

---

## Execução esperada

Sua solução deve utilizar o seguinte ponto de entrada:


```bash
python -m src.main --input input/solicitacoes.csv --output output/resultado.csv
```

Esse comando será utilizado nos testes da entrega. A organização interna dos módulos permanece livre.

---

## Requisitos técnicos

Obrigatórios:

- Python 3.11 ou superior;
- código organizado em módulos;
- variáveis de ambiente para configurações e credenciais;
- tratamento de exceções;
- logs;
- `requirements.txt` atualizado;
- documentação de execução;
- commits durante o desenvolvimento.

Desejáveis:

- type hints;
- testes automatizados;
- separação entre leitura, validação, integração e escrita;
- uso de `pathlib`;
- timeout explícito nas chamadas HTTP;
- boa organização de funções/classes;
- idempotência;
- execução concorrente, se bem justificada.

---

## Resumo da execução

Ao final, apresente no terminal um resumo semelhante a:

```text
Processamento concluído
Total: 6
Sucesso: 3
Não encontrados: 1
Inválidos: 1
Erros: 1
```

O formato exato é livre.

---

## Liberdade de implementação

Você pode alterar a estrutura interna da pasta `src`, adicionar bibliotecas e criar novos arquivos.

Evite alterar:

- `input/solicitacoes.csv`;
- comportamento da API simulada;
- requisitos mínimos deste documento.

---

## Uso de Inteligência Artificial

Ferramentas de IA podem ser utilizadas como apoio.

Entretanto, durante a avaliação, o candidato deverá ser capaz de:

- explicar o código entregue;
- justificar decisões técnicas;
- identificar problemas;
- realizar pequenas alterações na solução;
- explicar como tratou erros e retentativas.
