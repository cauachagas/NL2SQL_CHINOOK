# NL2SQL Chinook

Projeto em Python que converte perguntas em linguagem natural em consultas SQL seguras para o banco `chinook.db`. A aplicação combina inspeção automática do schema com geração via LLM (OpenAI) e validações locais, permitindo explorar o dataset sem escrever SQL manualmente.

## Componentes principais

- **`src/schema_inspector.py`**: usa SQLAlchemy para refletir o banco, listar tabelas, colunas, chaves primárias e relacionamentos. A saída já vem formatada para ser incluída no prompt do LLM.
- **`src/llm_sql_generator.py`**: encapsula o fluxo de geração. Monta o prompt com regras restritivas, chama o modelo (`gpt-4.1-mini` por padrão), extrai apenas o SQL e aplica duas camadas de validação (somente `SELECT` e `EXPLAIN` no SQLite local).
- **`src/database_queries.py`**: consultas analíticas prontas (top clientes, países e artistas) implementadas com ORM para servir de baseline e para depuração rápida.
- **`src/main.py`**: orquestra o processo; carrega variáveis de ambiente, lê o schema e solicita ao LLM uma SQL para a pergunta configurada.

## Fluxo atual

1. `dotenv` carrega `OPENAI_API_KEY` e demais variáveis.
2. `get_schema_representation()` coleta o schema do `chinook.db` (precisa estar na raiz do projeto).
3. `LlmSqlGenerator` cria o prompt com regras de segurança e chama a API da OpenAI.
4. O SQL retornado é higienizado, garantido como `SELECT` e validado via `EXPLAIN` no SQLite local.
5. O resultado final é impresso no terminal para posterior execução.

## Pré-requisitos

- Python 3.12+
- Arquivo `chinook.db` disponível na raiz do repositório
- Variável `OPENAI_API_KEY` definida (ou `.env` com a chave)
- Dependências instaladas: `pip install -e .` ou `pip install -r <arquivo>` equivalente
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

## Próximos passos sugeridos

1. Criar interface CLI/HTTP para enviar perguntas dinamicamente.
2. Persistir histórico de perguntas/SQLs para auditoria.
3. Adicionar testes integrados cobrindo `LlmSqlGenerator.generate_sql` com mocks do cliente.
4. Automatizar execução das consultas retornadas e devolver resultados tabulares.
5. Publicar exemplos de prompts/respostas no README para facilitar onboarding.

