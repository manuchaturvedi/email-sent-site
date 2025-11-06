import json
import os
from firebase_admin import credentials, firestore, initialize_app

def delete_job_posts():
    """Delete all job posts from both Firestore and local storage."""
    # Path to your job posts file
    JOB_POSTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'job_posts.json')
    
    try:
        # Initialize Firebase Admin SDK
        cred_path = os.path.join(os.path.dirname(__file__), "linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json")
        print(f"🔑 Loading Firebase credentials from: {cred_path}")
        
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            try:
                initialize_app(cred)
            except ValueError:
                # App already initialized
                pass

            # Delete from Firestore
            db = firestore.client()
            job_posts_collection = 'job_posts'  # Collection name for job posts
            
            # Get all documents in the job_posts collection
            docs = db.collection(job_posts_collection).stream()
            batch = db.batch()
            deleted_count = 0
            
            for doc in docs:
                batch.delete(doc.reference)
                deleted_count += 1
            
            if deleted_count > 0:
                batch.commit()
                print(f"✅ Deleted {deleted_count} job posts from Firestore")
            else:
                print("ℹ️ No job posts found in Firestore")
        else:
            print("⚠️ Firebase credentials file not found, skipping Firestore deletion")

    except Exception as e:
        print(f"❌ Error with Firestore: {str(e)}")

    # Clear local storage
    try:
        # Create empty job posts file
        with open(JOB_POSTS_FILE, 'w') as f:
            json.dump([], f)
        print("✅ Cleared local job posts storage")
        
    except Exception as e:
        print(f"❌ Error clearing local storage: {str(e)}")

if __name__ == "__main__":
    # Ask for confirmation
    response = input("⚠️ This will delete ALL job posts from both Firestore and local storage. Are you sure? (yes/no): ")
    if response.lower() == 'yes':
        delete_job_posts()
        print("✅ Job posts deletion complete")
    else:
        print("❌ Operation cancelled")