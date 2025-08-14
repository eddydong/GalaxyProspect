# This script fetches financial data and saves it to a JSON file without any plotting.
# Run "python load_market_data.py" or "python load_market_data.py incremental" to do incremental update
# Run "python load_market_data.py full" to do full update

import yfinance as yf
import json
import os
import pandas as pd
import sys
from datetime import datetime, timedelta

# List of 6 Macau casino operators traded in Hong Kong + 3 indexes
symbols = [
    '0027.HK',  # Galaxy Entertainment
    '0880.HK',  # SJM Holdings
    '1128.HK',  # Wynn Macau
    '1928.HK',  # Sands China
    '2282.HK',  # MGM China
    '0200.HK',  # Melco International Development
    '^HSI',     # Hang Seng Index (Hong Kong)
    '000001.SS',# Shanghai Composite
    '399001.SZ' # Shenzhen Component
]

output = {}

def get_latest_date(existing_data, symbol):
    if symbol not in existing_data:
        return None
    # Exclude non-date keys (like 'price_targets')
    dates = [d for d in existing_data[symbol].keys() if d[:4].isdigit()]
    if not dates:
        return None
    return max(dates)

def fetch_and_merge(symbols, mode):
    output = {}
    existing_data = {}
    if mode == 'incremental' and os.path.exists('data.json'):
        with open('data.json', 'r') as f:
            existing_data = json.load(f)

    today = datetime.today().strftime('%Y-%m-%d')
    for symbol in symbols:
        print(f'\n=== {symbol} ===')
        # Determine start date
        if mode == 'incremental':
            latest = get_latest_date(existing_data, symbol)
            if latest:
                # Add one day to avoid overlap
                start_date = (datetime.strptime(latest, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                start_date = '2000-01-01'
        else:
            start_date = '2000-01-01'

        # Download data
        data = yf.download(symbol, start=start_date, end=today, group_by='ticker', auto_adjust=False)
        try:
            # Handle both single-index and multi-index columns
            if isinstance(data.columns, pd.MultiIndex):
                if (symbol, 'Adj Close') in data.columns:
                    cols = [(symbol, 'Adj Close')]
                    if (symbol, 'Volume') in data.columns:
                        cols.append((symbol, 'Volume'))
                    df_out = data[cols].dropna()
                    # Rename columns for JSON output
                    df_out.columns = [c[1] for c in df_out.columns]
                else:
                    print(f"Skipping {symbol}: No 'Adj Close' in data.")
                    continue
            else:
                # Single-index columns (shouldn't happen for batch, but handle just in case)
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
            # Merge with existing data
            merged = dict(existing_data.get(symbol, {}))
            merged.update(df_out.to_dict(orient='index'))
            output[symbol] = merged

            # Fetch price target data (if available)
            ticker = yf.Ticker(symbol)
            price_targets = {}
            try:
                analysis = ticker.analysis if hasattr(ticker, 'analysis') else None
                if analysis is not None:
                    for col in ['targetMeanPrice', 'targetHighPrice', 'targetLowPrice', 'targetMedianPrice']:
                        if col in analysis:
                            price_targets[col] = float(analysis[col])
            except Exception as e:
                print(f"No price target data for {symbol}: {e}")
            if price_targets:
                output[symbol]['price_targets'] = price_targets
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    if output:
        with open('data.json', 'w') as f:
            json.dump(output, f, indent=2, default=str)

if __name__ == '__main__':
    mode = 'incremental'
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode not in ['full', 'incremental']:
            print("Usage: python load_market_data.py [full|incremental]")
            sys.exit(1)
    fetch_and_merge(symbols, mode)


