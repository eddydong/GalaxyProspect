

import json
import requests
import re
from datetime import datetime

from pymongo import MongoClient
from pymongo import MongoClient


# GGR API
GGR_API_URL = "https://www.dsec.gov.mo/TimeSeriesApi/App/IndicatorValue/LatestSameEndPeriodv3"
GGR_PAYLOAD = {
    "indicator_ids": [1216],  # GGR
    "language": "en-US",
    "types": ["VAL"],
    "dataPeriods": ["monthly"],
    "fromYear": 2002,
    "toYear": 2025
}

# Hotel and visitation indicators
INDICATORS = [
    {"url": "https://www.dsec.gov.mo/TimeSeriesApi/App/KeyIndicatorv3/1/en-US/245", "field": "DSEC_hotel"},
    {"url": "https://www.dsec.gov.mo/TimeSeriesApi/App/KeyIndicatorv3/1/en-US/243", "field": "DSEC_visitation"},
]

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

    # --- Fetch GGR ---
    print("Posting to:", GGR_API_URL)
    print("Payload:", json.dumps(GGR_PAYLOAD, indent=2))
    response = requests.post(GGR_API_URL, json=GGR_PAYLOAD)
    print("Status code:", response.status_code)
    ggr_data = {}
    try:
        data = response.json()
        for item in data.get("Value", []):
            for entry in item.get("dsecIndicatorData", []):
                ref = entry.get("ReferencePeriod", "")
                val = entry.get("IndicatorValue", "")
                date_str = normalize_date(ref)
                val_clean = clean_value(val)
                if val_clean is not None and date_str >= start_date:
                    ggr_data[date_str] = val_clean
    except Exception as e:
        print("Failed to parse/process GGR JSON:", e)
        print(response.text)
        ggr_data = {}

    # --- Fetch hotel and visitation ---
    def fetch_and_parse(api_url, field_name):
        resp = requests.get(api_url)
        resp.raise_for_status()
        data = resp.json()
        out = []
        try:
            indicator_values = data["Value"]["indicatorValues"][0]["dsecIndicatorData"]
            for entry in indicator_values:
                ref = entry.get("ReferencePeriod", "")
                date_obj = None
                ref_clean = re.sub(r"\./", "/", ref)
                ref_clean = re.sub(r"\.", "", ref_clean)
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
                val = entry.get("IndicatorValue", "")
                if isinstance(val, str):
                    val_clean = re.sub(r"[^0-9.\-]", "", val)
                    try:
                        val_clean = float(val_clean)
                    except Exception:
                        val_clean = None
                else:
                    val_clean = val
                if val_clean is not None:
                    out.append({"date": date_str, "value": val_clean})
        except Exception as e:
            print(f"Error extracting data for {field_name}:", e)
            out = []
        return out

    merged = {}
    # Add GGR data
    for dt, val in ggr_data.items():
        merged.setdefault(dt, {})["DSEC_ggr"] = val
    # Add hotel and visitation data
    for ind in INDICATORS:
        series = fetch_and_parse(ind["url"], ind["field"])
        for row in series:
            dt = row["date"]
            val = row["value"]
            if dt >= start_date:
                merged.setdefault(dt, {})[ind["field"]] = val

    # Save to MongoDB in unified 'daily_fact' collection, only updating relevant fields
    client = MongoClient('mongodb://localhost:27017/')
    db = client['MOWATCH']
    collection = db['daily_fact']
    count = 0
    for dt, data_fields in merged.items():
        wrapped = {f"data.{k}": {"value": v} for k, v in data_fields.items()}
        collection.update_one(
            {"_id": dt},
            {"$set": wrapped},
            upsert=True
        )
        count += 1
    print(f"Loaded {count} rows into MongoDB 'daily_fact' collection (date as _id, merged fields only).")

if __name__ == "__main__":
    fetch_and_save()
