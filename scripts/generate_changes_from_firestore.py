"""
Fetch job posts from Firestore, run JobAnalyzer, and export changed rows for review.
This script uses the service account JSON present in sendmail/ by default.

Outputs:
 - scripts/changed_rows_firestore.json
 - scripts/changed_rows_firestore.csv

Run from project root.
"""
import os
import sys
import json
import csv

ROOT = os.path.dirname(os.path.dirname(__file__))
# Ensure sendmail package is importable
sys.path.insert(0, os.path.join(ROOT, 'sendmail'))

try:
    from job_analyzer import JobAnalyzer
except Exception as e:
    print(f"❌ Could not import JobAnalyzer: {e}")
    raise

# Firestore imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except Exception as e:
    print(f"❌ firebase_admin not available: {e}")
    firebase_admin = None


def get_service_account_path():
    # Default path in the repo
    candidates = [
        os.path.join(ROOT, 'sendmail', 'linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json'),
        os.path.join(ROOT, 'sendmail', 'linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json'.replace('linkedin','')), # fallback
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def main():
    sa_path = get_service_account_path()
    if not sa_path:
        print("❌ No service account JSON found in sendmail/. Please provide a path to your Firebase service account JSON.")
        return

    if firebase_admin is None:
        print("❌ firebase_admin not installed in the environment. Install with 'pip install firebase-admin' and try again.")
        return

    try:
        cred = credentials.Certificate(sa_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        print(f"❌ Failed to initialize Firestore client: {e}")
        return

    analyzer = JobAnalyzer()

    try:
        docs = list(db.collection('job_posts').stream())
    except Exception as e:
        print(f"❌ Failed to query 'job_posts' collection: {e}")
        return

    total = len(docs)
    print(f"🔍 Retrieved {total} documents from Firestore 'job_posts' collection")

    changed = []
    for doc in docs:
        data = doc.to_dict()
        original_company = data.get('company')
        original_location = data.get('location')

        analyzed = analyzer.analyze_post(data.copy())
        new_company = analyzed.get('company')
        new_location = analyzed.get('location')

        if (original_company != new_company) or (original_location != new_location):
            out = {
                'id': doc.id,
                'original_company': original_company,
                'new_company': new_company,
                'original_location': original_location,
                'new_location': new_location,
                'title': data.get('title') or analyzed.get('title'),
                'email': data.get('email')
            }
            changed.append(out)

    # Write outputs
    out_json = os.path.join(ROOT, 'scripts', 'changed_rows_firestore.json')
    out_csv = os.path.join(ROOT, 'scripts', 'changed_rows_firestore.csv')

    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(changed, f, indent=2, ensure_ascii=False)

    if changed:
        keys = ['id','title','email','original_company','new_company','original_location','new_location']
        with open(out_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in changed:
                writer.writerow(r)

    print(f"✅ Analysis complete. Total={total} Changed={len(changed)}")
    print(f"Outputs:\n - {out_json}\n - {out_csv if changed else '(csv omitted because no changes)'}")


if __name__ == '__main__':
    main()
