import json
from datetime import datetime

import json
import os
import sys
import math
from datetime import datetime, timedelta
from fredapi import Fred
import yfinance as yf
import pandas as pd

FRED_API_KEY = '7479e85ab14cfbc7497819516a20dec4'

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def get_latest_date(existing_data, symbol):
    if symbol not in existing_data:
        return None
    dates = [d for d in existing_data[symbol].keys() if d[:4].isdigit()]
    if not dates:
        return None
    return max(dates)

def fetch_yf_data(symbols, mode, existing_data):
    output = {}
    today = datetime.today().strftime('%Y-%m-%d')
    for symbol in symbols:
        print(f'\n=== {symbol} (YF) ===')
        if mode == 'incremental':
            latest = get_latest_date(existing_data, symbol)
            if latest:
                start_date = (datetime.strptime(latest, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                start_date = '2000-01-01'
        else:
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
            if mode == 'incremental' and code in existing_data:
                latest = get_latest_date(existing_data, code)
                start_date = (datetime.strptime(latest, '%Y-%m-%d') + timedelta(days=1)) if latest else None
            else:
                start_date = None
            series = fred.get_series(code)
            series_dict = {}
            for date, value in series.items():
                if start_date and date < start_date:
                    continue
                date_str = date.strftime('%Y-%m-%d')
                if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
                    adj_close = None
                else:
                    adj_close = float(value)
                series_dict[date_str] = {"Adj Close": adj_close, "Volume": 0}
            merged = dict(existing_data.get(code, {}))
            merged.update(series_dict)
            macro_data[code] = merged
        except Exception as e:
            print(f"Error processing {code}: {e}")
    return macro_data

def main():
    config = load_config()
    yf_symbols = [item['symbol_name'] for item in config if item['server'] == 'YF']
    fred_symbols = [item['symbol_name'] for item in config if item['server'] == 'FRED']
    fred_desc = {item['symbol_name']: item['desc'] for item in config if item['server'] == 'FRED'}

    # Load existing data if incremental
    mode = 'incremental'
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode not in ['full', 'incremental']:
            print("Usage: python load_macro_data.py [full|incremental]")
            sys.exit(1)
    existing_data = {}
    if os.path.exists('macro.json'):
        with open('macro.json', 'r') as f:
            existing_data = json.load(f)

    # Fetch data
    yf_data = fetch_yf_data(yf_symbols, mode, existing_data)
    fred_data = fetch_fred_data(fred_symbols, fred_desc, mode, existing_data)

    # Merge and save
    merged = dict(existing_data)
    merged.update(yf_data)
    merged.update(fred_data)
    with open('macro.json', 'w') as f:
        json.dump(merged, f, indent=2)
    print("Saved macro data to macro.json")

if __name__ == '__main__':
    main()
