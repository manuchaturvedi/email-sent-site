from datetime import datetime, date
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate('sendmail/linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json')
try:
    firebase_admin.initialize_app(cred)
except:
    pass

db = firestore.client()
today = date.today()

# Test user
user_email = 'siddheya314@gmail.com'

# Get all sent emails for this user
emails = list(db.collection('sent_emails').where('user_email', '==', user_email).where('status', '==', 'sent').stream())

print(f"\n📊 Total emails in database: {len(emails)}")

# Count today's emails
count_today = 0
for email_doc in emails:
    email_data = email_doc.to_dict()
    timestamp = email_data.get('sent_at') or email_data.get('timestamp') or email_data.get('created_at')
    
    if timestamp:
        try:
            if isinstance(timestamp, datetime):
                if timestamp.date() == today:
                    count_today += 1
                    print(f"✅ Today: {email_data.get('email')} at {timestamp}")
            elif isinstance(timestamp, str):
                try:
                    sent_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                    if sent_date == today:
                        count_today += 1
                        print(f"✅ Today: {email_data.get('email')} at {timestamp}")
                except:
                    pass
        except Exception as e:
            print(f"⚠️ Error parsing: {e}")

print(f"\n📧 Emails sent TODAY: {count_today}/10")
print(f"{'🔒 LIMIT REACHED - Should block!' if count_today >= 10 else '✅ Can still send'}")

# Check subscription
user_doc = db.collection('user_profiles').document(user_email).get()
if user_doc.exists:
    user_data = user_doc.to_dict()
    subscription = user_data.get('subscription', {})
    plan = subscription.get('plan', 'free')
    print(f"💳 Current plan: {plan}")
else:
    print("⚠️ No user profile found")
