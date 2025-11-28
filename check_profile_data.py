import sqlite3

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()

cursor.execute('SELECT email, email_subject, email_content, search_role, resume_filename, length(resume_data) as resume_size FROM user_profiles')
rows = cursor.fetchall()

print('=== User Profiles Data ===')
for row in rows:
    print(f'\nEmail: {row[0]}')
    print(f'  Subject: {row[1][:50] if row[1] else "None"}...')
    print(f'  Content: {row[2][:50] if row[2] else "None"}...')
    print(f'  Role: {row[3] or "None"}')
    print(f'  Resume: {row[4] or "None"}')
    print(f'  Resume Size: {row[5] or 0} bytes')

conn.close()
