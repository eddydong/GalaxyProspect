// MongoDB Playground
// Use Ctrl+Space inside a snippet or a string literal to trigger completions.

// The current database to use.
use("MOWATCH");

// Find a document in a collection.
db.daily_fact.find().sort({ _id: -1 }).limit(100).toArray();