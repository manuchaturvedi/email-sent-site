import sqlite3
from datetime import datetime

conn = sqlite3.connect('sendmail/justmailit.db')
cursor = conn.cursor()

print("=" * 80)
print("CREATING scheduled_jobs TABLE AND DEFAULT JOB")
print("=" * 80)

# Create scheduled_jobs table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS scheduled_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_name TEXT NOT NULL,
        search_role TEXT NOT NULL,
        position TEXT,
        cron_expression TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        last_run TIMESTAMP,
        next_run TIMESTAMP,
        run_count INTEGER DEFAULT 0,
        created_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
print("✅ scheduled_jobs table created")

# Check if any jobs exist
cursor.execute("SELECT COUNT(*) FROM scheduled_jobs")
count = cursor.fetchone()[0]

if count == 0:
    print("\n📝 Creating default scraping job...")
    
    # Insert a default scraping job that runs every 30 minutes
    cursor.execute('''
        INSERT INTO scheduled_jobs 
        (job_name, search_role, position, cron_expression, is_active, created_by, next_run)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        'Auto Job Scraper',
        'Devops hiring OR Engineer hiring',
        'Remote/On-site',
        '*/30 * * * *',  # Every 30 minutes
        1,  # Active
        'admin@justmailit.in',
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))
    
    conn.commit()
    print("✅ Default scraping job created")
else:
    print(f"\n⚠️ {count} job(s) already exist, skipping creation")

# Display all jobs
cursor.execute("SELECT * FROM scheduled_jobs")
jobs = cursor.fetchall()

print("\n" + "=" * 80)
print("ALL SCHEDULED JOBS:")
print("=" * 80)

if jobs:
    for job in jobs:
        print(f"\nJob ID: {job[0]}")
        print(f"Name: {job[1]}")
        print(f"Search Role: {job[2]}")
        print(f"Position: {job[3]}")
        print(f"Cron: {job[4]}")
        print(f"Active: {job[5]}")
        print(f"Last Run: {job[6]}")
        print(f"Next Run: {job[7]}")
        print(f"Run Count: {job[8]}")
else:
    print("No jobs found")

conn.close()
print("\n✅ Done!")
