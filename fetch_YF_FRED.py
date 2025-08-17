
import json
import os
import sys
import math
from datetime import datetime, timedelta
from fredapi import Fred
import yfinance as yf
import pandas as pd

from pymongo import MongoClient

FRED_API_KEY = '7479e85ab14cfbc7497819516a20dec4'

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def fetch_yf_data(symbols, mode, existing_data):
    output = {}
    today = datetime.today().strftime('%Y-%m-%d')
    for symbol in symbols:
        print(f'\n=== {symbol} (YF) ===')
        start_date = '2000-01-01'
        data = yf.download(symbol, start=start_date, end=today, group_by='ticker', auto_adjust=False)
        try:
            if not isinstance(data, pd.DataFrame):
                print(f"Skipping {symbol}: Data is not a DataFrame.")
                continue            
            if isinstance(data.columns, pd.MultiIndex):
                if (symbol, 'Adj Close') in data.columns:
                    cols = [(symbol, 'Adj Close')]
                    if (symbol, 'Volume') in data.columns:
                        cols.append((symbol, 'Volume'))
                    df_out = data[cols].dropna()
                    df_out.columns = [c[1] for c in df_out.columns]
                else:
                    print(f"Skipping {symbol}: No 'Adj Close' in data.")
                    continue
            else:
                if 'Adj Close' in data.columns:
                    cols = ['Adj Close']
                    if 'Volume' in data.columns:
                        cols.append('Volume')
                    df_out = data[cols].dropna()
                else:
                    print(f"Skipping {symbol}: No 'Adj Close' in data.")
                    continue
            print(df_out)
            df_out.index = df_out.index.astype(str)
            merged = dict(existing_data.get(symbol, {}))
            merged.update(df_out.to_dict(orient='index'))
            output[symbol] = merged
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
    return output

def fetch_fred_data(symbols, desc_map, mode, existing_data):
    fred = Fred(api_key=FRED_API_KEY)
    macro_data = {}
    for code in symbols:
        print(f'\n=== {desc_map[code]} ({code}) (FRED) ===')
        try:
            series = fred.get_series(code)
            series_dict = {}
            for date, value in series.items():
                date_str = date.strftime('%Y-%m-%d')
                if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
                    adj_close = None
                else:
                    adj_close = float(value)
                series_dict[date_str] = {"Adj Close": adj_close, "Volume": 0}
            macro_data[code] = series_dict
        except Exception as e:
            print(f"Error processing {code}: {e}")
    return macro_data


def main():
    config = load_config()
    start_date = config.get('startDate', '2000-01-01')
    symbols = config['symbols']
    yf_symbols = [item['symbol_name'] for item in symbols if item['server'] == 'YF']
    fred_symbols = [item['symbol_name'] for item in symbols if item['server'] == 'FRED']
    fred_desc = {item['symbol_name']: item['desc'] for item in symbols if item['server'] == 'FRED'}
    field_map = {item['symbol_name']: item['field_name'] for item in symbols if 'symbol_name' in item}

    # Always use full mode, ignore any command line args
    mode = 'full'
    existing_data = {}

    # Fetch data
    yf_data = fetch_yf_data(yf_symbols, mode, existing_data)
    fred_data = fetch_fred_data(fred_symbols, fred_desc, mode, existing_data)

    # Merge and filter by start_date
    merged = dict(existing_data)
    merged.update(yf_data)
    merged.update(fred_data)


    # Filter all symbols' data to start_date or later, and print data count for each
    for symbol in list(merged.keys()):
        filtered = {date: val for date, val in merged[symbol].items() if date >= start_date}
        count = len(filtered)
        print(f"{symbol}: {count} records")
        if filtered:
            merged[symbol] = filtered
        else:
            del merged[symbol]

    # Save to MongoDB 'daily_fact' collection, merging with existing data if present
    client = MongoClient('mongodb://localhost:27017/')
    db = client['MOWATCH']
    collection = db['daily_fact']
    # Build a merged dict by date: {date: {field1: value1, ...}}
    by_date = {}
    for symbol in merged:
        field_name = field_map.get(symbol)
        if not field_name:
            continue
        for date, valdict in merged[symbol].items():
            v = valdict.get("Adj Close")
            if v is None:
                continue
            if date not in by_date:
                by_date[date] = {}
            by_date[date][field_name] = v
    # Upsert into MongoDB, merging with existing 'data' field if present, and wrap as {value: ...}
    count = 0
    for date, fields in by_date.items():
        # Only update the relevant fields in data, not the whole data object
        wrapped = {f"data.{k}": {"value": v} for k, v in fields.items()}
        collection.update_one(
            {"_id": date},
            {"$set": wrapped},
            upsert=True
        )
        count += 1
    print(f"Saved all YF/FRED data to MongoDB 'daily_fact' collection (from {start_date} onward, {count} dates updated, merged fields only)")

if __name__ == '__main__':
    main()
