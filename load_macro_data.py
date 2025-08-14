import json
from datetime import datetime
from fredapi import Fred

# Set your FRED API key here
FRED_API_KEY = '7479e85ab14cfbc7497819516a20dec4'

# Macro indicators to fetch (add more as needed)
INDICATORS = {
    'CHNCPIALLMINMEI': 'China Consumer Price Index: All Items',  # Correct FRED code for China CPI
    'CSCICP02CNM460S': 'China Composite Consumer Confidence',  # FRED code for China Composite Consumer Confidence
    'EXPCH': 'U.S. Exports of Goods to China',  # FRED code for U.S. Exports of Goods to China
    'IR3TIB01CNM156N': 'China Interest Rates: 3-Month',
    'CHNLOLITOAASTSAM': 'OECD Composite Leading Indicator',
    'CHNCSESFT02STSAM': 'OECD Future Tendency for China',
    'CHNBSCICP02STSAM': 'OECD Business Tendency Surveys (Manufacturing)'
}

# Output file
OUTPUT_FILE = 'macro.json'


def fetch_macro_data():
    fred = Fred(api_key=FRED_API_KEY)
    macro_data = {}
    import math
    for code, desc in INDICATORS.items():
        print(f'Fetching {desc} ({code})...')
        series = fred.get_series(code)
        # Convert to the same format as your current JSON: {date: {"Adj Close": value, "Volume": 0}}
        series_dict = {}
        for date, value in series.items():
            # FRED returns pandas.Timestamp, convert to YYYY-MM-DD
            date_str = date.strftime('%Y-%m-%d')
            # Replace NaN or infinite values with None (null in JSON)
            if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
                adj_close = None
            else:
                adj_close = float(value)
            series_dict[date_str] = {"Adj Close": adj_close, "Volume": 0}
        macro_data[code] = series_dict
    return macro_data


def main():
    macro_data = fetch_macro_data()
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(macro_data, f, indent=2)
    print(f"Saved macro data to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
