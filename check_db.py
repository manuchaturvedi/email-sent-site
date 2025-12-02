import sqlite3
import os

db_path = 'linkedin_jobs.db'

print("=" * 60)
print("🔍 LINKEDIN JOB SCRAPER - DATABASE CHECK")
print("=" * 60)
print(f"Database: {os.path.abspath(db_path)}")
print(f"Exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    size_kb = os.path.getsize(db_path) / 1024
    print(f"Size: {size_kb:.2f} KB")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get counts
    cursor.execute("SELECT COUNT(*) FROM job_posts")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM job_posts WHERE recruiter_email IS NOT NULL AND recruiter_email != ''")
    with_email = cursor.fetchone()[0]
    
    print(f"\n📊 Statistics:")
    print(f"   Total Jobs: {total}")
    print(f"   With Email: {with_email}")
    
    if total > 0:
        print(f"\n🔍 Sample Jobs (first 3):")
        cursor.execute("SELECT recruiter_email, company, created_at FROM job_posts ORDER BY created_at DESC LIMIT 3")
        for i, row in enumerate(cursor.fetchall(), 1):
            email, company, date = row
            print(f"   {i}. {email} @ {company or 'Unknown'} - {date}")
    
    conn.close()
else:
    print("\n💡 Database will be created on first successful scrape run")
    print("\nTo run scraper:")
    print("  1. Set LinkedIn credentials:")
    print("     $env:LINKEDIN_EMAIL = 'your@email.com'")
    print("     $env:LINKEDIN_PASSWORD = 'yourpassword'")
    print("\n  2. Run scraper:")
    print("     python linkedin_job_scraper.py --role 'Python Developer'")
    print("\n  OR use visible mode for manual login:")
    print("     python linkedin_job_scraper.py --visible --role 'Python Developer'")

print("=" * 60)
