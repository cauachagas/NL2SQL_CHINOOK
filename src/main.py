from schema_inspector import get_schema_representation
from llm_sql_generator import LlmSqlGenerator, LlmSqlGeneratorConfig
from dotenv import load_dotenv

load_dotenv()

def main():
    schema = get_schema_representation(db_path="chinook.db")

    config = LlmSqlGeneratorConfig(
        model="gpt-4.1-mini",
        db_url="sqlite:///chinook.db",
        temperature=0.0,
        timeout=20.0,
    )

    generator = LlmSqlGenerator(config=config)

    question = (
        "Identifique os 10 clientes com os maiores volumes de gastos totais, "
        "incluindo o número de transações."
    )
    # question = "Determine os 10 países com a maior receita total, incluindo o número de vendas."
    sql = generator.generate_sql(question, schema)

    print(sql)


if __name__ == "__main__":
    main()
