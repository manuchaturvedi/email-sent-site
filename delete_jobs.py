import sqlite3

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()
cursor.execute('DELETE FROM job_posts')
conn.commit()
print(f'Deleted {conn.total_changes} job posts')
cursor.execute('SELECT COUNT(*) FROM job_posts')
count = cursor.fetchone()[0]
print(f'Remaining job posts: {count}')
conn.close()
