
import json
import os
import sys
import math
from datetime import datetime, timedelta
from fredapi import Fred
import yfinance as yf
import pandas as pd
import sqlite3

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
    field_map = {item['symbol_name']: item['field_name'] for item in symbols}

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

    # Save to DB
    DB_FILE = "galaxyprospect.db"
    TABLE_NAME = "fact"
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # For each symbol, upsert its data by date and field_name
    for symbol in merged:
        field_name = field_map.get(symbol)
        if not field_name:
            continue
        for date, valdict in merged[symbol].items():
            # Use 'Adj Close' if present, else skip
            v = valdict.get("Adj Close")
            if v is None:
                continue
            # Upsert
            c.execute(f"SELECT 1 FROM {TABLE_NAME} WHERE date = ?", (date,))
            if c.fetchone():
                c.execute(f"UPDATE {TABLE_NAME} SET {field_name} = ? WHERE date = ?", (v, date))
            else:
                c.execute(f"INSERT INTO {TABLE_NAME} (date, {field_name}) VALUES (?, ?)", (date, v))
    conn.commit()
    conn.close()
    print(f"Saved all data to {DB_FILE} (from {start_date} onward)")

if __name__ == '__main__':
    main()
