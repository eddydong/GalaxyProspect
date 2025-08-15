import json
import requests
import re
from datetime import datetime
import sqlite3
import os

API_URL = "https://www.dsec.gov.mo/TimeSeriesApi/App/IndicatorValue/LatestSameEndPeriodv3"

payload = {
    "indicator_ids": [1216],
    "language": "en-US",
    "types": ["VAL"],
    "dataPeriods": ["monthly"],
    "fromYear": 2002,
    "toYear": 2025
}

DB_FILE = "galaxyprospect.db"
TABLE_NAME = "ggr_data"

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

def clean_value(val):
    if isinstance(val, str):
        val_clean = re.sub(r"[^0-9.\-]", "", val)
        try:
            val_clean = float(val_clean)
        except Exception:
            val_clean = None
    else:
        val_clean = val
    return val_clean

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            GGR REAL NOT NULL
        )
    """)
    conn.commit()
    return conn

def insert_data(conn, data):
    c = conn.cursor()
    c.executemany(f"INSERT INTO {TABLE_NAME} (date, GGR) VALUES (?, ?)", data)
    conn.commit()

def fetch_and_save():
    print("Posting to:", API_URL)
    print("Payload:", json.dumps(payload, indent=2))
    response = requests.post(API_URL, json=payload)
    print("Status code:", response.status_code)
    try:
        data = response.json()
        out = []
        for item in data.get("Value", []):
            for entry in item.get("dsecIndicatorData", []):
                ref = entry.get("ReferencePeriod", "")
                val = entry.get("IndicatorValue", "")
                date_str = normalize_date(ref)
                val_clean = clean_value(val)
                if val_clean is not None:
                    out.append((date_str, val_clean))
        if out:
            conn = init_db()
            insert_data(conn, out)
            conn.close()
            print(f"Saved {len(out)} rows to {DB_FILE} in table {TABLE_NAME}")
        else:
            print("No valid data to save.")
    except Exception as e:
        print("Failed to parse/process JSON:", e)
        print(response.text)

if __name__ == "__main__":
    fetch_and_save()
