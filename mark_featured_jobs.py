#!/usr/bin/env python3
"""
Script to mark jobs from big companies as featured
"""
import sys
sys.path.insert(0, '/app/sendmail')
import sqlite3

# Connect to database
conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()

# List of big companies to mark as featured
big_companies = ['Google', 'Microsoft', 'Amazon', 'Apple', 'Meta', 'Netflix', 'Tesla', 
                'Uber', 'Airbnb', 'Adobe', 'Salesforce', 'Oracle', 'IBM', 'Intel', 
                'NVIDIA', 'AMD', 'Qualcomm', 'Twitter', 'LinkedIn', 'Spotify',
                'TCS', 'Tata Consultancy', 'Infosys', 'Accenture', 'Cognizant', 
                'Capgemini', 'Cap Gemini', 'Wipro', 'HCL', 'Tech Mahindra']

print("Marking jobs from big companies as featured...")

total_marked = 0
for company in big_companies:
    cursor.execute('UPDATE job_posts SET featured = 1 WHERE company LIKE ? AND featured = 0', (f'%{company}%',))
    marked = cursor.rowcount
    if marked > 0:
        print(f"  ✓ {company}: {marked} jobs marked")
        total_marked += marked

conn.commit()

# Get final count
cursor.execute('SELECT COUNT(*) FROM job_posts WHERE featured = 1')
featured_count = cursor.fetchone()[0]

print(f"\n✨ Total featured jobs: {featured_count}")
print(f"📊 Newly marked: {total_marked}")

# Show sample featured companies
cursor.execute('SELECT DISTINCT company FROM job_posts WHERE featured = 1 ORDER BY company')
print("\n🏢 Featured companies:")
for row in cursor.fetchall():
    print(f"   - {row[0]}")

conn.close()
