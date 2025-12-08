import sqlite3

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()
cursor.execute('SELECT DISTINCT location FROM job_posts WHERE location IS NOT NULL AND location != "" LIMIT 30')
locations = cursor.fetchall()
print('Unique locations in database:')
for loc in locations:
    print(f'  - {loc[0]}')
conn.close()
