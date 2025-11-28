import sqlite3

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(user_profiles)')
cols = cursor.fetchall()
print('user_profiles columns:')
for row in cols:
    print(f'  {row[1]} ({row[2]})')

cursor.execute('SELECT * FROM user_profiles')
rows = cursor.fetchall()
print(f'\nTotal rows: {len(rows)}')
if rows:
    print('\nFirst row data:')
    for i, col in enumerate(cols):
        print(f'  {col[1]}: {rows[0][i]}')
conn.close()
