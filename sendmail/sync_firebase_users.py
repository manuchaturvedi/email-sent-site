"""
Sync Firebase users to SQLite database.
Run this script to onboard existing Firebase users into the database.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database
import firebase_admin
from firebase_admin import credentials, auth

def sync_firebase_users_to_db():
    """Sync all Firebase users to SQLite database"""
    
    # Initialize database
    db_path = os.path.join(os.path.dirname(__file__), '..', 'justmailit.db')
    db_path = os.path.abspath(db_path)
    print(f"[SYNC] Using database: {db_path}")
    db = Database(db_path=db_path)
    
    # Initialize Firebase Admin SDK
    try:
        cred_path = os.path.join(os.path.dirname(__file__), 
                                 "justmailit-d6f2d-firebase-adminsdk-fbsvc-552f0c36ab.json")
        
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            print(f"[SYNC] Firebase initialized")
        else:
            print(f"[ERROR] Firebase credentials not found at: {cred_path}")
            return
    except Exception as e:
        print(f"[ERROR] Failed to initialize Firebase: {e}")
        return
    
    # Get all Firebase users
    try:
        print("[SYNC] Fetching all Firebase users...")
        page = auth.list_users()
        users_synced = 0
        users_skipped = 0
        users_total = 0
        
        while page:
            for user in page.users:
                users_total += 1
                email = user.email
                display_name = user.display_name or ""
                photo_url = user.photo_url or ""
                
                print(f"\n[SYNC] Processing user: {email}")
                
                # Check if user already exists in DB
                existing = db.get_profile(email)
                if existing:
                    print(f"  ✓ User already exists in database: {email}")
                    users_skipped += 1
                else:
                    # Create new profile
                    try:
                        db.create_or_update_profile(
                            email=email,
                            display_name=display_name,
                            photo_url=photo_url
                        )
                        print(f"  ✅ Added to database: {email} ({display_name})")
                        users_synced += 1
                        
                        # Verify
                        verify = db.get_profile(email)
                        if not verify:
                            print(f"  ❌ Verification failed for: {email}")
                    except Exception as e:
                        print(f"  ❌ Error adding user {email}: {e}")
            
            # Get next batch of users
            page = page.get_next_page()
        
        print(f"\n{'='*60}")
        print(f"[SYNC] Sync completed!")
        print(f"  Total Firebase users: {users_total}")
        print(f"  Newly synced: {users_synced}")
        print(f"  Already existed: {users_skipped}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch Firebase users: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("="*60)
    print("Firebase to Database User Sync")
    print("="*60)
    sync_firebase_users_to_db()
