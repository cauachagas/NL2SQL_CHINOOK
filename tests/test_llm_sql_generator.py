import os
import textwrap
import unittest

from sqlalchemy import create_engine, text

from src.llm_sql_generator import LlmSqlGenerator, LlmSqlGeneratorConfig
from src.schema_inspector import get_schema_representation


def _fetch_rows(engine, raw_sql: str) -> list[tuple]:
    with engine.connect() as connection:
        result = connection.execute(text(raw_sql))
        return [tuple(row) for row in result]


@unittest.skipUnless(os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY não configurada")
class TestLlmSqlGeneratorIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db_path = os.getenv("CHINOOK_DB_PATH", "chinook.db")
        if not os.path.exists(db_path):
            raise unittest.SkipTest("Banco chinook.db não encontrado na raiz do projeto.")

        cls.schema = get_schema_representation(db_path=db_path)
        cls.engine = create_engine(f"sqlite:///{db_path}")
        cls.generator = LlmSqlGenerator(
            config=LlmSqlGeneratorConfig(
                model="gpt-4.1-mini",
                db_url=f"sqlite:///{db_path}",
                temperature=0.0,
                timeout=20.0,
            )
        )

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "engine"):
            cls.engine.dispose()

    def test_generate_sql_top_spending_customers(self) -> None:
        reference_sql = textwrap.dedent(
            """
            SELECT
                c.CustomerId,
                c.FirstName,
                c.LastName,
                SUM(i.Total) AS TotalSpent,
                COUNT(i.InvoiceId) AS NumberOfTransactions
            FROM customers c
            JOIN invoices i ON c.CustomerId = i.CustomerId
            GROUP BY c.CustomerId, c.FirstName, c.LastName
            ORDER BY TotalSpent DESC
            LIMIT 10;
            """
        ).strip()

        question = (
            "Identifique os 10 clientes com os maiores volumes de gastos totais, "
            "incluindo o número de transações."
        )

        generated_sql = self.generator.generate_sql(question, self.schema)
        self.assertListEqual(
            _fetch_rows(self.engine, generated_sql),
            _fetch_rows(self.engine, reference_sql),
        )

    def test_generate_sql_top_countries_by_revenue(self) -> None:
        reference_sql = textwrap.dedent(
            """
            SELECT
                BillingCountry AS Country,
                COUNT(InvoiceId) AS NumberOfSales,
                SUM(Total) AS TotalRevenue
            FROM invoices
            GROUP BY BillingCountry
            ORDER BY TotalRevenue DESC
            LIMIT 10;
            """
        ).strip()

        question = (
            "Determine os 10 países com a maior receita total, incluindo o número de vendas."
        )

        generated_sql = self.generator.generate_sql(question, self.schema)
        self.assertListEqual(
            _fetch_rows(self.engine, generated_sql),
            _fetch_rows(self.engine, reference_sql),
        )


if __name__ == "__main__":
    unittest.main()
