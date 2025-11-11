"""
Firestore Operations Module - Simplified version for cloud deployment
Handles Firebase Firestore operations for the email automation app
"""

import os
from datetime import datetime

# Try to import Firebase/Firestore
try:
    import firebase_admin
    from firebase_admin import firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    print("⚠️ Firebase not available - using local storage fallback")


class FirestoreOps:
    """Handles Firestore operations with fallback to local storage"""
    
    def __init__(self):
        """Initialize Firestore operations"""
        self.db = None
        if FIRESTORE_AVAILABLE:
            try:
                self.db = firestore.client()
                print("✅ Firestore client initialized")
            except Exception as e:
                print(f"⚠️ Firestore initialization failed: {e}")
                self.db = None
    
    def save_automation_run(self, run_id, user_email, settings=None):
        """
        Save automation run data to Firestore
        
        Args:
            run_id: Unique identifier for the automation run
            user_email: Email of the user who initiated the run
            settings: Dictionary of settings used for this run
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.db is not None:
                run_data = {
                    'user_email': user_email,
                    'start_time': firestore.SERVER_TIMESTAMP,
                    'status': 'running',
                    'settings_used': settings or {},
                    'total_emails': 0,
                    'successful': 0,
                    'failed': 0,
                    'run_id': run_id,
                    'created_at': datetime.now().isoformat()
                }
                
                doc_ref = self.db.collection('automation_runs').document(run_id)
                doc_ref.set(run_data)
                print(f"✅ Automation run {run_id} saved to Firestore")
                return True
            else:
                print(f"⚠️ Firestore not available - automation run {run_id} not saved")
                return False
                
        except Exception as e:
            print(f"❌ Error saving automation run {run_id}: {e}")
            return False
    
    def update_automation_run(self, run_id, stats):
        """
        Update automation run statistics in Firestore
        
        Args:
            run_id: Automation run ID
            stats: Dictionary with statistics to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.db is not None:
                update_data = stats.copy()
                update_data['end_time'] = firestore.SERVER_TIMESTAMP
                update_data['status'] = 'completed'
                update_data['updated_at'] = datetime.now().isoformat()
                
                doc_ref = self.db.collection('automation_runs').document(run_id)
                doc_ref.update(update_data)
                print(f"✅ Automation run {run_id} updated in Firestore")
                return True
            else:
                print(f"⚠️ Firestore not available - automation run {run_id} not updated")
                return False
                
        except Exception as e:
            print(f"❌ Error updating automation run {run_id}: {e}")
            return False
    
    def get_automation_runs(self, user_email, limit=10):
        """
        Get automation runs for a user
        
        Args:
            user_email: User's email address
            limit: Maximum number of runs to return
            
        Returns:
            list: List of automation run records
        """
        try:
            if self.db is not None:
                query = (self.db.collection('automation_runs')
                        .where('user_email', '==', user_email)
                        .limit(limit))
                
                docs = list(query.stream())
                runs = []
                
                for doc in docs:
                    run_data = doc.to_dict()
                    run_data['id'] = doc.id
                    runs.append(run_data)
                
                # Sort by start time descending
                runs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                print(f"✅ Retrieved {len(runs)} automation runs for {user_email}")
                return runs
            else:
                print(f"⚠️ Firestore not available - no automation runs retrieved")
                return []
                
        except Exception as e:
            print(f"❌ Error getting automation runs for {user_email}: {e}")
            return []
    
    def save_job_post(self, job_post):
        """
        Save a job post to Firestore
        
        Args:
            job_post: Dictionary containing job post data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.db is not None:
                # Add timestamps
                job_post_data = job_post.copy()
                job_post_data.update({
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'status': 'active'
                })
                
                doc_ref = self.db.collection('job_posts').document()
                doc_ref.set(job_post_data)
                print(f"✅ Job post saved to Firestore: {job_post.get('title', 'Unknown')}")
                return True
            else:
                print(f"⚠️ Firestore not available - job post not saved")
                return False
                
        except Exception as e:
            print(f"❌ Error saving job post: {e}")
            return False
    
    def save_sent_email(self, email_record):
        """
        Save sent email record to Firestore
        
        Args:
            email_record: Dictionary containing email record data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.db is not None:
                # Add timestamps
                email_data = email_record.copy()
                email_data.update({
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'timestamp': datetime.now().isoformat()
                })
                
                doc_ref = self.db.collection('sent_emails').document()
                doc_ref.set(email_data)
                print(f"✅ Email record saved to Firestore: {email_record.get('email', 'Unknown')}")
                return True
            else:
                print(f"⚠️ Firestore not available - email record not saved")
                return False
                
        except Exception as e:
            print(f"❌ Error saving email record: {e}")
            return False
    
    def get_user_stats(self, user_email):
        """
        Get user statistics from Firestore
        
        Args:
            user_email: User's email address
            
        Returns:
            dict: User statistics
        """
        try:
            if self.db is not None:
                # Get sent emails count
                sent_emails_query = (self.db.collection('sent_emails')
                                   .where('user_email', '==', user_email))
                sent_emails = list(sent_emails_query.stream())
                
                # Calculate stats
                stats = {
                    'total_emails': len(sent_emails),
                    'sent': sum(1 for email in sent_emails if email.to_dict().get('status') == 'sent'),
                    'failed': sum(1 for email in sent_emails if email.to_dict().get('status') == 'failed'),
                    'skipped': sum(1 for email in sent_emails if email.to_dict().get('status') == 'skipped'),
                }
                
                print(f"✅ Retrieved stats for {user_email}: {stats}")
                return stats
            else:
                print(f"⚠️ Firestore not available - no stats retrieved")
                return {'total_emails': 0, 'sent': 0, 'failed': 0, 'skipped': 0}
                
        except Exception as e:
            print(f"❌ Error getting user stats for {user_email}: {e}")
            return {'total_emails': 0, 'sent': 0, 'failed': 0, 'skipped': 0}
    
    def is_available(self):
        """Check if Firestore is available and initialized"""
        return self.db is not None


# Global instance for easy import
firestore_ops = FirestoreOps()