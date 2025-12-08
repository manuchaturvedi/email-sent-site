#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()

cursor.execute('SELECT id, title, company, location, full_text FROM job_posts WHERE id = 782')
result = cursor.fetchone()

print(f"ID: {result[0]}")
print(f"Title: {result[1]}")
print(f"Company: {result[2]}")
print(f"Current Location: {result[3]}")
print(f"\nFull Text:\n{result[4]}")

conn.close()
