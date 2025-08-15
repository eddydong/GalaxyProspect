
from flask import Flask, jsonify, send_from_directory
import sqlite3
import os

app = Flask(__name__)

@app.route('/api/data')
def get_data():
    DB_FILE = 'galaxyprospect.db'
    # Get startDate from config.json
    import json
    with open('config.json', 'r') as f:
        config = json.load(f)
    start_date = config.get('startDate', '2000-01-01')
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM fact WHERE date >= ?', (start_date,))
    rows = c.fetchall()
    data = [dict(row) for row in rows]
    conn.close()
    return jsonify(data)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(debug=True)
