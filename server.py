from flask import Flask, jsonify, send_from_directory, Response, request
import pymongo
import json
from datetime import datetime, timedelta
from flasgger import Swagger

app = Flask(__name__)
swagger = Swagger(app)

@app.route('/api/daily')
def api_daily():
    field_name = request.args.get('field')
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['MOWATCH']
    collection = db['daily_fact']
    query = {}
    if not from_date and not to_date:
        # Default: last 90 days from today
        today = datetime.today()
        from_date = (today - timedelta(days=90)).strftime('%Y-%m-%d')
        to_date = today.strftime('%Y-%m-%d')
    if from_date and to_date:
        query['_id'] = {'$gte': from_date, '$lte': to_date}
    elif from_date:
        query['_id'] = {'$gte': from_date}
    elif to_date:
        query['_id'] = {'$lte': to_date}
    if field_name:
        docs = list(collection.find(query))
        result = []
        field_name_lower = field_name.lower()
        for doc in docs:
            data = doc.get('data', {})
            for k in data:
                if field_name_lower in k.lower():
                    out = {'_id': str(doc['_id']), k: data[k]}
                    result.append(out)
                    break
        return jsonify(result)
    elif not request.args:
        # No parameters: return a list of all unique field names in data
        docs = collection.find({}, {'data': 1})
        field_names = set()
        for doc in docs:
            data = doc.get('data', {})
            for k in data:
                field_names.add(k)
        return jsonify(sorted(field_names))
    else:
        docs = list(collection.find(query))
        for doc in docs:
            doc['_id'] = str(doc['_id'])
        return jsonify(docs)

@app.route('/api/preview')
def preview_data():
    # Connect to MongoDB and fetch all documents from daily_fact
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['MOWATCH']
    collection = db['daily_fact']
    docs = list(collection.find({}))
    # Convert ObjectId to string and prepare readable HTML
    for doc in docs:
        doc['_id'] = str(doc['_id'])
    html = "<html><head><title>Daily Fact Preview</title><style>body{font-family:monospace;}pre{background:#f8f8f8;padding:1em;}</style></head><body>"
    html += f"<h2>daily_fact ({len(docs)} records)</h2>"
    for doc in docs:
        html += f"<pre>{json.dumps(doc, indent=2, ensure_ascii=False)}</pre>"
    html += "</body></html>"
    return Response(html, mimetype='text/html')

@app.route('/api/data')
def get_data():
    # Get startDate from MongoDB config collection
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['MOWATCH']
    config_doc = db['config'].find_one({'_id': 'main'})
    start_date = config_doc.get('startDate', '2000-01-01') if config_doc else '2000-01-01'
    collection = db['daily_fact']
    # Query for all documents with _id >= start_date
    docs = list(collection.find({"_id": {"$gte": start_date}}))
    # Convert ObjectId to string if needed
    for doc in docs:
        doc['_id'] = str(doc['_id'])
    return jsonify(docs)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(debug=True)
