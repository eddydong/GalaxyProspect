from flask import Flask, jsonify, send_from_directory
import json
import os

app = Flask(__name__)


@app.route('/api/data')
def get_data():
    with open('data.json', 'r') as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(debug=True)
