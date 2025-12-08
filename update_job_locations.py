#!/usr/bin/env python3
"""
Script to analyze existing job posts and update locations in database
"""
import sys
sys.path.insert(0, '/app/sendmail')

from job_analyzer import JobAnalyzer
import sqlite3
import json

# Connect to database
conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()

# Initialize analyzer
print("Initializing JobAnalyzer...")
analyzer = JobAnalyzer()

# Get all job posts
cursor.execute('SELECT id, title, company, location, full_text, recruiter_email FROM job_posts')
jobs = cursor.fetchall()

print(f"\nFound {len(jobs)} jobs to analyze\n")
print("=" * 80)

updated_count = 0
skipped_count = 0

for job in jobs:
    job_id, title, company, old_location, full_text, email = job
    
    # Skip if already has a good location (not generic)
    if old_location and old_location not in ['Remote/On-site', 'Remote/On-Site', 'Location Not Specified', '']:
        if len(old_location) < 50 and 'experience' not in old_location.lower():
            skipped_count += 1
            continue
    
    # Create job dict for analyzer
    job_dict = {
        'id': job_id,
        'title': title or '',
        'company': company or '',
        'location': old_location or '',
        'full_text': full_text or '',
        'description': full_text or '',
        'email': email or ''
    }
    
    # Analyze the job
    analyzed = analyzer.analyze_post(job_dict)
    new_location = analyzed.get('location', 'Remote')
    
    # Only update if location changed
    if new_location != old_location:
        cursor.execute('UPDATE job_posts SET location = ? WHERE id = ?', (new_location, job_id))
        updated_count += 1
        
        company_display = (company[:30] + '...') if company and len(company) > 30 else company
        print(f"✓ ID {job_id}: {company_display}")
        print(f"  OLD: {old_location}")
        print(f"  NEW: {new_location}")
        print()

conn.commit()

print("=" * 80)
print(f"\n✅ Analysis complete!")
print(f"   Updated: {updated_count} jobs")
print(f"   Skipped: {skipped_count} jobs (already had valid locations)")
print(f"   Total:   {len(jobs)} jobs\n")

# Show sample of updated locations
cursor.execute('SELECT DISTINCT location FROM job_posts WHERE location IS NOT NULL ORDER BY location LIMIT 20')
locations = cursor.fetchall()
print("📍 Sample locations after update:")
for loc in locations:
    print(f"   - {loc[0]}")

conn.close()
