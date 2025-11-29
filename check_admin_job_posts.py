import sys
sys.path.insert(0, '/justmailit')

from sendmail.database import Database

def check_database():
    try:
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if job_posts table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"[INFO] Available tables: {tables}")
        
        if 'job_posts' not in tables:
            print("[ERROR] job_posts table does not exist!")
            return
        
        # Check job_posts schema
        cursor.execute("PRAGMA table_info(job_posts)")
        columns = cursor.fetchall()
        print(f"\n[INFO] job_posts columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Count job posts
        cursor.execute("SELECT COUNT(*) FROM job_posts")
        count = cursor.fetchone()[0]
        print(f"\n[INFO] Total job posts: {count}")
        
        # Try the same query as admin route
        cursor.execute("""
            SELECT 
                jp.id, jp.title, jp.company, jp.location, jp.email,
                jp.description, jp.posted_date, jp.source_url, jp.created_at,
                jp.user_email
            FROM job_posts jp
            ORDER BY jp.created_at DESC
            LIMIT 5
        """)
        
        jobs = [dict(row) for row in cursor.fetchall()]
        print(f"\n[INFO] Sample jobs retrieved: {len(jobs)}")
        if jobs:
            print(f"  First job title: {jobs[0].get('title', 'N/A')}")
        
        conn.close()
        print("\n[SUCCESS] Database check completed successfully")
        
    except Exception as e:
        print(f"[ERROR] Database check failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()
