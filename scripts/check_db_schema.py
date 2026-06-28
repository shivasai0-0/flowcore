import sqlite3
from src.database import engine
from src.models import Base
from sqlalchemy import inspect

def check_schema():
    inspector = inspect(engine)
    db_tables = inspector.get_table_names()
    print("Database tables:", db_tables)

    for model in Base.__subclasses__():
        table_name = model.__tablename__
        if table_name not in db_tables:
            print(f"Table '{table_name}' is missing from DB!")
            continue

        model_columns = {c.name: c for c in model.__table__.columns}
        db_columns = {c['name']: c for c in inspector.get_columns(table_name)}

        missing_in_db = set(model_columns.keys()) - set(db_columns.keys())
        if missing_in_db:
            print(f"Table '{table_name}' is missing columns in DB: {missing_in_db}")
            for col_name in missing_in_db:
                col = model_columns[col_name]
                # Determine type string for SQLite
                col_type = "TEXT"
                if "INTEGER" in str(col.type).upper():
                    col_type = "INTEGER"
                elif "BOOLEAN" in str(col.type).upper():
                    col_type = "INTEGER"
                elif "DATETIME" in str(col.type).upper():
                    col_type = "TIMESTAMP"
                
                default_clause = ""
                if col.default is not None:
                    # simplistic default check
                    default_clause = " DEFAULT 0"
                
                alter_query = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}{default_clause}"
                print(f"Running alter query: {alter_query}")
                with engine.begin() as conn:
                    conn.exec_driver_sql(alter_query)
        else:
            print(f"Table '{table_name}' schema matches model!")

if __name__ == "__main__":
    check_schema()
