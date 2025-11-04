from firebase_admin import firestore
from datetime import datetime
import json
import os

SENT_EMAILS_FILE = 'sent_emails.json'

class FirestoreOps:
    def __init__(self):
        self.db = firestore.client()
    
    def save_email(self, record, run_id=None, user_email=None):
        """Save email record to Firestore."""
        try:
            # Add metadata
            if user_email:
                record['user_email'] = user_email
            if run_id:
                record['run_id'] = run_id
                record['run_time'] = datetime.now().isoformat()
            
            # Save to Firestore
            doc_ref = self.db.collection('sent_emails').document()
            record['created_at'] = firestore.SERVER_TIMESTAMP
            doc_ref.set(record)
            
            # Update run statistics
            if run_id:
                run_ref = self.db.collection('automation_runs').document(run_id)
                if record.get('status') == 'sent':
                    run_ref.update({
                        'successful': firestore.Increment(1),
                        'total_emails': firestore.Increment(1)
                    })
                elif record.get('status') == 'failed':
                    run_ref.update({
                        'failed': firestore.Increment(1),
                        'total_emails': firestore.Increment(1)
                    })
            
            return True
            
        except Exception as e:
            print(f"❌ Firestore error: {str(e)}")
            return False
    
    def get_user_emails(self, user_email):
        """Get all emails for a user."""
        try:
            # Simple query with just user_email filter
            docs = self.db.collection('sent_emails')\
                .where(filter=firestore.FieldFilter('user_email', '==', user_email))\
                .stream()
            
            emails = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                emails.append(data)
            
            # Sort in memory
            emails.sort(key=lambda x: x.get('created_at', x.get('sent_at', '')), reverse=True)
            return emails
            
        except Exception as e:
            print(f"❌ Error loading from Firestore: {str(e)}")
            return self.get_local_emails(user_email)
    
    def get_local_emails(self, user_email=None):
        """Fallback to load emails from local storage."""
        try:
            with open(SENT_EMAILS_FILE, 'r') as f:
                all_emails = json.load(f)
                if user_email:
                    return [e for e in all_emails if e.get('user_email') == user_email]
                return all_emails
        except FileNotFoundError:
            return []
    
    def save_automation_run(self, run_id, user_email, settings=None):
        """Initialize an automation run record."""
        try:
            run_data = {
                'user_email': user_email,
                'start_time': firestore.SERVER_TIMESTAMP,
                'status': 'running',
                'settings': settings or {},
                'total_emails': 0,
                'successful': 0,
                'failed': 0
            }
            self.db.collection('automation_runs').document(run_id).set(run_data)
            return True
        except Exception as e:
            print(f"❌ Error saving automation run: {str(e)}")
            return False
    
    def complete_automation_run(self, run_id, stats):
        """Mark an automation run as completed."""
        try:
            self.db.collection('automation_runs').document(run_id).update({
                'end_time': firestore.SERVER_TIMESTAMP,
                'status': 'completed',
                **stats
            })
            return True
        except Exception as e:
            print(f"❌ Error updating automation run: {str(e)}")
            return False