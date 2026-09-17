# API simulada

Esta pasta contém uma API local utilizada exclusivamente para o desafio.

Ela simula respostas de sucesso, registros não encontrados, rate limit (`429`) e erros temporários de servidor (`500`).

## Como iniciar

Na raiz do projeto, com o ambiente virtual ativado:

```bash
uvicorn mock_api.app:app --host 127.0.0.1 --port 8000
```

Ou utilize os scripts disponíveis em `scripts/`.

Depois, valide:

```text
GET http://127.0.0.1:8000/health
```

Resposta esperada:

```json
{
  "status": "ok"
}
```

## Token

Utilize o token definido no `.env.example`:

```text
desafio-local-token
```

## Observação

Não altere o comportamento desta API como parte da solução do desafio.
