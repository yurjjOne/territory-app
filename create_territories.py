import sqlite3
import os

# Delete existing database if it exists
if os.path.exists('territories.db'):
    os.remove('territories.db')

# Create a new database
conn = sqlite3.connect('territories.db')
cursor = conn.cursor()

# Create territories table with the correct structure
cursor.execute('''
CREATE TABLE IF NOT EXISTS territories (
    id INTEGER PRIMARY KEY,
    name TEXT,
    custom_name TEXT,
    status TEXT DEFAULT 'Вільна',
    taken_by TEXT DEFAULT '',
    date_taken TEXT DEFAULT '',
    date_due TEXT DEFAULT '',
    notes TEXT DEFAULT ''
)
''')

# Create history table
cursor.execute('''
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    territory_id INTEGER,
    taken_by TEXT,
    date_taken TEXT,
    date_due TEXT
)
''')

# Insert territories with basic information
territories = []
for i in range(1, 183):  # 182 території
    territories.append((i, f"Територія {i}", f"Територія {i}", 'Вільна', '', '', '', ''))

cursor.executemany('INSERT INTO territories (id, name, custom_name, status, taken_by, date_taken, date_due, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', territories)

# Commit changes and close connection
conn.commit()
conn.close()

print("Territories database has been created successfully with 182 territories!") 