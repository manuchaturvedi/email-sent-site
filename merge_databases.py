"""
Database Merge Utility
======================
Merges job_posts from one SQLite database into another.
Useful for combining scraped jobs from Windows PC with Pi database.

Usage:
    python merge_databases.py target.db source.db
    
Example:
    python merge_databases.py justmailit.db linkedin_jobs.db
"""

import sqlite3
import sys
import os
from datetime import datetime

def merge_databases(target_db, source_db, dry_run=False):
    """
    Merge job_posts from source_db into target_db
    
    Args:
        target_db: Path to target database (will be modified)
        source_db: Path to source database (read-only)
        dry_run: If True, only show what would be done
    """
    
    if not os.path.exists(target_db):
        print(f"❌ Target database not found: {target_db}")
        return False
    
    if not os.path.exists(source_db):
        print(f"❌ Source database not found: {source_db}")
        return False
    
    print("\n" + "="*60)
    print("🔄 DATABASE MERGE UTILITY")
    print("="*60)
    print(f"Target: {target_db}")
    print(f"Source: {source_db}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify target)'}")
    print("="*60 + "\n")
    
    try:
        # Connect to both databases
        target_conn = sqlite3.connect(target_db)
        target_cursor = target_conn.cursor()
        
        source_conn = sqlite3.connect(source_db)
        source_conn.row_factory = sqlite3.Row
        source_cursor = source_conn.cursor()
        
        # Get stats before merge
        target_cursor.execute("SELECT COUNT(*) FROM job_posts")
        target_before = target_cursor.fetchone()[0]
        
        source_cursor.execute("SELECT COUNT(*) FROM job_posts")
        source_total = source_cursor.fetchone()[0]
        
        print(f"📊 Before Merge:")
        print(f"   Target database: {target_before} jobs")
        print(f"   Source database: {source_total} jobs")
        print()
        
        # Get all jobs from source
        source_cursor.execute('''
            SELECT * FROM job_posts 
            ORDER BY created_at DESC
        ''')
        
        source_jobs = source_cursor.fetchall()
        
        # Track merge stats
        inserted = 0
        skipped_duplicate = 0
        skipped_email = 0
        errors = 0
        
        print(f"🔍 Processing {len(source_jobs)} jobs from source...\n")
        
        # Process each job
        for job in source_jobs:
            try:
                recruiter_email = job['recruiter_email']
                
                # Skip if no email
                if not recruiter_email:
                    skipped_email += 1
                    continue
                
                # Check if already exists in target (by recruiter_email and similar date)
                target_cursor.execute('''
                    SELECT id FROM job_posts 
                    WHERE recruiter_email = ?
                    AND date(created_at) = date(?)
                ''', (recruiter_email, job['created_at']))
                
                if target_cursor.fetchone():
                    skipped_duplicate += 1
                    print(f"   ⏭️  Skipped (duplicate): {recruiter_email}")
                    continue
                
                # Insert into target
                if not dry_run:
                    target_cursor.execute('''
                        INSERT INTO job_posts 
                        (user_email, title, company, location, job_url, recruiter_email, skills, full_text, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        job['user_email'],
                        job['title'],
                        job['company'],
                        job['location'],
                        job['job_url'],
                        job['recruiter_email'],
                        job['skills'],
                        job['full_text'],
                        job['created_at']
                    ))
                
                inserted += 1
                print(f"   ✅ Inserted: {recruiter_email} @ {job['company']}")
                
            except Exception as e:
                errors += 1
                print(f"   ❌ Error: {e}")
        
        # Commit changes
        if not dry_run:
            target_conn.commit()
        
        # Get stats after merge
        target_cursor.execute("SELECT COUNT(*) FROM job_posts")
        target_after = target_cursor.fetchone()[0]
        
        # Print summary
        print("\n" + "="*60)
        print("📊 MERGE SUMMARY")
        print("="*60)
        print(f"Source Jobs Processed: {len(source_jobs)}")
        print(f"Inserted: {inserted}")
        print(f"Skipped (duplicate): {skipped_duplicate}")
        print(f"Skipped (no email): {skipped_email}")
        print(f"Errors: {errors}")
        print()
        print(f"Target Before: {target_before} jobs")
        print(f"Target After: {target_after} jobs")
        print(f"Net Change: +{target_after - target_before} jobs")
        
        if dry_run:
            print("\n⚠️  DRY RUN - No changes were made")
        else:
            print("\n✅ Merge completed successfully")
        
        print("="*60 + "\n")
        
        # Close connections
        source_conn.close()
        target_conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def backup_database(db_path):
    """Create backup of database before merge"""
    if not os.path.exists(db_path):
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup created: {backup_path}\n")
        return backup_path
    except Exception as e:
        print(f"⚠️  Backup failed: {e}\n")
        return None

def main():
    """Main function with CLI"""
    if len(sys.argv) < 3:
        print("Usage: python merge_databases.py target.db source.db [--dry-run]")
        print()
        print("Arguments:")
        print("  target.db   Path to target database (will be modified)")
        print("  source.db   Path to source database (read-only)")
        print("  --dry-run   Show what would be done without making changes")
        print()
        print("Example:")
        print("  python merge_databases.py justmailit.db linkedin_jobs.db")
        print("  python merge_databases.py justmailit.db linkedin_jobs.db --dry-run")
        print()
        sys.exit(1)
    
    target_db = sys.argv[1]
    source_db = sys.argv[2]
    dry_run = '--dry-run' in sys.argv
    
    # Confirm before proceeding (unless dry-run)
    if not dry_run:
        print(f"\n⚠️  WARNING: This will modify {target_db}")
        print("   A backup will be created automatically")
        response = input("\nProceed? (yes/no): ")
        
        if response.lower() not in ['yes', 'y']:
            print("❌ Cancelled by user")
            sys.exit(0)
        
        # Create backup
        backup_database(target_db)
    
    # Run merge
    success = merge_databases(target_db, source_db, dry_run=dry_run)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
