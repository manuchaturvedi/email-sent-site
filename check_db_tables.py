import sqlite3

conn = sqlite3.connect('sendmail/justmailit.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=" * 80)
print("ALL TABLES IN DATABASE:")
print("=" * 80)
for table in tables:
    print(f"- {table[0]}")

# Check scheduler-related data
print("\n" + "=" * 80)
print("CHECKING FOR SCHEDULER DATA:")
print("=" * 80)

# Check if there's a scheduler or jobs related table
for table in tables:
    table_name = table[0]
    if 'job' in table_name.lower() or 'schedule' in table_name.lower() or 'admin' in table_name.lower():
        print(f"\n\nTable: {table_name}")
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
        rows = cursor.fetchall()
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Columns: {', '.join(columns)}")
        print(f"Row count: {len(rows)}")
        if rows:
            print("Sample rows:")
            for row in rows[:3]:
                print(f"  {row}")

conn.close()
