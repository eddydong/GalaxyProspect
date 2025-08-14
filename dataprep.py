import requests
import json
import sqlite3
import ast

def api_to_json():
    url = 'http://api.marketstack.com/v2/eod?access_key=35f40f3b376df4e6ae24bdf489278f6f&symbols=0027.HK&date_from=2025-04-01'

    r = requests.get(url)
    data = r.json()

    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4)

def json_to_db():
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        # Try loading with ast.literal_eval for non-standard JSON (single quotes)
        with open('data.json', 'r') as f:
            data = ast.literal_eval(f.read())

    # Connect to SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS market_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        date TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL
    )''')

    # Clear existing data (optional)
    c.execute('DELETE FROM market_data')

    # Insert data from JSON
    # This assumes the JSON structure from marketstack API
    for entry in data.get('data', []):
        c.execute('''INSERT INTO market_data (symbol, date, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (
                      entry.get('symbol'),
                      entry.get('date'),
                      entry.get('open'),
                      entry.get('high'),
                      entry.get('low'),
                      entry.get('close'),
                      entry.get('volume')
                  ))

    conn.commit()
    conn.close()

def api_to_db():
    api_to_json()
    json_to_db()

def preview_db():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('SELECT * FROM market_data LIMIT 10')
    rows = c.fetchall()
    for row in rows:
        print(row)
    conn.close()

if __name__ == "__main__":
    api_to_db()
    preview_db()