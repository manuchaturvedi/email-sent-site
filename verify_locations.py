#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()

# Get statistics
cursor.execute('SELECT COUNT(*) FROM job_posts')
total_jobs = cursor.fetchone()[0]

# Check remaining tech terms as locations
tech_terms = ['Java', 'Python', 'React', 'Angular', 'Node', 'DevOps', 'Docker', 
              'Azure', 'AWS', 'JavaScript', 'HTML', 'CSS', 'Machine Learning']

print("📊 Location Quality Report\n")
print(f"Total jobs: {total_jobs}\n")

remaining_bad = []
for term in tech_terms:
    cursor.execute('SELECT id, location FROM job_posts WHERE location = ? OR location LIKE ?', 
                   (term, f'%{term}%'))
    results = cursor.fetchall()
    if results:
        for job_id, location in results:
            # Only count if it's EXACTLY the tech term, not part of a real location
            if location.strip() in tech_terms:
                remaining_bad.append((job_id, location))

print(f"🔴 Jobs still with tech terms as location: {len(remaining_bad)}")
if remaining_bad:
    print("\nRemaining issues:")
    for job_id, location in remaining_bad[:15]:
        print(f"  ID {job_id}: {location}")
    if len(remaining_bad) > 15:
        print(f"  ... and {len(remaining_bad) - 15} more")

# Count jobs with proper locations
cursor.execute('''
    SELECT COUNT(*) FROM job_posts 
    WHERE location NOT IN ('Location Not Specified', 'Remote/On-site', 'Not specified')
    AND location IS NOT NULL
    AND location != ''
''')
good_locations = cursor.fetchone()[0]

print(f"\n✅ Jobs with valid locations: {good_locations} ({good_locations*100/total_jobs:.1f}%)")

# Show sample of good locations
cursor.execute('''
    SELECT DISTINCT location FROM job_posts 
    WHERE location NOT IN ('Location Not Specified', 'Remote/On-site', 'Not specified')
    AND location IS NOT NULL
    AND location != ''
    ORDER BY location
    LIMIT 30
''')
samples = cursor.fetchall()
print(f"\n📍 Sample valid locations:")
for (loc,) in samples:
    print(f"   • {loc}")

conn.close()
