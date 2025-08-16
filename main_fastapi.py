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
    - If no parameters: returns a list of all unique field names.
    - If field is provided: returns matching fields (fuzzy, case-insensitive).
    - If from/to are provided: filters by date range.
    """
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['MOWATCH']
    collection = db['daily_fact']
    # If no query parameters at all, return field names only
    from fastapi import Request
    import inspect
    # Get the current request object
    request = None
    for frame in inspect.stack():
        if 'request' in frame.frame.f_locals:
            request = frame.frame.f_locals['request']
            break
    if request is None:
        try:
            from fastapi import Request
            import starlette.requests
            request = starlette.requests.Request(scope={})
        except Exception:
            pass
    # Fallback: check if all parameters are None
    has_query = False
    try:
        # If running in FastAPI, request.query_params will exist
        if request and hasattr(request, 'query_params') and request.query_params:
            has_query = bool(request.query_params)
    except Exception:
        pass
    if not (field or from_date or to_date) and not has_query:
        docs = collection.find({}, {'data': 1})
        field_names = set()
        for doc in docs:
            data = doc.get('data', {})
            for k in data:
                field_names.add(k)
        return sorted(field_names)
    # Otherwise, proceed as before
    query = {}
    if not from_date and not to_date:
        today = datetime.today()
        from_date = (today - timedelta(days=90)).strftime('%Y-%m-%d')
        to_date = today.strftime('%Y-%m-%d')
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

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_fastapi:app", host="127.0.0.1", port=8000, reload=True)
