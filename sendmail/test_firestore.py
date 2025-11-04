from firebase_admin import credentials, firestore
import firebase_admin
import datetime

print("1. Loading credentials...")
cred = credentials.Certificate("D:/linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json")

print("2. Initializing Firebase app...")
try:
    firebase_admin.initialize_app(cred)
except ValueError:
    # App might already be initialized
    pass

print("3. Getting Firestore client...")
db = firestore.client()

print("4. Listing existing sent_emails documents...")
docs = db.collection('sent_emails').limit(5).get()
for doc in docs:
    print(f"Found document: {doc.id} => {doc.to_dict()}")

print("\nFirestore connection test complete!")