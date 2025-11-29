import sqlite3
from datetime import datetime

conn = sqlite3.connect('sendmail/justmailit.db')
cursor = conn.cursor()

# Check admin scraping jobs
cursor.execute("SELECT id, email, keywords, location, cron_expression, next_run, is_active FROM admin_scraping_jobs")
jobs = cursor.fetchall()

print("=" * 80)
print("ADMIN SCRAPING JOBS:")
print("=" * 80)

if jobs:
    for job in jobs:
        print(f"\nJob ID: {job[0]}")
        print(f"Email: {job[1]}")
        print(f"Keywords: {job[2]}")
        print(f"Location: {job[3]}")
        print(f"Cron Expression: {job[4]}")
        print(f"Next Run: {job[5]}")
        print(f"Is Active: {job[6]}")
        print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
else:
    print("No admin scraping jobs found!")

# Check job_posts count
cursor.execute("SELECT COUNT(*) FROM job_posts")
count = cursor.fetchone()[0]
print(f"\n\nTotal job_posts in database: {count}")

conn.close()
