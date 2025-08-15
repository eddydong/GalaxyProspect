import sqlite3

conn = sqlite3.connect("galaxyprospect.db")
c = conn.cursor()


# 1. Rename the old table
c.execute("ALTER TABLE ggr_data RENAME TO ggr_data_old")

# 2. Create new table 'fact' with 'date' as PRIMARY KEY and no 'id' column
c.execute("""
CREATE TABLE fact (
	date TEXT PRIMARY KEY,
	GGR REAL NOT NULL
)
""")

# 3. Copy data from old table to new table
c.execute("INSERT INTO fact (date, GGR) SELECT date, GGR FROM ggr_data_old")

# 4. Drop the old table
c.execute("DROP TABLE ggr_data_old")

conn.commit()
conn.close()