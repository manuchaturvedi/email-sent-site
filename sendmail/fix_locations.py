import sqlite3

conn = sqlite3.connect('justmailit.db')
cursor = conn.cursor()

# Update all invalid locations to force re-extraction
cursor.execute("""
    UPDATE job_posts 
    SET location = 'Remote/On-site' 
    WHERE location LIKE '%profile%' 
       OR location LIKE '%processed%' 
       OR location LIKE '%immediately%' 
       OR location LIKE '%appy%' 
       OR location LIKE '%Appy%'
       OR location LIKE '%📂%'
       OR location LIKE '%Core%' 
       OR location LIKE '%Java:%'
       OR location LIKE '%🔥%'
       OR location LIKE '%🚀%'
       OR location LIKE '%📍%'
       OR location LIKE '%💼%'
       OR location LIKE '%📅%'
       OR LENGTH(location) > 50
       OR LENGTH(location) < 3
""")

conn.commit()
print(f'✅ Updated {cursor.rowcount} invalid location rows to force re-extraction')

# Show all unique locations for verification
cursor.execute('SELECT DISTINCT location FROM job_posts ORDER BY location')
rows = cursor.fetchall()
print(f"\n📍 Found {len(rows)} unique locations:")
for r in rows:
    print(f"  - [{r[0]}]")

conn.close()
print("\n✓ Database updated. Restart the Flask server to see new locations.")
