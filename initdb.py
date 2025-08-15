import json
import sqlite3
import os

DB_FILE = "galaxyprospect.db"
CONFIG_FILE = "config.json"

def get_table_schema(symbols):
    # Always include datetime as primary key
    fields = ["date datetime PRIMARY KEY"]
    for sym in symbols:
        fname = sym.get("field_name")
        if fname:
            fields.append(f'"{fname}" REAL')
    return f"CREATE TABLE IF NOT EXISTS fact ({', '.join(fields)})"

def main():
    if not os.path.exists(CONFIG_FILE):
        print(f"Config file {CONFIG_FILE} not found.")
        return
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    symbols = config.get("symbols", [])
    schema_sql = get_table_schema(symbols)
    print("Creating table with schema:")
    print(schema_sql)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"DROP TABLE IF EXISTS fact")
    c.execute(schema_sql)
    conn.commit()
    conn.close()
    print(f"Table 'fact' created in {DB_FILE}.")

if __name__ == "__main__":
    main()
