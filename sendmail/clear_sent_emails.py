"""
clear_sent_emails.py

Safe, one-off script to delete all documents from the `sent_emails` Firestore collection.
Usage:
  - Dry run (shows how many docs):
      python clear_sent_emails.py
  - Confirmed run (no prompt):
      python clear_sent_emails.py --yes

IMPORTANT: This permanently deletes documents in Firestore. Use carefully.
"""
import os
import sys
import time
import argparse

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except Exception as e:
    print("❌ firebase_admin is not installed or cannot be imported:", e)
    sys.exit(1)

def get_creds_path():
    # Look for the credentials file shipped in the sendmail folder
    base = os.path.dirname(__file__)
    candidates = [
        os.path.join(base, 'linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json'),
        os.path.join(base, 'firebase-credentials.json'),
        os.path.join(base, 'linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json')
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def init_firebase(cred_path):
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print(f"✅ Firebase initialized using: {cred_path}")
        else:
            print("✅ Firebase already initialized")
        return firestore.client()
    except Exception as e:
        print("❌ Failed to initialize Firebase:", e)
        raise


def count_docs(db, collection_name):
    try:
        coll = db.collection(collection_name)
        docs = list(coll.limit(1).stream())
        if not docs:
            return 0
        # If there is at least one doc, count in batches (best-effort)
        # WARNING: Counting large collections this way can be slow. We do batch deletes regardless.
        count = 0
        for d in coll.stream():
            count += 1
        return count
    except Exception as e:
        print("❌ Error counting documents:", e)
        return -1


def delete_collection(db, collection_name, batch_size=200):
    coll_ref = db.collection(collection_name)
    deleted = 0
    while True:
        docs = list(coll_ref.limit(batch_size).stream())
        if not docs:
            break
        for doc in docs:
            try:
                print(f"- Deleting document {doc.id}")
                coll_ref.document(doc.id).delete()
                deleted += 1
            except Exception as e:
                print(f"⚠️ Failed to delete {doc.id}: {e}")
        # small pause to avoid hammering
        time.sleep(0.2)
    return deleted


def main():
    parser = argparse.ArgumentParser(description='Clear Firestore sent_emails collection')
    parser.add_argument('--yes', action='store_true', help='Proceed without prompting')
    parser.add_argument('--collection', default='sent_emails', help='Collection name to delete (default: sent_emails)')
    args = parser.parse_args()

    cred_path = get_creds_path()
    if not cred_path:
        print('❌ Could not find Firebase credentials in the sendmail folder. Please place your service account JSON there.')
        sys.exit(1)

    try:
        db = init_firebase(cred_path)
    except Exception:
        sys.exit(1)

    collection_name = args.collection
    print(f"🔍 Target collection: {collection_name}")

    # Count docs (best-effort)
    try:
        docs_preview = list(db.collection(collection_name).limit(3).stream())
        if docs_preview:
            print(f"ℹ️ Example document id: {docs_preview[0].id}")
        total = count_docs(db, collection_name)
    except Exception as e:
        print("❌ Could not query collection:", e)
        total = -1

    if total == 0:
        print("✅ Collection appears empty — nothing to delete.")
        sys.exit(0)
    elif total < 0:
        print("⚠️ Unable to determine total document count. Will proceed with deletion if confirmed.")
    else:
        print(f"⚠️ Found approximately {total} documents in '{collection_name}'.")

    if not args.yes:
        confirm = input('Type YES to confirm permanent deletion of all documents in this collection: ')
        if confirm != 'YES':
            print('Aborted by user.')
            sys.exit(0)

    print('🗑️ Deleting documents...')
    deleted = delete_collection(db, collection_name)
    print(f"✅ Deleted {deleted} documents from '{collection_name}'")

    # Verify
    remaining = count_docs(db, collection_name)
    print(f"📊 Remaining documents after deletion: {remaining if remaining>=0 else 'unknown'}")

if __name__ == '__main__':
    main()
