

import json
import re
from datetime import datetime
import requests
import sqlite3

# Indicator Lookup (Travel & Services)
# https://www.dsec.gov.mo/TimeSeriesApi/App/Indicatorv3/1503

# hotel occupancy
# https://www.dsec.gov.mo/TimeSeriesApi/App/KeyIndicatorv3/1/en-US/245
# visitation
# https://www.dsec.gov.mo/TimeSeriesApi/App/KeyIndicatorv3/1/en-US/243



DB_FILE = "galaxyprospect.db"
TABLE_NAME = "fact"

INDICATORS = [
    {"url": "https://www.dsec.gov.mo/TimeSeriesApi/App/KeyIndicatorv3/1/en-US/245", "field": "DSEC_hotel"},
    {"url": "https://www.dsec.gov.mo/TimeSeriesApi/App/KeyIndicatorv3/1/en-US/243", "field": "DSEC_visitation"},
]



def fetch_and_parse(api_url, field_name):
    resp = requests.get(api_url)
    resp.raise_for_status()
    data = resp.json()
    out = []
    try:
        indicator_values = data["Value"]["indicatorValues"][0]["dsecIndicatorData"]
        for entry in indicator_values:
            # --- Date normalization ---
            ref = entry.get("ReferencePeriod", "")
            date_obj = None
            # Try to parse date like 'Jan./2025', 'May/2025', etc.
            # Remove trailing dot in month if present
            ref_clean = re.sub(r"\./", "/", ref)
            ref_clean = re.sub(r"\.", "", ref_clean)
            # Try to parse with first 3 letters as month
            try:
                parts = re.split(r"[./ ]", ref_clean)
                if len(parts) >= 2:
                    date_obj = datetime.strptime(parts[0][:3] + "/" + parts[-1], "%b/%Y")
            except Exception:
                date_obj = None
            if date_obj:
                date_str = date_obj.strftime("%Y-%m-01")
            else:
                date_str = ref  # fallback to original

            # --- Value cleaning ---
            val = entry.get("IndicatorValue", "")
            # Remove any non-numeric except dot and minus
            if isinstance(val, str):
                val_clean = re.sub(r"[^0-9.\-]", "", val)
                try:
                    val_clean = float(val_clean)
                except Exception:
                    val_clean = None
            else:
                val_clean = val

            if val_clean is not None:
                out.append({
                    "date": date_str,
                    "value": val_clean
                })
    except Exception as e:
        print(f"Error extracting data for {field_name}:", e)
        out = []
    return out


def main():
    # Load startDate from config.json
    with open('config.json', 'r') as f:
        config = json.load(f)
    start_date = config.get('startDate', '2000-01-01')

    # Fetch and merge both series
    all_data = {}
    for ind in INDICATORS:
        series = fetch_and_parse(ind["url"], ind["field"])
        for row in series:
            dt = row["date"]
            val = row["value"]
            if dt >= start_date:
                if dt not in all_data:
                    all_data[dt] = {}
                all_data[dt][ind["field"]] = val

    # Save to DB
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for dt, fields in all_data.items():
        # Check if row exists
        c.execute(f"SELECT 1 FROM {TABLE_NAME} WHERE date = ?", (dt,))
        if c.fetchone():
            # Update only the fields present
            for field, val in fields.items():
                c.execute(f"UPDATE {TABLE_NAME} SET {field} = ? WHERE date = ?", (val, dt))
        else:
            # Insert with all available fields
            columns = ["date"] + list(fields.keys())
            placeholders = ["?"] * len(columns)
            values = [dt] + [fields[f] for f in fields]
            c.execute(f"INSERT INTO {TABLE_NAME} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})", values)
    conn.commit()
    conn.close()
    print(f"Loaded {len(all_data)} rows into {TABLE_NAME} for hotel and visitation (from {start_date} onward).")

if __name__ == "__main__":
    main()
