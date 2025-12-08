#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()

# Fix job 782 specifically
cursor.execute(
    "UPDATE job_posts SET location = ? WHERE id = ?",
    ("Bangalore | Chennai | Hyderabad | Pune", 782)
)
conn.commit()

# Verify the update
cursor.execute('SELECT id, title, location FROM job_posts WHERE id = 782')
result = cursor.fetchone()
print(f"✅ Updated Job ID {result[0]}")
print(f"   Title: {result[1]}")
print(f"   New Location: {result[2]}")

conn.close()
