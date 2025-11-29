import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('sendmail/justmailit.db')
cursor = conn.cursor()

# Check total jobs
cursor.execute("SELECT COUNT(*) FROM job_posts")
total = cursor.fetchone()[0]

# Check jobs added in last 10 minutes
ten_min_ago = (datetime.now() - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
cursor.execute("SELECT COUNT(*) FROM job_posts WHERE created_at >= ?", (ten_min_ago,))
recent = cursor.fetchone()[0]

# Get some recent job samples
cursor.execute("""
    SELECT title, company, recruiter_email, created_at 
    FROM job_posts 
    WHERE created_at >= ? 
    LIMIT 5
""", (ten_min_ago,))
recent_jobs = cursor.fetchall()

print("=" * 80)
print("JOB SCRAPING RESULTS")
print("=" * 80)
print(f"Total jobs in database: {total}")
print(f"Jobs added in last 10 minutes: {recent}")
print("\nRecent job samples:")
for job in recent_jobs:
    print(f"\n  Title: {job[0][:60]}...")
    print(f"  Company: {job[1]}")
    print(f"  Email: {job[2]}")
    print(f"  Added: {job[3]}")

conn.close()
