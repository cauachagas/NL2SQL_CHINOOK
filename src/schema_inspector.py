def get_schema_representation(db_path="chinook.db"):
    from sqlalchemy import create_engine, inspect

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)

    schema_blocks = []

    for table_name in inspector.get_table_names():
        block = [f"Table: {table_name}", "Columns:"]

        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns = set(pk_constraint.get("constrained_columns", []))

        foreign_keys = inspector.get_foreign_keys(table_name)
        fk_map = {}
        for fk in foreign_keys:
            for col in fk["constrained_columns"]:
                fk_map[col] = (
                    f"{fk['referred_table']}.{','.join(fk['referred_columns'])}"
                )

        for column in columns:
            col_name = column["name"]
            line = f"- {col_name}"

            if col_name in pk_columns:
                line += " (PK)"

            if col_name in fk_map:
                line += f" (FK -> {fk_map[col_name]})"

            block.append(line)

        schema_blocks.append("\n".join(block))

    return "\n\n".join(schema_blocks)


if __name__ == "__main__":
    schema = get_schema_representation()
    print(schema)
