import sqlite3
from datetime import datetime

conn = sqlite3.connect('sendmail/justmailit.db')
cursor = conn.cursor()

# Set next_run to NULL so the scheduler recalculates it
cursor.execute("UPDATE scheduled_jobs SET next_run = NULL WHERE id = 1")
conn.commit()

print("✅ Reset next_run time")
print("The scheduler will recalculate the next run time based on the cron expression")
print("\nCurrent job:")
cursor.execute("SELECT id, job_name, cron_expression, is_active, next_run FROM scheduled_jobs WHERE id = 1")
job = cursor.fetchone()
print(f"  ID: {job[0]}")
print(f"  Name: {job[1]}")
print(f"  Cron: {job[2]} (every 30 minutes)")
print(f"  Active: {job[3]}")
print(f"  Next Run: {job[4]}")

conn.close()
