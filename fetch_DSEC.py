import json
import requests
import re
from datetime import datetime

from pymongo import MongoClient
from pymongo import MongoClient

# To get all indicator symbols: https://www.dsec.gov.mo/TimeSeriesApi/App/Indicatorv3
# To get sub-tree for specific symbol: https://www.dsec.gov.mo/TimeSeriesApi/App/Indicatorv3?id=1050

# GGR API
GGR_API_URL = "https://www.dsec.gov.mo/TimeSeriesApi/App/IndicatorValue/LatestSameEndPeriodv3"
GGR_PAYLOAD = {
    "indicator_ids": [1051],  # GGR
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

def fetch_and_save_ggr():
    with open('config.json', 'r') as f:
        config = json.load(f)
    start_date = config.get('startDate', '2000-01-01')
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
    # Save to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['MOWATCH']
    collection = db['daily_fact']
    count = 0
    for dt, val in ggr_data.items():
        wrapped = {"data.DSEC_ggr": {"value": val}}
        collection.update_one(
            {"_id": dt},
            {"$set": wrapped},
            upsert=True
        )
        count += 1
    print(f"Loaded {count} GGR rows into MongoDB 'daily_fact' collection.")

def fetch_and_save_hotel():
    with open('config.json', 'r') as f:
        config = json.load(f)
    start_date = config.get('startDate', '2000-01-01')
    url = INDICATORS[0]["url"]
    field = INDICATORS[0]["field"]
    resp = requests.get(url)
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
                date_str = ref
            val = entry.get("IndicatorValue", "")
            if isinstance(val, str):
                val_clean = re.sub(r"[^0-9.\-]", "", val)
                try:
                    val_clean = float(val_clean)
                except Exception:
                    val_clean = None
            else:
                val_clean = val
            if val_clean is not None and date_str >= start_date:
                out.append({"date": date_str, "value": val_clean})
    except Exception as e:
        print(f"Error extracting data for {field}:", e)
        out = []
    # Save to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['MOWATCH']
    collection = db['daily_fact']
    count = 0
    for row in out:
        dt = row["date"]
        val = row["value"]
        wrapped = {f"data.{field}": {"value": val}}
        collection.update_one(
            {"_id": dt},
            {"$set": wrapped},
            upsert=True
        )
        count += 1
    print(f"Loaded {count} hotel rows into MongoDB 'daily_fact' collection.")

def fetch_and_save_visitation():
    with open('config.json', 'r') as f:
        config = json.load(f)
    start_date = config.get('startDate', '2000-01-01')
    url = INDICATORS[1]["url"]
    field = INDICATORS[1]["field"]
    resp = requests.get(url)
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
                date_str = ref
            val = entry.get("IndicatorValue", "")
            if isinstance(val, str):
                val_clean = re.sub(r"[^0-9.\-]", "", val)
                try:
                    val_clean = float(val_clean)
                except Exception:
                    val_clean = None
            else:
                val_clean = val
            if val_clean is not None and date_str >= start_date:
                out.append({"date": date_str, "value": val_clean})
    except Exception as e:
        print(f"Error extracting data for {field}:", e)
        out = []
    # Save to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['MOWATCH']
    collection = db['daily_fact']
    count = 0
    for row in out:
        dt = row["date"]
        val = row["value"]
        wrapped = {f"data.{field}": {"value": val}}
        collection.update_one(
            {"_id": dt},
            {"$set": wrapped},
            upsert=True
        )
        count += 1
    print(f"Loaded {count} visitation rows into MongoDB 'daily_fact' collection.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch and save DSEC data.")
    parser.add_argument('--ggr', action='store_true', help='Reload GGR data')
    parser.add_argument('--hotel', action='store_true', help='Reload hotel data')
    parser.add_argument('--visitation', action='store_true', help='Reload visitation data')
    args = parser.parse_args()
    if args.ggr:
        fetch_and_save_ggr()
    if args.hotel:
        fetch_and_save_hotel()
    if args.visitation:
        fetch_and_save_visitation()
    if not (args.ggr or args.hotel or args.visitation):
        print("No action specified. Use --ggr, --hotel, or --visitation.")
