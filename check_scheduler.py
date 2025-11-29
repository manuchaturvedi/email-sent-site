import sys
sys.path.insert(0, '/app')

from sendmail.database import Database

db = Database()
jobs = db.get_all_scheduled_jobs()

print("\n=== SCHEDULED JOBS ===")
if not jobs:
    print("No scheduled jobs found")
else:
    for job in jobs:
        print(f"\nJob: {job['job_name']}")
        print(f"  Role: {job['search_role']}")
        print(f"  Cron: {job['cron_expression']}")
        print(f"  Active: {job['is_active']}")
        print(f"  Last Run: {job['last_run']}")
        print(f"  Next Run: {job['next_run']}")

print("\n")
