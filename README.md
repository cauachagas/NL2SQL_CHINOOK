# NL2SQL Chinook

Projeto em Python que converte perguntas em linguagem natural em consultas SQL seguras para o banco `chinook.db`. A aplicação combina inspeção automática do schema com geração via LLM (OpenAI) e validações locais, permitindo explorar o dataset sem escrever SQL manualmente.

## Componentes principais

- **`src/schema_inspector.py`**: usa SQLAlchemy para refletir o banco, listar tabelas, colunas, chaves primárias e relacionamentos. A saída já vem formatada para ser incluída no prompt do LLM.
- **`src/llm_sql_generator.py`**: encapsula o fluxo de geração. Monta o prompt com regras restritivas (aliases/identificadores sempre em inglês, naming consistente para agregações), solicita _structured output_ (Pydantic) contendo plano + SQL, força `LIMIT` padrão quando ausente e aplica duas camadas de validação (somente `SELECT` e `EXPLAIN` no SQLite local).
- **`src/database_queries.py`**: consultas analíticas prontas (top clientes, países e artistas) implementadas com ORM para servir de baseline e para depuração rápida.
- **`src/main.py`**: orquestra o processo; carrega variáveis de ambiente, lê o schema e solicita ao LLM uma SQL para a pergunta configurada.

## Fluxo atual

1. `dotenv` carrega `OPENAI_API_KEY` e demais variáveis.
2. `get_schema_representation()` coleta o schema do `chinook.db` (precisa estar na raiz do projeto).
3. `LlmSqlGenerator` cria o prompt com regras de segurança (SELECT-only, aliases em inglês, limites) e chama a API da OpenAI pedindo um JSON com `plan` + `sql`.
4. A SQL é saneada, recebe `LIMIT` (caso ausente), validada como somente leitura, executada com `EXPLAIN` e retorna junto ao plano estruturado para depuração.
5. `src/main.py` exibe o plano textual numerado e a SQL final pronta para execução manual ou integração posterior.

## Pré-requisitos

- Python 3.12+
- Arquivo `chinook.db` disponível na raiz do repositório
- Variável `OPENAI_API_KEY` definida (ou `.env` com a chave)
- Dependências instaladas: `pip install -e .` ou `pip install -r <arquivo>` equivalente (inclui `pydantic`, `sqlalchemy`, `openai`)
- Opcional: Ruff para lint/format (já configurado em `pyproject.toml`)

## Como executar

```bash
pip install -e .
export OPENAI_API_KEY="sua-chave"
python -m src.main
```

- Edite a variável `question` em `src/main.py` para testar novos cenários.
- Ajuste `LlmSqlGeneratorConfig` conforme necessário (`model`, `temperature`, `db_url`).

## Consultas analíticas prontas

Para validar respostas do modelo ou criar dashboards rápidos, execute `src/database_queries.py`. Ele expõe funções como `get_top_10_spending_customers()` e imprime rankings quando chamado diretamente (`python src/database_queries.py`).

## Testes

- `tests/test_llm_sql_generator.py` executa testes de integração reais: roda a pergunta contra o LLM, executa a SQL resultante no `chinook.db` e compara com uma consulta referência. Por depender da API, os testes só rodam quando `OPENAI_API_KEY` e o banco estão presentes.
	- Asserções comparam o resultado tabular (não apenas a string SQL), tolerando mudanças de ordem de colunas e garantindo que o plano textual não venha vazio.

## Próximos passos sugeridos

1. Criar interface CLI/HTTP para enviar perguntas dinamicamente.
2. Persistir histórico de perguntas/SQLs e planos para auditoria.
3. Expandir os testes atuais para cobrir cenários adicionais (joins múltiplos, filtros complexos) e comparar também metadados como schema das colunas.
4. Automatizar execução das consultas retornadas e devolver resultados tabulares pela aplicação (não apenas manualmente).
5. Publicar exemplos de prompts/respostas + planos no README para facilitar onboarding.

