from firebase_admin import credentials, firestore
import firebase_admin
import datetime

# Use existing cred path
cred = credentials.Certificate("D:/linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json")
firebase_admin.initialize_app(cred)

# Try to write to Firestore
db = firestore.client()
test_doc = {
    'email': 'test@example.com',
    'subject': 'Test Connection',
    'sent_at': datetime.datetime.now(),
    'status': 'test'
}

try:
    # Write the test document
    doc_ref = db.collection('sent_emails').add(test_doc)
    print("✅ Successfully wrote test document to Firestore")
    
    # Try to read it back
    docs = db.collection('sent_emails').where('status', '==', 'test').limit(1).get()
    for doc in docs:
        print(f"✅ Successfully read test document: {doc.to_dict()}")
    
except Exception as e:
    print(f"❌ Firestore test failed: {str(e)}")