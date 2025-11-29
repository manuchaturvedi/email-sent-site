import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('sendmail/justmailit.db')
cursor = conn.cursor()

# Force the job to run NOW by setting next_run to a time in the past
now = datetime.now()
trigger_time = (now - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')

cursor.execute('''
    UPDATE scheduled_jobs 
    SET next_run = ? 
    WHERE id = 1
''', (trigger_time,))

conn.commit()

# Verify
cursor.execute("SELECT id, job_name, next_run FROM scheduled_jobs WHERE id = 1")
job = cursor.fetchone()

print("=" * 80)
print("FORCING SCHEDULER TO RUN NOW")
print("=" * 80)
print(f"Job ID: {job[0]}")
print(f"Job Name: {job[1]}")
print(f"Next Run Set To: {job[2]} (should trigger immediately)")
print(f"Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print("\n✅ Job should run within 60 seconds (scheduler checks every minute)")
print("\nWatch the logs with:")
print("docker logs -f justmailit-app")

conn.close()
