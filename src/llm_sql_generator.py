import logging
import os
import re
from dataclasses import dataclass
from typing import Any

import openai
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)


class SqlGenerationError(Exception):
    """Erro ao gerar SQL a partir de linguagem natural."""


class SqlValidationError(Exception):
    """Erro de validação na SQL gerada."""


@dataclass(frozen=True, slots=True)
class SqlGenerationResult:
    """Resultado estruturado com SQL final e plano textual."""

    sql: str
    plan: str


class SqlGenerationResponse(BaseModel):
    """Modelo para parsing da resposta estruturada do LLM."""

    plan: str
    sql: str


@dataclass(frozen=True, slots=True, kw_only=True)
class LlmSqlGeneratorConfig:
    """Configuração para o gerador de SQL via LLM.

    Exemplo de uso básico:

        from src.schema_inspector import get_schema_representation
        from src.llm_sql_generator import LlmSqlGenerator, LlmSqlGeneratorConfig

        schema = get_schema_representation()
        config = LlmSqlGeneratorConfig(
            model="gpt-4.1-mini",
            db_url="sqlite:///chinook.db",
            temperature=0.0,
            timeout=20.0,
        )
        generator = LlmSqlGenerator(config)
        sql = generator.generate_sql("Qual cidade mais compra meus produtos?", schema)
    """

    model: str = "gpt-4.1-mini"
    db_url: str | None = "sqlite:///chinook.db"
    temperature: float = 0.0
    timeout: float = 20.0
    default_limit: int = 50


class LlmSqlGenerator:
    """Gera consultas SQL a partir de linguagem natural usando a API da OpenAI.

    Regras principais:
    - Gera exclusivamente consultas SELECT.
    - Nunca modifica dados (sem INSERT, UPDATE, DELETE, etc.).
    - Utiliza apenas tabelas e colunas presentes no schema fornecido.
    - Em caso de schema insuficiente, retorna o token INSUFFICIENT_SCHEMA.

    A chave da API deve ser configurada via variável de ambiente OPENAI_API_KEY.
    """

    def __init__(
        self,
        config: LlmSqlGeneratorConfig | None = None,
        logger_instance: logging.Logger | None = None,
        client: OpenAI | None = None,
    ) -> None:
        self._config = config or LlmSqlGeneratorConfig()
        self._logger = logger_instance or logger

        api_key = os.environ.get("OPENAI_API_KEY")
        self._client = client or OpenAI(api_key=api_key)

        self._engine = None
        if self._config.db_url:
            self._engine = create_engine(self._config.db_url, future=True)

    def generate_sql(self, question: str, schema: str) -> SqlGenerationResult:
        """Gera uma consulta SQL SELECT e um plano textual a partir de linguagem natural."""
        if not question:
            raise ValueError("A pergunta em linguagem natural não pode ser vazia.")

        if not schema:
            raise ValueError("O schema do banco de dados não pode ser vazio.")

        self._logger.info("Gerando SQL a partir de pergunta em linguagem natural.")
        prompt = self._build_prompt(question, schema)

        try:
            raw_response = self._call_openai(prompt)
        except Exception as exc:  # noqa: BLE001
            self._logger.error("Falha ao chamar a API da OpenAI.", exc_info=True)
            raise SqlGenerationError("Falha ao chamar a API da OpenAI.") from exc

        structured = self._parse_structured_response(raw_response)
        sql = structured.sql
        plan = structured.plan
        self._logger.debug("SQL bruta retornada pelo modelo: %s", sql)

        if sql.strip() == "INSUFFICIENT_SCHEMA":
            self._logger.warning("Modelo retornou INSUFFICIENT_SCHEMA.")
            return SqlGenerationResult(sql="INSUFFICIENT_SCHEMA", plan=plan)

        sql = self._ensure_limit_clause(sql)

        try:
            self._validate_select_only(sql)
            if self._engine is not None:
                self._validate_with_database(sql)
        except SqlValidationError:
            self._logger.error("SQL gerada foi reprovada na validação: %s", sql)
            raise

        self._logger.info("SQL gerada com sucesso.")
        return SqlGenerationResult(sql=sql, plan=plan)

    def _build_prompt(self, question: str, schema: str) -> str:
        return (
            "You are an expert SQL generator for a SQLite database.\n\n"  # noqa: S608
            "<Rules>\n"
            "- Only generate SELECT queries.\n"
            "- Never modify data.\n"
            "- Do not use INSERT, UPDATE, DELETE, CREATE, DROP, ALTER or TRUNCATE.\n"
            "- Use only tables and columns from the schema below.\n"
            "- If the schema is insufficient to answer, respond with exactly: "
            "INSUFFICIENT_SCHEMA.\n"
            "- Return only the SQL query, without commentary or explanation.\n"
            "</Rules>\n\n"
            "<Schema>\n"
            f"{schema}\n"
            "</Schema>\n\n"
            "<Question>\n"
            f"{question}\n"
            "</Question>\n"
        )

    def _call_openai(self, prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a careful assistant that generates only "
                            "safe, read-only SQL."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self._config.temperature,
                timeout=self._config.timeout,
                response_format=self._structured_response_format(),
            )
        except (
            openai.APIError,
            openai.APIConnectionError,
            openai.RateLimitError,
            openai.AuthenticationError,
            openai.BadRequestError,
        ) as exc:
            self._logger.error("Erro na chamada da API da OpenAI.", exc_info=True)
            raise SqlGenerationError("Erro na API da OpenAI.") from exc

        choice = response.choices[0]
        content = choice.message.content or ""
        return content

    def _structured_response_format(self) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "sql_generation_response",
                "schema": {
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "string",
                            "description": (
                                "Lista numerada descrevendo as etapas para montar a consulta."
                            ),
                        },
                        "sql": {
                            "type": "string",
                            "description": "Consulta SQL final, apenas SELECT.",
                        },
                    },
                    "required": ["plan", "sql"],
                    "additionalProperties": False,
                },
            },
        }

    def _parse_structured_response(self, raw_response: str) -> SqlGenerationResponse:
        try:
            return SqlGenerationResponse.model_validate_json(raw_response)
        except PydanticValidationError as exc:  # pragma: no cover - proteção extra
            self._logger.error(
                "Resposta do modelo fora do formato esperado:
 %s", raw_response, exc_info=True
            )
            raise SqlGenerationError("Resposta do modelo fora do formato esperado.") from exc

    def _validate_select_only(self, sql: str) -> None:
        cleaned = self._strip_literals_and_comments(sql)
        stripped = cleaned.lstrip()

        if not stripped.lower().startswith("select"):
            raise SqlValidationError("A consulta gerada não é um SELECT.")

        lower_sql = stripped.lower()
        forbidden_keywords = [
            "insert",
            "update",
            "delete",
            "drop",
            "alter",
            "truncate",
            "create",
        ]
        for keyword in forbidden_keywords:
            if re.search(rf"\b{keyword}\b", lower_sql):
                raise SqlValidationError(
                    "A consulta gerada contém operações de modificação de dados ou DDL proibidas."
                )

    def _strip_literals_and_comments(self, sql: str) -> str:
        without_block_comments = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
        without_line_comments = re.sub(r"--.*?$", "", without_block_comments, flags=re.MULTILINE)
        no_single_quotes = re.sub(r"'([^']|'')*'", "''", without_line_comments, flags=re.DOTALL)
        no_double_quotes = re.sub(r'"([^"]|"")*"', '""', no_single_quotes, flags=re.DOTALL)
        return no_double_quotes

    def _ensure_limit_clause(self, sql: str) -> str:
        sanitized = self._strip_literals_and_comments(sql)
        if re.search(r"\blimit\b", sanitized, flags=re.IGNORECASE):
            return sql

        stripped_sql = sql.rstrip()
        has_semicolon = stripped_sql.endswith(";")
        if has_semicolon:
            stripped_sql = stripped_sql[:-1].rstrip()

        separator = "\n" if "\n" in stripped_sql else " "
        limited_sql = f"{stripped_sql}{separator}LIMIT {self._config.default_limit}"

        if has_semicolon:
            limited_sql += ";"

        return limited_sql

    def _validate_with_database(self, sql: str) -> None:
        if self._engine is None:
            return

        try:
            with self._engine.connect() as connection:
                connection.exec_driver_sql("EXPLAIN " + sql)
        except SQLAlchemyError as exc:
            self._logger.error("Falha ao validar a SQL gerada no banco de dados.", exc_info=True)
            raise SqlValidationError("A SQL gerada é inválida para o banco de dados.") from exc


def generate_sql(question: str, schema: str) -> str:
    """Função de conveniência para geração de SQL usando configuração padrão."""
    generator = LlmSqlGenerator()
    return generator.generate_sql(question, schema)
