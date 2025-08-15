

import json
import requests
import re
from datetime import datetime
import sqlite3

API_URL = "https://www.dsec.gov.mo/TimeSeriesApi/App/IndicatorValue/LatestSameEndPeriodv3"

# Example payload (replace with real indicator IDs and types as needed)
payload = {
    "indicator_ids": [1216],  # GGR
    "language": "en-US",
    "types": ["VAL"],
    "dataPeriods": ["monthly"],
    "fromYear": 2002,
    "toYear": 2025
}

DB_FILE = "galaxyprospect.db"
TABLE_NAME = "fact"
FIELD_NAME = "DSEC_ggr"

def normalize_date(ref):
    ref = str(ref)
    # If it's a year (e.g., '2023')
    if re.fullmatch(r"\d{4}", ref):
        return f"{ref}-01-01"
    # If it's a year/month (e.g., '2023-05' or '2023/5')
    m = re.match(r"(\d{4})[-/](\d{1,2})", ref)
    if m:
        year, month = m.groups()
        return f"{year}-{int(month):02d}-01"
    # Try to parse month name (e.g., 'Jan./2025', 'Feb./2025', 'May/2025', etc.)
    m = re.match(r"([A-Za-z]{3,})\.?/?(\d{4})", ref)
    if m:
        month_str, year = m.groups()
        try:
            month = datetime.strptime(month_str[:3], "%b").month
            return f"{year}-{month:02d}-01"
        except Exception:
            pass
    return ref  # fallback

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


def fetch_and_save():
    # Load startDate from config.json
    with open('config.json', 'r') as f:
        config = json.load(f)
    start_date = config.get('startDate', '2000-01-01')

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
                if val_clean is not None and date_str >= start_date:
                    out.append({
                        "date": date_str,
                        "value": val_clean
                    })
        # Save to DB
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        for row in out:
            dt = row["date"]
            val = row["value"]
            c.execute(f"SELECT 1 FROM {TABLE_NAME} WHERE date = ?", (dt,))
            if c.fetchone():
                c.execute(f"UPDATE {TABLE_NAME} SET {FIELD_NAME} = ? WHERE date = ?", (val, dt))
            else:
                c.execute(f"INSERT INTO {TABLE_NAME} (date, {FIELD_NAME}) VALUES (?, ?)", (dt, val))
        conn.commit()
        conn.close()
        print(f"Loaded {len(out)} rows into {TABLE_NAME}.{FIELD_NAME} (from {start_date} onward)")
    except Exception as e:
        print("Failed to parse/process JSON:", e)
        print(response.text)

if __name__ == "__main__":
    fetch_and_save()
