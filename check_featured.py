import sqlite3

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()

# Check featured count
cursor.execute('SELECT COUNT(*) FROM job_posts WHERE featured = 1')
featured_count = cursor.fetchone()[0]
print(f'Featured jobs: {featured_count}')

# Get sample companies
cursor.execute('SELECT company FROM job_posts WHERE featured = 1 LIMIT 10')
print('\nSample featured companies:')
for row in cursor.fetchall():
    print(f'  - {row[0]}')

conn.close()
