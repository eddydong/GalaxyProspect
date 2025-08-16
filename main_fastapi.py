from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from datetime import datetime, timedelta
import pymongo

app = FastAPI(title="MOWATCH API", description="Unified time series and event data API", version="1.0.0")

# Mount static files (for index.html and others)
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/api/daily", response_class=JSONResponse, summary="Query daily data", tags=["Data"])
def api_daily(
    field: Optional[str] = Query(None, description="Fuzzy field name to search for"),
    from_date: Optional[str] = Query(None, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, alias="to", description="End date (YYYY-MM-DD)")
):
    """
    Query daily data with optional fuzzy field search and date range.
    - If field is provided: returns matching fields (fuzzy, case-insensitive).
    - If from/to are provided: filters by date range.
    - If no parameters: returns all data.
    """
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['MOWATCH']
    collection = db['daily_fact']
    query = {}
    if from_date and to_date:
        query['_id'] = {'$gte': from_date, '$lte': to_date}
    elif from_date:
        query['_id'] = {'$gte': from_date}
    elif to_date:
        query['_id'] = {'$lte': to_date}
    if field:
        docs = list(collection.find(query))
        result = []
        field_lower = field.lower()
        for doc in docs:
            data = doc.get('data', {})
            for k in data:
                if field_lower in k.lower():
                    out = {'_id': str(doc['_id']), k: data[k]}
                    result.append(out)
                    break
        return result
    else:
        docs = list(collection.find(query))
        for doc in docs:
            doc['_id'] = str(doc['_id'])
        return docs

# New endpoint to list all field names in daily_fact
@app.get("/api/list", response_class=JSONResponse, summary="List all field names in daily_fact", tags=["Data"])
def api_list():
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['MOWATCH']
    collection = db['daily_fact']
    docs = collection.find({}, {'data': 1})
    field_names = set()
    for doc in docs:
        data = doc.get('data', {})
        for k in data:
            field_names.add(k)
    return sorted(field_names)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_fastapi:app", host="127.0.0.1", port=8000, reload=True)
