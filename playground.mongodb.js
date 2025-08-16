// MongoDB Playground

// Use Ctrl+Space inside a snippet or a string literal to trigger completions.

// The current database to use.
use("MOWATCH");

// db.daily_fact.updateMany(
//     { "Value": { $exists: true } },
//     [{ $set: { value: "$value" } }]
// );

// Find a document in a collection.
db.daily_fact.find().sort({ _id: -1 }).limit(200).toArray();