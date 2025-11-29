import sqlite3

conn = sqlite3.connect('sendmail/justmailit.db')
cursor = conn.cursor()

# Check if scheduled_jobs table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scheduled_jobs'")
result = cursor.fetchone()

if result:
    print("✅ scheduled_jobs table EXISTS")
    
    # Get table structure
    cursor.execute("PRAGMA table_info(scheduled_jobs)")
    columns = cursor.fetchall()
    print("\nTable structure:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Get all rows
    cursor.execute("SELECT * FROM scheduled_jobs")
    rows = cursor.fetchall()
    print(f"\nTotal rows: {len(rows)}")
    
    if rows:
        print("\nScheduled jobs:")
        for row in rows:
            print(f"\n{row}")
    else:
        print("\n⚠️ NO SCHEDULED JOBS FOUND IN TABLE!")
else:
    print("❌ scheduled_jobs table DOES NOT EXIST")
    print("\nAvailable tables:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for table in cursor.fetchall():
        print(f"  - {table[0]}")

conn.close()
