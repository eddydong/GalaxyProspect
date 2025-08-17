// MongoDB Playground
// Use Ctrl+Space inside a snippet or a string literal to trigger completions.

// The current database to use.
use("MOWATCH");

// Find a document in a collection.
db.getCollection("daily_fact").find(
    {"_id": { $gte: "2025-01-01" }}, 
    {"data.DSEC_ggr": 1}
).sort({_id: -1}).toArray();
