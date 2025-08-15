import json
import sqlite3
from datetime import datetime
import re

DB_FILE = "galaxyprospect.db"
HOTEL_JSON = "hotel_data_mo.json"  # or your hotel data JSON file
FIELD_NAME = "DSEC_hotel"
TABLE_NAME = "fact"

# Helper to normalize date to YYYY-MM-DD
def normalize_date(ref):
    ref = str(ref)
    if re.fullmatch(r"\d{4}", ref):
        return f"{ref}-01-01"
    m = re.match(r"(\d{4})[-/](\d{1,2})", ref)
    if m:
        year, month = m.groups()
        return f"{year}-{int(month):02d}-01"
    m = re.match(r"([A-Za-z]{3,})\.?/?(\d{4})", ref)
    if m:
        month_str, year = m.groups()
        try:
            month = datetime.strptime(month_str[:3], "%b").month
            return f"{year}-{month:02d}-01"
        except Exception:
            pass
    return ref

def main():
    with open(HOTEL_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for entry in data:
        dt = normalize_date(entry.get("date", ""))
        val = entry.get("value")
        # Upsert: insert or update the DSEC_hotel field for this datetime
        c.execute(f"SELECT 1 FROM {TABLE_NAME} WHERE datetime = ?", (dt,))
        if c.fetchone():
            c.execute(f"UPDATE {TABLE_NAME} SET {FIELD_NAME} = ? WHERE datetime = ?", (val, dt))
        else:
            c.execute(f"INSERT INTO {TABLE_NAME} (datetime, {FIELD_NAME}) VALUES (?, ?)", (dt, val))
    conn.commit()
    conn.close()
    print(f"Loaded {len(data)} rows into {TABLE_NAME}.{FIELD_NAME}")

if __name__ == "__main__":
    main()
