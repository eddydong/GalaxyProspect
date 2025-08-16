
from pymongo import MongoClient
import json
from datetime import datetime

# MongoDB connection setup
client = MongoClient('mongodb://localhost:27017/')
db = client['MOWATCH']
events_collection = db['events']


def load_events_to_mongodb(json_path='events_expanded.json'):
    with open(json_path, 'r', encoding='utf-8') as f:
        events = json.load(f)
    # Optional: clear existing collection
    events_collection.delete_many({})
    # Group events by date
    grouped = {}
    for event in events:
        date_str = event.get('date')
        if not date_str:
            raise ValueError("Event missing 'date' field.")
        event_no_date = {k: v for k, v in event.items() if k != 'date'}
        # Add value field for impact_score if present
        if 'impact_score' in event_no_date:
            event_no_date['value'] = event_no_date['impact_score']
        grouped.setdefault(date_str, []).append(event_no_date)
    # Upsert into 'daily_fact' collection under data.events as an object with value and events list
    client = MongoClient('mongodb://localhost:27017/')
    db = client['MOWATCH']
    collection = db['daily_fact']
    for date, events_list in grouped.items():
        # Calculate composite impact: 1 - product(1-impact_score)
        impacts = [e.get('impact_score', 0) for e in events_list if isinstance(e.get('impact_score', 0), (int, float))]
        composite_impact = 1.0
        for impact in impacts:
            composite_impact *= (1 - impact)
        composite_impact = 1 - composite_impact if impacts else 0
        events_obj = {"value": composite_impact, "events": events_list}
        # Only update data.events, do not overwrite other fields in data
        collection.update_one(
            {"_id": date},
            {"$set": {"data.events": events_obj}},
            upsert=True
        )
    print(f"Inserted or updated {len(grouped)} date-grouped event documents into MongoDB 'daily_fact'.")

if __name__ == '__main__':
    load_events_to_mongodb()
