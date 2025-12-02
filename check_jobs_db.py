import sqlite3
import json

db_path = r"c:\Users\windows 10\Desktop\AI_support\justmailit.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get total count
cursor.execute('SELECT COUNT(*) as total FROM job_posts')
total = cursor.fetchone()['total']
print(f"\n📊 Total jobs in database: {total}")

# Get recent jobs
cursor.execute('''
    SELECT id, user_email, title, company, location, recruiter_email, created_at 
    FROM job_posts 
    ORDER BY created_at DESC 
    LIMIT 10
''')

rows = cursor.fetchall()
print(f"\n📋 Recent 10 jobs:\n")
print(f"{'ID':<5} {'User Email':<30} {'Title':<20} {'Company':<20} {'Created':<20}")
print("-" * 100)

for row in rows:
    job = dict(row)
    print(f"{job['id']:<5} {job['user_email']:<30} {job['title'][:20]:<20} {job['company'][:20] if job['company'] else 'N/A':<20} {job['created_at'][:19]:<20}")

# Test the get_job_posts query (universal query)
print("\n\n🔍 Testing universal query (no user_email filter):")
cursor.execute('''
    SELECT * FROM job_posts 
    ORDER BY created_at DESC 
    LIMIT 5
''')

rows = cursor.fetchall()
print(f"Returned {len(rows)} jobs")

for row in rows:
    job = dict(row)
    print(f"\n  ID: {job['id']}")
    print(f"  User: {job['user_email']}")
    print(f"  Title: {job['title']}")
    print(f"  Company: {job['company']}")
    print(f"  Email: {job['recruiter_email']}")
    print(f"  Created: {job['created_at']}")

conn.close()
