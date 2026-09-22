# Desafio Técnico de Automações

Este repositório contém o desafio técnico para a vaga de **Desenvolvedor de Automações** da Save Contabilidade.

O objetivo é avaliar raciocínio, organização, uso de Git, integração com API, tratamento de erros, logs, testes e documentação.

## Antes de começar

Clone o repositório:

```bash
git clone https://github.com/Save-Contabilidade/Desafio-Tecnico-de-Automacoes.git
cd Desafio-Tecnico-de-Automacoes
```

Crie uma branch usando o padrão:

```bash
git checkout -b candidate/seu-nome-sobrenome
```

Exemplo:

```bash
git checkout -b candidate/joao-silva
```

> Não faça alterações diretamente na branch `main`.

## Desafio

Leia as instruções completas em:

- [docs/DESAFIO.md](docs/DESAFIO.md)
- [docs/CRITERIOS_AVALIACAO.md](docs/CRITERIOS_AVALIACAO.md)

## Configuração rápida

Crie um ambiente virtual:

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Instale as dependências iniciais:

```bash
pip install -r requirements.txt
```

Copie as variáveis de ambiente:

Windows:

```powershell
copy .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Inicie a API simulada conforme as instruções em [mock_api/README.md](mock_api/README.md).

## Entrega

Faça commits durante o desenvolvimento. Exemplos:

```bash
git add .
git commit -m "feat: implementa processamento inicial"
git commit -m "fix: adiciona retentativas para erros temporarios"
git commit -m "docs: atualiza instrucoes de execucao"
```

Envie sua branch:

```bash
git push origin candidate/seu-nome-sobrenome
```

Depois, abra um **Pull Request** para a branch `main`.

### Importante

- Não faça merge do Pull Request.
- Não faça commit do arquivo `.env`.
- Não altere ou remova os arquivos de entrada fornecidos.
- O código deverá funcionar em uma instalação limpa.
- Poderão existir testes adicionais não disponíveis neste repositório.

Boa sorte!

## Solução do candidato

A documentação da solução (execução, configuração, validações, tratamento de
erros e testes) está em [docs/SOLUCAO.md](docs/SOLUCAO.md).

```bash
python -m src.main --input input/solicitacoes.csv --output output/resultado.csv
pytest
```
