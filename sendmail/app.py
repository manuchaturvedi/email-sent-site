from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Response
from functools import wraps
import firebase_admin
from firebase_admin import credentials, auth
from job_analyzer import JobAnalyzer
# Firestore and Storage are optional; we'll import if available at runtime
try:
    from firebase_admin import firestore, storage
    from firebase_admin.firestore import FieldFilter  # Add FieldFilter import
except Exception:
    firestore = None
    storage = None
    FieldFilter = None
import base64
import threading
from queue import Queue, Empty
import os
import smtplib
import time
import tempfile
import shutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import json
import platform


app = Flask(__name__)

# Server-Sent Events clients (each client gets a Queue)
clients = []
clients_lock = threading.Lock()

def cleanup_chrome_processes():
    """Cross-platform Chrome process cleanup"""
    try:
        system = platform.system().lower()
        if system == "windows":
            os.system('taskkill /f /im chrome.exe')
        else:
            # Linux/Unix systems (including Render)
            os.system('pkill -f chrome || killall chrome || true')
        print("🧹 Chrome processes cleaned up")
    except Exception as e:
        print(f"⚠️ Chrome cleanup failed: {e}")

def send_event(message: str):
    """Push a message to all connected SSE clients."""
    with clients_lock:
        for q in list(clients):
            try:
                q.put(message)
            except Exception:
                # If a client queue is broken, ignore and continue
                continue

def log(message: str):
    """Unified logger that writes to console and sends SSE events."""
    try:
        print(message)
    except Exception:
        pass
    try:
        send_event(message)
    except Exception:
        pass

# Initialize job posts storage
JOB_POSTS_FILE = 'job_posts.json'
SENT_EMAILS_FILE = 'sent_emails.json'

# Optional persistent Chrome profile directory helps preserve LinkedIn login state.
_env_profile = os.getenv("CHROME_PROFILE_DIR")
_default_profile = r"D:\Profile"
if _env_profile:
    CHROME_PROFILE_DIR = _env_profile
elif os.path.exists(_default_profile):
    CHROME_PROFILE_DIR = _default_profile
else:
    CHROME_PROFILE_DIR = None

# LinkedIn credentials for programmatic login (fallback)
LINKEDIN_EMAIL = "manudrive04@gmail.com"
LINKEDIN_PASSWORD = "Jpking@232"

# Global variables for 2FA handling
automation_driver = None
verification_code_submitted = None
verification_code_value = None

def is_duplicate_job_post(post, existing_posts=None):
    """Check if a job post is a duplicate based on email, title, and company."""
    try:
        if firestore is not None:
            db = firestore.client()
            # Query Firestore for potential duplicates
            query = (db.collection(FIRESTORE_COLLECTIONS['job_posts'])
                    .where('email', '==', post.get('email', ''))
                    .where('company', '==', post.get('company', '')))
            
            docs = list(query.stream())
            for doc in docs:
                existing = doc.to_dict()
                # Consider it a duplicate if title is similar (to handle minor variations)
                if (existing.get('email') == post.get('email') and
                    existing.get('company') == post.get('company') and
                    existing.get('title', '').lower().strip() == post.get('title', '').lower().strip()):
                    return True
            return False
        
        # Fallback to local storage check
        if existing_posts is None:
            existing_posts = load_job_posts()
        
        for existing in existing_posts:
            if (existing.get('email') == post.get('email') and
                existing.get('company') == post.get('company') and
                existing.get('title', '').lower().strip() == post.get('title', '').lower().strip()):
                return True
        return False
        
    except Exception as e:
        print(f"❌ Error checking for duplicate job post: {str(e)}")
        # If we can't check duplicates, assume it's not a duplicate
        return False

def load_job_posts():
    """Load job posts from Firestore or fall back to local JSON storage."""
    # Initialize job analyzer
    analyzer = JobAnalyzer()

    try:
        if firestore is not None:
            db = firestore.client()
            docs = list(db.collection(FIRESTORE_COLLECTIONS['job_posts']).stream())

            posts = []
            for doc in docs:
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                # Analyze post to extract company, location, and skills
                posts.append(analyzer.analyze_post(post_data))

            # Sort by posted_date descending
            posts.sort(key=lambda x: x.get('posted_date', ''), reverse=True)
            print(f"✅ Loaded {len(posts)} job posts from Firestore")
            return posts

    except Exception as e:
        print(f"❌ Error loading from Firestore: {str(e)}")
        # Continue to try local storage

    try:
        with open(JOB_POSTS_FILE, 'r') as f:
            posts = json.load(f)
            # Analyze each post from local storage
            posts = [analyzer.analyze_post(post) for post in posts]
            print(f"✅ Loaded {len(posts)} job posts from local storage")
            return posts
    except FileNotFoundError:
        return []

def save_job_post(post):
    """Save a job post to Firestore and local storage, avoiding duplicates."""
    try:
        # First check if this is a duplicate
        if is_duplicate_job_post(post):
            print(f"⚠️ Duplicate job post found for {post.get('company')} - {post.get('title')}")
            return False
            
        # Try Firestore first
        if firestore is not None:
            db = firestore.client()
            try:
                # Add timestamp and clean up post data
                post_to_save = post.copy()
                post_to_save.update({
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'posted_date': post.get('posted_date') or datetime.now().strftime("%Y-%m-%d"),
                    'status': 'active'
                })
                
                # Save to Firestore
                doc_ref = db.collection(FIRESTORE_COLLECTIONS['job_posts']).document()
                doc_ref.set(post_to_save)
                
                # Verify the save
                saved_doc = doc_ref.get()
                if saved_doc.exists:
                    print(f"✅ Job post saved to Firestore with ID: {doc_ref.id}")
                    
                    # Notify connected clients
                    try:
                        send_event(f"NEW_JOB: {post.get('title')} | {post.get('company')} | {post.get('email')}")
                    except Exception:
                        pass
                    
                    return True
                else:
                    print("⚠️ Warning: Job post save to Firestore could not be verified")
                    
            except Exception as e:
                print(f"❌ Error saving to Firestore: {str(e)}")
                # Continue to local storage as fallback
        
        # Fallback to local storage
        try:
            posts = load_job_posts()
            posts.append(post)
            with open(JOB_POSTS_FILE, 'w') as f:
                json.dump(posts, f, indent=2)
                
            # Notify connected clients
            try:
                send_event(f"NEW_JOB: {post.get('title')} | {post.get('company')} | {post.get('email')}")
            except Exception:
                pass
                
            print(f"✅ Job post saved to local storage")
            return True
            
        except Exception as e:
            print(f"❌ Error saving to local storage: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ Error in save_job_post: {str(e)}")
        return False


def load_sent_emails(user_email=None):
    """Load sent emails for a specific user or all emails if no user specified.
    
    Args:
        user_email: Optional email to filter by user
    
    Returns:
        List of email records sorted by sent time
    """
    emails = []
    
    try:
        # Try to load from Firestore first
        if firestore is not None:
            db = firestore.client()
            try:
                # First try loading without ordering to avoid index requirement
                query = db.collection(FIRESTORE_COLLECTIONS['sent_emails'])
                if user_email:
                    query = query.where(filter=FieldFilter('user_email', '==', user_email))
                
                print(f"🔍 Querying Firestore collection: {FIRESTORE_COLLECTIONS['sent_emails']}")
                # Add more debug info about the query
                if user_email:
                    print(f"📧 Filtering by user_email: {user_email}")
                    
                try:
                    docs = list(query.stream())  # Convert to list to force execution
                    print(f"📊 Found {len(docs)} documents in Firestore")
                    
                    # If no documents found, try a simple query to verify collection access
                    if len(docs) == 0:
                        test_docs = list(db.collection(FIRESTORE_COLLECTIONS['sent_emails']).limit(1).stream())
                        if len(test_docs) > 0:
                            print("ℹ️ Note: Collection has documents but none match the filter")
                        else:
                            print("ℹ️ Note: Collection appears to be empty")
                except Exception as e:
                    print(f"❌ Error executing Firestore query: {str(e)}")
                    raise  # Re-raise to be caught by outer try/except
                
                print("📨 Processing Firestore documents...")
                for doc in docs:
                    try:
                        email_data = doc.to_dict()
                        if not email_data:
                            print(f"⚠️ Empty document found with ID: {doc.id}")
                            continue
                            
                        email_data['id'] = doc.id
                        
                        # Ensure we have required fields
                        if not email_data.get('email'):
                            print(f"⚠️ Skipping document {doc.id} - missing email field")
                            continue
                            
                        emails.append(email_data)
                    except Exception as e:
                        print(f"⚠️ Error processing document {doc.id}: {str(e)}")
                        continue
                
                print(f"✅ Successfully processed {len(emails)} valid email records")
                
                # Sort in memory instead of using Firestore ordering
                # Convert Firestore timestamps to isoformat strings for sorting
                for email in emails:
                    created_at = email.get('created_at')
                    if created_at and hasattr(created_at, 'isoformat'):
                        email['created_at'] = created_at.isoformat()
                    elif isinstance(created_at, str):
                        # Already a string, leave as is
                        pass
                    else:
                        # Use a default date for sorting if no valid date
                        email['created_at'] = '1970-01-01T00:00:00'

                emails.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                print(f"✅ Loaded {len(emails)} emails from Firestore")
                return emails
            except Exception as e:
                print(f"❌ Error loading from Firestore: {str(e)}")
                # Continue to try local storage
        
        # Fallback to local file
        try:
            with open(SENT_EMAILS_FILE, 'r') as f:
                all_emails = json.load(f)
                if user_email:
                    emails = [email for email in all_emails if email.get('user_email') == user_email]
                else:
                    emails = all_emails
                
                # Sort by sent time descending
                emails.sort(key=lambda x: x.get('sent_at', ''), reverse=True)
                print(f"✅ Loaded {len(emails)} emails from local storage")
                return emails
                
        except FileNotFoundError:
            print("ℹ️ No local email records found")
            return []
            
    except Exception as e:
        print(f"❌ Error in load_sent_emails: {str(e)}")
        return []


def get_user_email_stats(user_email):
    """Get user email statistics from Firestore with efficient querying."""
    try:
        if firestore is not None:
            db = firestore.client()
            # Avoid server-side ordering which can require a composite index.
            # Fetch documents for the user and sort in-memory to remove the
            # need for a composite index on (user_id, timestamp).
            try:
                base_query = db.collection(FIRESTORE_COLLECTIONS['sent_emails']).where('user_id', '==', user_email)
                docs = list(base_query.stream())
            except Exception as e:
                print(f"❌ Error executing Firestore query: {str(e)}")
                return None, {}

            # Prepare empty stats structure
            stats = {
                "sent": 0,
                "skipped": 0,
                "failed": 0,
                "duplicates": 0,
                "total": len(docs),
                "unique_recipients": set(),
                "unique_runs": set(),
                "last_run_time": None
            }

            processed_emails = []
            for doc in docs:
                try:
                    email_data = doc.to_dict() or {}
                    email_data['id'] = doc.id

                    # Normalize timestamp fields for comparisons
                    ts = email_data.get('timestamp') or email_data.get('created_at')
                    if ts and hasattr(ts, 'isoformat'):
                        # Firestore timestamp -> ISO string
                        email_data['timestamp'] = ts.isoformat()
                    elif isinstance(ts, str):
                        email_data['timestamp'] = ts
                    else:
                        email_data['timestamp'] = ''

                    # Update stats counters
                    status = email_data.get('status', 'unknown')
                    if status in stats:
                        stats[status] += 1

                    # Track unique values
                    if email_data.get('email'):
                        stats['unique_recipients'].add(email_data['email'])
                    if email_data.get('run_id'):
                        stats['unique_runs'].add(email_data['run_id'])

                    # Track latest run (string compare of ISO timestamps is OK)
                    timestamp = email_data.get('timestamp', '')
                    if timestamp and (not stats['last_run_time'] or timestamp > stats['last_run_time']):
                        stats['last_run_time'] = timestamp

                    processed_emails.append(email_data)
                except Exception as e:
                    print(f"⚠️ Error processing document {doc.id}: {str(e)}")
                    continue

            # Sort processed emails by timestamp descending
            processed_emails.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            # Convert sets to counts and finalize stats
            stats['unique_recipients'] = len(stats['unique_recipients'])
            stats['runs'] = len(stats['unique_runs'])
            stats['last_run'] = stats['last_run_time']
            del stats['unique_runs']
            del stats['last_run_time']

            print(f"✅ Processed {len(processed_emails)} email records for user {user_email}")
            return processed_emails, stats
    except Exception as e:
        print(f"❌ Error querying Firestore: {str(e)}")
        return None, {}

def prepare_email_record(record, run_id=None, user_email=None):
    """Prepare an email record for storage by adding necessary fields."""
    record_to_save = record.copy()
    record_to_save.update({
        'created_at': firestore.SERVER_TIMESTAMP if firestore else datetime.now().isoformat(),
        'user_id': user_email,
        'user_email': user_email,  # For backwards compatibility
        'run_id': run_id,
        'status': record.get('status', 'unknown'),
        'timestamp': datetime.now().isoformat(),
        'run_time': datetime.now().isoformat(),  # Add run_time for consistency
        'subject': record.get('subject', 'No Subject'),
        'email': record.get('email', ''),
        'action_type': record.get('status', 'unknown'),
        'error': record.get('error', None),  # Store any error messages
        'metadata': {  # Additional metadata for analysis
            'client_time': datetime.now().isoformat(),
            'source': 'automation',
            'version': '1.0'
        }
    })
    return record_to_save

def save_sent_email(record, run_id=None, user_email=None):
    """Save a single sent-email record locally and to Firestore."""
    try:
        # Add user information
        if user_email:
            record['user_email'] = user_email
        
        # Add run information
        if run_id:
            record['run_id'] = run_id
            record['run_time'] = datetime.now().isoformat()
        
        # First try Firestore
        if firestore is not None:
            db = firestore.client()
            
            try:
                print("🔍 Checking Firestore for existing record...")
                
                # Save or update in Firestore
                try:
                    # Always create a new record with timestamp
                    doc_ref = db.collection(FIRESTORE_COLLECTIONS['sent_emails']).document()
                    
                    # Clean up and prepare the record for storage
                    record_to_save = prepare_email_record(record, run_id, user_email)
                    doc_ref.set(record_to_save)
                    # Notify connected clients about the new email
                    try:
                        send_event(f"NEW_EMAIL: {record_to_save.get('email')} | {record_to_save.get('status')} | {record_to_save.get('run_id')}")
                    except Exception:
                        pass
                    
                    # Update automation run statistics
                    if run_id:
                        run_ref = db.collection(FIRESTORE_COLLECTIONS['automation_runs']).document(run_id)
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
                    
                    print(f"✅ Saved email record to Firestore: {record.get('email')}")
                    # Force a read back to verify
                    verify_query = db.collection(FIRESTORE_COLLECTIONS['sent_emails']).document(doc_ref.id).get()
                    if verify_query.exists:
                        print(f"✅ Verified record exists in Firestore with ID: {doc_ref.id}")
                    else:
                        print(f"⚠️ Warning: Record save succeeded but verification failed")
                    
                    return True
                except Exception as e:
                    print(f"❌ Error in Firestore operation: {str(e)}")
                    return False

            except Exception as e:
                print(f"❌ Error saving to Firestore: {str(e)}")
                # Continue to local storage as fallback
        # Fallback to local storage
        try:
            existing = load_sent_emails()
            
            # Check for duplicates in local storage
            for r in existing:
                if (r.get('email') == record.get('email') and 
                    r.get('subject') == record.get('subject') and
                    r.get('run_id') == record.get('run_id') and
                    r.get('user_email') == record.get('user_email')):
                    print(f"⚠️ Duplicate email record found in local storage: {record.get('email')}")
                    return False
            
            # No duplicate found, append and save
            existing.append(record)
            with open(SENT_EMAILS_FILE, 'w') as f:
                json.dump(existing, f, default=str, indent=2)
                
            # Try to notify connected clients
            try:
                send_event(f"NEW_EMAIL: {record.get('email')} | {record.get('status')}")
            except Exception:
                pass
                
            print(f"✅ Saved email record to local storage: {record.get('email')}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving to local storage: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ Error in save_sent_email: {str(e)}")
        return False
    try:
        send_event(f"SENT_EMAIL: {record.get('email')} | {record.get('subject')}")
    except Exception:
        pass

    return True
app.secret_key = "super-secret-key-change-this"

# Initialize Firebase Admin SDK
# Initialize Firebase with credentials (cloud-compatible)
import base64
import json

def initialize_firebase():
    """Initialize Firebase with environment variable or local file"""
    try:
        # Try environment variable first (for cloud deployment)
        firebase_json_b64 = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        
        if firebase_json_b64:
            print("🔑 Loading Firebase credentials from environment variable")
            # Decode base64 and parse JSON
            firebase_json_str = base64.b64decode(firebase_json_b64).decode('utf-8')
            firebase_config = json.loads(firebase_json_str)
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized from environment variable")
            return True
            
        else:
            # Fallback to local file (for development)
            cred_path = os.path.join(os.path.dirname(__file__), "linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json")
            if os.path.exists(cred_path):
                print(f"🔑 Loading Firebase credentials from local file: {cred_path}")
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("✅ Firebase initialized from local file")
                return True
            else:
                print("⚠️ No Firebase credentials found - running without Firebase")
                return False
                
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        return False

# Initialize Firebase
firebase_initialized = initialize_firebase()

# Initialize Firestore operations
from firestore_ops import FirestoreOps
db_ops = FirestoreOps() if firebase_initialized else None


# --- LOGIN CONTROL ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please log in first!", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/sessionLogin", methods=["POST"])
def session_login():
    data = request.get_json()
    id_token = data.get("idToken")
    try:
        decoded_token = auth.verify_id_token(id_token)
        user_email = decoded_token["email"]
        session["user"] = user_email
        print(f"✅ {user_email} logged in successfully!")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return jsonify({"error": str(e)}), 401


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


# --- MAIN PAGE ---
@app.route("/profile")
@login_required
def profile():
    """User profile page for managing default templates and resume."""
    return render_template("profile.html")

@app.route("/get_profile")
@login_required
def get_profile():
    """Get user profile data from Firestore."""
    user_email = session.get("user")
    try:
        db = firestore.client()
        doc = db.collection('user_profiles').document(user_email).get()
        if doc.exists:
            data = doc.to_dict()
            return jsonify(data)
        return jsonify({})
    except Exception as e:
        print(f"Error getting profile: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Firestore collection names
FIRESTORE_COLLECTIONS = {
    'user_profiles': 'user_profiles',      # Stores user profile data
    'user_preferences': 'user_preferences', # Stores user preferences
    'sent_emails': 'sent_emails',          # Stores email history
    'automation_runs': 'automation_runs',   # Stores automation run data
    'job_posts': 'job_posts'               # Stores unique job posts
}

def get_user_preferences(user_email):
    """Get user preferences from Firestore.
    
    Data structure in Firestore:
    - Collection: user_preferences
      - Document ID: user's email
        - Fields:
          - defaultSubject: string
          - defaultTemplate: string
          - notifications: boolean
          - customSettings: map
          - lastUpdated: timestamp
    """
    try:
        if firestore is not None:
            db = firestore.client()
            doc = db.collection(FIRESTORE_COLLECTIONS['user_preferences']).document(user_email).get()
            if doc.exists:
                return doc.to_dict()
    except Exception as e:
        print(f"Error getting user preferences: {str(e)}")
    return {}

def save_user_preferences(user_email, preferences):
    """Save user preferences to Firestore."""
    try:
        if firestore is not None:
            db = firestore.client()
            # Add timestamp to track last update
            preferences['lastUpdated'] = firestore.SERVER_TIMESTAMP
            db.collection(FIRESTORE_COLLECTIONS['user_preferences']).document(user_email).set(preferences, merge=True)
            return True
    except Exception as e:
        print(f"Error saving user preferences: {str(e)}")
    return False

def save_automation_run(run_id, user_email, settings=None):
    """Save automation run data to Firestore.
    
    Args:
        run_id: Unique identifier for the automation run
        user_email: Email of the user who initiated the run
        settings: Dictionary of settings used for this run
    """
    try:
        if firestore is not None:
            db = firestore.client()
            run_data = {
                'user_email': user_email,
                'start_time': firestore.SERVER_TIMESTAMP,
                'status': 'running',
                'settings_used': settings or {},
                'total_emails': 0,
                'successful': 0,
                'failed': 0
            }
            db.collection(FIRESTORE_COLLECTIONS['automation_runs']).document(run_id).set(run_data)
            return True
    except Exception as e:
        print(f"Error saving automation run: {str(e)}")
    return False

def update_automation_run(run_id, stats):
    """Update automation run statistics in Firestore."""
    try:
        if firestore is not None:
            db = firestore.client()
            stats['end_time'] = firestore.SERVER_TIMESTAMP
            stats['status'] = 'completed'
            db.collection(FIRESTORE_COLLECTIONS['automation_runs']).document(run_id).update(stats)
            return True
    except Exception as e:
        print(f"Error updating automation run: {str(e)}")
    return False

@app.route("/save_profile", methods=["POST"])
@login_required
def save_profile():
    """Save user profile data to Firestore."""
    user_email = session.get("user")
    
    # Get form data
    email_subject = request.form.get("emailSubject")
    email_content = request.form.get("emailContent")
    search_role = request.form.get("searchRole", "devops, cloud, site reliability")
    search_time_period = request.form.get("searchTimePeriod", "past-week")
    
    # Handle resume file - store in Firestore as base64
    resume_data = None
    resume_filename = None
    if "resumeFile" in request.files:
        resume = request.files["resumeFile"]
        if resume.filename:
            # Read file and encode as base64
            resume_bytes = resume.read()
            resume_data = base64.b64encode(resume_bytes).decode('utf-8')
            resume_filename = resume.filename
            print(f"📄 Resume uploaded: {resume_filename}, size: {len(resume_bytes)} bytes")
    
    try:
        db = firestore.client()
        profile_data = {
            "emailSubject": email_subject,
            "emailContent": email_content,
            "searchRole": search_role,
            "searchTimePeriod": search_time_period,
            "updatedAt": datetime.now()
        }
        
        # Only update resume if new one uploaded
        if resume_data:
            profile_data["resumeData"] = resume_data
            profile_data["resumeFilename"] = resume_filename
            print(f"✅ Storing resume in Firestore: {resume_filename}")
        
        db.collection('user_profiles').document(user_email).set(profile_data, merge=True)
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"❌ Error saving profile: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/")
@login_required
def home():
    """Home landing page after login with links to the main features."""
    user_email = session["user"]
    
    # Get user's email stats from Firestore
    sent_emails, stats = get_user_email_stats(user_email)
    
    if sent_emails is None:
        # Fallback to local storage if Firestore query failed
        print("⚠️ Falling back to local storage")
        sent_emails = load_sent_emails(user_email)
        stats = {
            "sent": sum(1 for r in sent_emails if r.get("status") == "sent"),
            "skipped": sum(1 for r in sent_emails if r.get("status") == "skipped"),
            "failed": sum(1 for r in sent_emails if r.get("status") == "failed"),
            "duplicates": 0,
            "total": len(sent_emails),
            "last_run": max((r.get('timestamp', '') for r in sent_emails), default=''),
            "unique_recipients": len(set(r.get('email') for r in sent_emails if r.get('email'))),
            "runs": len(set(r.get('run_id') for r in sent_emails if r.get('run_id')))
        }
    
    # Get user profile data
    try:
        db = firestore.client()
        profile_doc = db.collection('user_profiles').document(user_email).get()
        profile_data = profile_doc.to_dict() if profile_doc.exists else {}
    except Exception:
        profile_data = {}
    
    # Get recent activity
    recent_runs = []
    if sent_emails:
        # Group by run_id and get the most recent 5 runs
        runs = {}
        for email in sorted(sent_emails, key=lambda x: x.get('run_time', ''), reverse=True):
            run_id = email.get('run_id', 'unknown')
            if run_id not in runs:
                runs[run_id] = {
                    'run_id': run_id,
                    'run_time': email.get('run_time'),
                    'emails_sent': sum(1 for e in sent_emails if e.get('run_id') == run_id and e.get('status') == 'sent'),
                    'total_emails': sum(1 for e in sent_emails if e.get('run_id') == run_id)
                }
            if len(runs) >= 5:
                break
        recent_runs = list(runs.values())
    
    return render_template(
        "home.html",
        user=user_email,
        stats=stats,
        profile=profile_data,
        recent_runs=recent_runs
    )


@app.route("/send")
@login_required
def send_page():
    """Email sending UI (previously the root index)."""
    return render_template("index_live.html", user=session["user"])

# --- JOB POSTS PAGE ---
@app.route("/jobs")
@login_required
def job_posts():
    posts = load_job_posts()
    # Sort posts by date, newest first
    posts.sort(key=lambda x: x["posted_date"], reverse=True)
    return render_template("job_posts.html", job_posts=posts)


@app.route("/sent_emails")
@login_required
def sent_emails_page():
    """Render a page listing all sent emails grouped by automation runs for the current user."""
    user_email = session["user"]
    
    # Get records using the efficient query helper
    records, stats = get_user_email_stats(user_email)
    
    if records is None:
        records = load_sent_emails(user_email)
        print(f"📁 Loaded {len(records)} emails from local storage")
    
    # Group emails by run_id with enhanced stats
    runs = {}
    for record in records:
        run_id = record.get('run_id', 'unknown')
        run_time = record.get('run_time', record.get('sent_at', ''))
        if run_id not in runs:
            runs[run_id] = {
                'run_id': run_id,
                'run_time': run_time,
                'emails': [],
                'stats': {'sent': 0, 'failed': 0, 'skipped': 0},
                'subject': record.get('subject', 'No Subject'),  # Add subject for better context
                'user_email': user_email
            }
        runs[run_id]['emails'].append(record)
        # Update stats
        status = record.get('status', 'unknown')
        if status in runs[run_id]['stats']:
            runs[run_id]['stats'][status] += 1
    
    # Convert to list and sort by run_time
    runs_list = list(runs.values())
    runs_list.sort(key=lambda x: x['run_time'], reverse=True)
    
    # Add total stats
    total_stats = {
        'total_runs': len(runs_list),
        'total_emails': len(records),
        'total_sent': sum(run['stats']['sent'] for run in runs_list),
        'total_failed': sum(run['stats']['failed'] for run in runs_list),
        'total_skipped': sum(run['stats']['skipped'] for run in runs_list)
    }
    
    return render_template('sent_emails.html', runs=runs_list, total_stats=total_stats)


@app.route('/api/sent_emails')
@login_required
def sent_emails_api():
    """Return JSON array of sent email records for the current user."""
    user_email = session["user"]
    return jsonify(load_sent_emails(user_email))


@app.route('/api/sent_email_stats')
@login_required
def sent_email_stats_api():
    """Return lightweight stats (sent/skipped/failed/total) for the current user.

    This endpoint avoids returning the full history and is intended for
    quick dashboard updates (Home page) — it uses the same Firestore-safe
    query helper that sorts in-memory to avoid requiring composite indexes.
    """
    user_email = session.get('user')
    try:
        records, stats = get_user_email_stats(user_email)
        if records is None:
            # Fallback: compute stats from local storage
            emails = load_sent_emails(user_email)
            stats = {
                'sent': sum(1 for r in emails if r.get('status') == 'sent'),
                'skipped': sum(1 for r in emails if r.get('status') == 'skipped'),
                'failed': sum(1 for r in emails if r.get('status') == 'failed'),
                'total': len(emails)
            }
        else:
            # Ensure minimal shape in response
            stats = {k: stats.get(k, 0) for k in ('sent', 'skipped', 'failed', 'total')}
        return jsonify(stats)
    except Exception as e:
        print(f"❌ Error in /api/sent_email_stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/preferences', methods=['GET', 'POST'])
@login_required
def user_preferences():
    """Handle user preferences."""
    user_email = session.get("user")
    
    if request.method == 'POST':
        preferences = request.get_json()
        if save_user_preferences(user_email, preferences):
            return jsonify({"status": "success"})
        return jsonify({"error": "Failed to save preferences"}), 500
    
    # GET request
    preferences = get_user_preferences(user_email)
    return jsonify(preferences)

@app.route('/submit_2fa_code', methods=['POST'])
@login_required
def submit_2fa_code():
    """Endpoint to submit 2FA verification code."""
    global verification_code_submitted, verification_code_value, automation_driver
    
    code = request.json.get('code', '').strip()
    
    if not code:
        return jsonify({"status": "error", "message": "Code is required"}), 400
    
    if automation_driver is None:
        return jsonify({"status": "error", "message": "No active automation session"}), 400
    
    try:
        log(f"📱 Received 2FA code from user: {code}")
        verification_code_value = code
        verification_code_submitted = True
        
        return jsonify({
            "status": "success", 
            "message": "Code submitted successfully. Automation will continue..."
        })
    except Exception as e:
        log(f"❌ Error submitting 2FA code: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/progress')
@login_required
def progress_stream():
    """Server-Sent Events endpoint that streams log messages to the client."""
    print("🔌 Progress stream connection established")
    
    def event_stream():
        q = Queue()
        with clients_lock:
            clients.append(q)
            print(f"👥 Active clients: {len(clients)}")

        try:
            while True:
                try:
                    # Wait up to 15s for a message then send heartbeat
                    msg = q.get(timeout=15)
                    print(f"📢 Sending message: {msg}")
                    yield f"data: {msg}\n\n"
                except Empty:
                    # heartbeat to keep connection alive
                    print("💓 Sending heartbeat")
                    yield "data: \n\n"
        except GeneratorExit:
            # Client disconnected
            print("🔌 Client disconnected")
            with clients_lock:
                try:
                    clients.remove(q)
                    print(f"👥 Remaining clients: {len(clients)}")
                except ValueError:
                    print("❌ Client queue not found")

    return Response(event_stream(), mimetype='text/event-stream')


def linkedin_login(driver, email, password):
    """Log into LinkedIn using email and password."""
    try:
        log("🔐 Attempting LinkedIn login...")
        
        # Navigate to LinkedIn login page
        driver.get("https://www.linkedin.com/login")
        time.sleep(3)
        
        # Wait for login form to load
        wait = WebDriverWait(driver, 10)
        
        # Find email field
        email_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        email_field.clear()
        email_field.send_keys(email)
        log("📧 Email entered")
        
        # Find password field
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys(password)
        log("🔑 Password entered")
        
        # Click sign in button
        sign_in_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        sign_in_button.click()
        log("🚀 Sign in button clicked")
        
        # Wait for login to complete - check for feed or home page
        log("⏳ Waiting for page to load after login...")
        time.sleep(5)
        
        # Check if login was successful
        current_url = driver.current_url
        log(f"🔍 Current URL after login: {current_url}")
        log(f"🔍 Page title: {driver.title}")
        
        if "feed" in current_url or "home" in current_url or "mynetwork" in current_url:
            log("✅ LinkedIn login successful!")
            return True
        
        # Check for 2FA/verification elements on page (not just URL)
        has_2fa = False
        try:
            # Look for verification input fields
            verification_selectors = [
                "#input__email_verification_pin",
                "#input__phone_verification_pin",
                "input[name='pin']",
                "input[autocomplete='one-time-code']",
                "input[id*='verification']",
                "input[id*='pin']"
            ]
            
            for selector in verification_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 0:
                        log(f"🔍 Found 2FA input field: {selector}")
                        has_2fa = True
                        break
                except:
                    continue
            
            # Also check page text for 2FA keywords
            if not has_2fa:
                page_text = driver.page_source.lower()
                verification_keywords = ["verification code", "verify", "two-step", "security code", "enter the code"]
                for keyword in verification_keywords:
                    if keyword in page_text:
                        log(f"🔍 Found 2FA keyword in page: '{keyword}'")
                        has_2fa = True
                        break
        except Exception as check_error:
            log(f"⚠️ Error checking for 2FA: {str(check_error)}")
        
        if "checkpoint" in current_url or "challenge" in current_url or has_2fa:
            log("=" * 70)
            log("⚠️ LinkedIn requires additional verification (2FA/challenge)")
            log(f"� Current URL: {current_url}")
            log("=" * 70)
            
            # Save screenshot for debugging
            try:
                screenshot_path = "/tmp/linkedin_2fa_challenge.png"
                driver.save_screenshot(screenshot_path)
                log(f"📸 Screenshot saved: {screenshot_path}")
            except Exception as ss_error:
                log(f"⚠️ Could not save screenshot: {str(ss_error)}")
            
            # Save page HTML
            try:
                html_path = "/tmp/linkedin_2fa_challenge.html"
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                log(f"📄 Page HTML saved: {html_path}")
            except Exception as html_error:
                log(f"⚠️ Could not save HTML: {str(html_error)}")
            
            log("�🔍 Waiting for 2FA verification code...")
            
            # Wait for verification code input field
            try:
                # Try to find the verification code input field
                code_input = None
                input_selectors = [
                    "#input__email_verification_pin",
                    "#input__phone_verification_pin", 
                    "input[name='pin']",
                    "input[autocomplete='one-time-code']",
                    "input[id*='verification']",
                    "input[id*='pin']"
                ]
                
                for selector in input_selectors:
                    try:
                        code_input = driver.find_element(By.CSS_SELECTOR, selector)
                        if code_input and code_input.is_displayed():
                            log(f"✅ Found verification input field: {selector}")
                            break
                    except:
                        continue
                
                if code_input:
                    global verification_code_submitted, verification_code_value
                    
                    log("📱 2FA code input field detected")
                    log("=" * 70)
                    log("🔐 ENTER YOUR 2FA CODE VIA WEB INTERFACE:")
                    log("   1. Check your email/phone for LinkedIn verification code")
                    log("   2. A modal will appear on the web page")
                    log("   3. Enter your 6-digit code in the input field")
                    log("   4. Click 'Submit Code' button")
                    log("   5. Automation will enter the code and continue")
                    log("⏳ Waiting for code submission (max 10 minutes)...")
                    log("=" * 70)
                    # Also send to stdout for visibility
                    print("=" * 70, flush=True)
                    print("🔐 ENTER YOUR 2FA CODE", flush=True)
                    print("=" * 70, flush=True)
                    
                    # Reset verification state
                    verification_code_submitted = False
                    verification_code_value = None
                    
                    # Wait for user to submit code via web interface
                    timeout = 600  # 10 minutes (increased from 5)
                    elapsed = 0
                    while elapsed < timeout and not verification_code_submitted:
                        time.sleep(1)
                        elapsed += 1
                        if elapsed % 10 == 0:  # Log every 10 seconds
                            remaining = timeout - elapsed
                            log(f"⏳ Still waiting for 2FA code... ({elapsed}s / {timeout}s - {remaining}s remaining)")
                            # Keep the modal trigger visible
                            if elapsed % 30 == 0:  # Re-send trigger every 30 seconds
                                log("🔐 ENTER YOUR 2FA CODE")
                    
                    if verification_code_submitted and verification_code_value:
                        log(f"✅ Received code, entering it now...")
                        
                        # Enter the code
                        code_input.clear()
                        code_input.send_keys(verification_code_value)
                        log("✅ Code entered into LinkedIn form")
                        time.sleep(1)
                        
                        # Find and click submit button
                        from selenium.webdriver.common.keys import Keys
                        submit_button = None
                        button_selectors = [
                            "button[type='submit']",
                            "button[data-litms-control-urn*='verify']",
                            "button[aria-label*='Submit']",
                            ".primary-action-button",
                            "button.btn__primary--large"
                        ]
                        
                        for btn_selector in button_selectors:
                            try:
                                submit_button = driver.find_element(By.CSS_SELECTOR, btn_selector)
                                if submit_button and submit_button.is_displayed():
                                    submit_button.click()
                                    log(f"✅ Submit button clicked: {btn_selector}")
                                    break
                            except:
                                continue
                        
                        if not submit_button:
                            log("⚠️ Could not find submit button, using Enter key...")
                            code_input.send_keys(Keys.RETURN)
                        
                        # Wait for redirect
                        log("⏳ Waiting for LinkedIn to verify...")
                        time.sleep(3)
                        wait = WebDriverWait(driver, 30)
                        try:
                            wait.until(lambda d: "feed" in d.current_url or "home" in d.current_url or "mynetwork" in d.current_url)
                            log("=" * 70)
                            log("✅ Verification completed successfully!")
                            log(f"✅ Redirected to: {driver.current_url}")
                            log("=" * 70)
                            return True
                        except:
                            log("❌ Verification may have failed - check code")
                            return False
                    else:
                        log("=" * 70)
                        log("⏰ TIMEOUT: No 2FA code entered within 10 minutes")
                        log("❌ Please try running automation again and enter code faster")
                        log("=" * 70)
                        return False
                else:
                    log("⚠️ Could not find verification input field")
                    log("=" * 70)
                    log("⏳ WAITING FOR MANUAL VERIFICATION:")
                    log("   1. Complete the verification challenge on LinkedIn")
                    log("   2. You should be redirected to feed/home")
                    log("   3. Automation will detect completion and resume")
                    log("⏳ Maximum wait time: 5 minutes")
                    log("=" * 70)
                    
                    # Wait for URL to change to feed/home (verification completed)
                    wait = WebDriverWait(driver, 300)  # 5 minutes
                    wait.until(lambda d: "feed" in d.current_url or "home" in d.current_url or "mynetwork" in d.current_url)
                    
                    log("=" * 70)
                    log("✅ Verification completed!")
                    log(f"✅ Redirected to: {driver.current_url}")
                    log("=" * 70)
                    return True
                    
            except Exception as verification_error:
                log("=" * 70)
                log(f"⏰ Verification timeout or error: {str(verification_error)}")
                log(f"⏰ Current URL after timeout: {driver.current_url}")
                log("⚠️ Please check LinkedIn and try again")
                log("=" * 70)
                return False
        else:
            log("❌ LinkedIn login failed - checking for error messages")
            try:
                error_element = driver.find_element(By.CLASS_NAME, "alert-error")
                log(f"❌ Login error: {error_element.text}")
            except:
                log("❌ Login failed - unknown error")
            return False
            
    except Exception as e:
        log(f"❌ Error during LinkedIn login: {str(e)}")
        return False


# --- AUTOMATION FUNCTION ---
def run_automation(subject, email_content, attachment_path, cc_email, run_id=None, user_email=None, search_role=None, search_time=None):
    # Wrap EVERYTHING in try-catch to catch silent failures
    try:
        print("=" * 80, flush=True)
        print("🚀 DEBUG: run_automation FUNCTION CALLED", flush=True)
        print(f"🚀 DEBUG: Thread ID: {threading.current_thread().ident}", flush=True)
        print(f"🚀 DEBUG: Thread Name: {threading.current_thread().name}", flush=True)
        print(f"🚀 DEBUG: Parameters received:", flush=True)
        print(f"    - subject: {subject}", flush=True)
        print(f"    - email_content length: {len(email_content) if email_content else 0}", flush=True)
        print(f"    - attachment_path: {attachment_path}", flush=True)
        print(f"    - cc_email: {cc_email}", flush=True)
        print(f"    - run_id: {run_id}", flush=True)
        print(f"    - user_email: {user_email}", flush=True)
        print(f"    - search_role: {search_role}", flush=True)
        print(f"    - search_time: {search_time}", flush=True)
        print("=" * 80, flush=True)
    except Exception as top_error:
        print(f"❌ CRITICAL: Error in function entry: {str(top_error)}", flush=True)
        import traceback
        traceback.print_exc()
        return
    
    log("🚀 Starting automation...")
    log(f"📝 Run ID: {run_id}")
    if user_email:
        log(f"👤 User: {user_email}")
    # Initialize resources referenced in finally/cleanup
    driver = None
    all_emails = set()

    try:
        print("✅ DEBUG: Entered main try block")
        log("⚙️ Initializing automation process...")
        print("✅ DEBUG: About to set email credentials")
        # Log initial state
        log("⚙️ Initializing automation process...")

        # Fixed email credentials
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "manudrive06@gmail.com"
        sender_password = "ozds nrqo gduy mnwd"

        # Chrome setup - always use D:\Profile directory
        options = webdriver.ChromeOptions()
        
        # Only use headless mode if HEADLESS environment variable is not set to "false"
        if os.environ.get('HEADLESS', 'true').lower() != 'false':
            options.add_argument("--headless=new")
            log("🔇 Running Chrome in headless mode")
        else:
            log("👁️ Running Chrome in visible mode (headless disabled)")
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument("--disable-features=VizDisplayCompositor")

        # Use appropriate profile directory based on environment
        if os.environ.get('CHROME_BIN'):  # Docker/Cloud environment
            profile_dir = "/tmp/chrome-profile"
            log("🌐 Using Docker Chrome profile directory")
        else:  # Local Windows environment
            profile_dir = r"D:\Profile"
            log("🏠 Using Windows Chrome profile directory")
        
        os.makedirs(profile_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
        log(f"🗂 Using Chrome profile directory: {profile_dir}")

        options.page_load_strategy = 'normal'
        log("✅ Chrome options configured")
    except Exception as e:
        error_msg = f"❌ Error during initialization: {str(e)}"
        log(error_msg)
        print(error_msg)
        raise
    
    from selenium.webdriver.chrome.service import Service
    
    try:
        log("=" * 60)
        log("🔍 DEBUG: Starting Chrome initialization")
        log(f"🔍 DEBUG: CHROME_BIN env = {os.environ.get('CHROME_BIN')}")
        log(f"🔍 DEBUG: CHROMEDRIVER_PATH env = {os.environ.get('CHROMEDRIVER_PATH')}")
        log("=" * 60)
        
        # Use explicit ChromeDriver path in Docker/Cloud, auto-install locally
        if os.environ.get('CHROMEDRIVER_PATH'):
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
            log(f"🔧 Using ChromeDriver from: {chromedriver_path}")
            
            # Verify ChromeDriver exists
            if os.path.exists(chromedriver_path):
                log(f"✅ ChromeDriver file exists at {chromedriver_path}")
            else:
                log(f"❌ ChromeDriver file NOT FOUND at {chromedriver_path}")
                raise FileNotFoundError(f"ChromeDriver not found at {chromedriver_path}")
            
            service = Service(chromedriver_path)
            log("✅ Service object created")
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            log("🔄 Installing ChromeDriver via webdriver_manager...")
            service = Service(ChromeDriverManager().install())
            log("✅ ChromeDriver installed via webdriver_manager")
        
        log("🚀 DEBUG: About to launch Chrome browser...")
        log(f"🚀 DEBUG: Chrome binary location from options: {options.binary_location if hasattr(options, 'binary_location') and options.binary_location else 'Not set'}")
        
        try:
            log("🔄 Launching Chrome WebDriver...")
            driver = webdriver.Chrome(service=service, options=options)
            log("✅ Chrome WebDriver created successfully!")
        except Exception as chrome_error:
            log("=" * 70)
            log("❌ CRITICAL: Failed to launch Chrome!")
            log(f"❌ Error type: {type(chrome_error).__name__}")
            log(f"❌ Error message: {str(chrome_error)}")
            log("=" * 70)
            import traceback
            log(f"❌ Full traceback:")
            log(traceback.format_exc())
            log("=" * 70)
            raise
        
        # Set global driver for 2FA handling
        global automation_driver
        automation_driver = driver
        
        log("✅ Chrome launched successfully!")
        log(f"✅ Chrome version: {driver.capabilities.get('browserVersion', 'unknown')}")
        log(f"✅ ChromeDriver version: {driver.capabilities.get('chrome', {}).get('chromedriverVersion', 'unknown')}")
        print("✅ Chrome instance ready", flush=True)
        
        log("🔄 DEBUG: About to start LinkedIn login flow")

        # Login logic: check existing profile first, fallback to email/password
        login_successful = False
        
        log("🔄 DEBUG: login_successful variable initialized")

        # First, try to use existing profile
        log("=" * 60)
        log("🔍 DEBUG: Starting LinkedIn login check...")
        log("🔍 DEBUG: Navigating to LinkedIn feed...")
        
        try:
            driver.get("https://www.linkedin.com/feed/")
            log(f"✅ DEBUG: Page loaded, current URL: {driver.current_url}")
            log(f"✅ DEBUG: Page title: {driver.title}")
        except Exception as nav_error:
            log(f"❌ DEBUG: Navigation error: {str(nav_error)}")
            raise
        
        log("⏳ DEBUG: Waiting 5 seconds for page to settle...")
        time.sleep(5)  # Increased wait time
        log(f"✅ DEBUG: After wait, URL: {driver.current_url}")

        # Better login check: look for elements that only exist when logged in
        try:
            log("🔍 DEBUG: Checking login indicators...")
            # Check for multiple indicators of being logged in
            login_indicators = [
                ".global-nav__me",  # User profile dropdown
                ".feed-identity-module",  # Feed identity section
                "[data-control-name='nav.settings_and_privacy']",  # Settings menu
                ".nav-item__profile-member-photo"  # Profile photo
            ]

            logged_in = False
            for indicator in login_indicators:
                try:
                    log(f"🔍 DEBUG: Checking indicator: {indicator}")
                    elements = driver.find_elements(By.CSS_SELECTOR, indicator)
                    log(f"🔍 DEBUG: Found {len(elements)} elements for {indicator}")
                    if elements:
                        logged_in = True
                        log(f"✅ DEBUG: Login confirmed via indicator: {indicator}")
                        break
                except Exception as ind_error:
                    log(f"⚠️ DEBUG: Error checking {indicator}: {str(ind_error)}")
                    continue

            # Also check URL - if redirected to login page, definitely not logged in
            current_url = driver.current_url
            log(f"🔍 DEBUG: Final URL check: {current_url}")
            
            if "login" in current_url or "authwall" in current_url:
                logged_in = False
                log("⚠️ Redirected to login page - not logged in")
            elif logged_in:
                log("✅ Existing profile login successful!")
                login_successful = True
            else:
                log("⚠️ Could not find login indicators, profile may not be logged in")
                log(f"🔍 DEBUG: Page source length: {len(driver.page_source)}")
                # Save page source for debugging
                try:
                    with open('/tmp/linkedin_debug.html', 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    log("📄 DEBUG: Page source saved to /tmp/linkedin_debug.html")
                except:
                    pass

        except Exception as e:
            log(f"❌ DEBUG: Error checking login status: {str(e)}")
            log(f"❌ DEBUG: Error type: {type(e).__name__}")
            import traceback
            log(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
            
            # Check URL as fallback
            try:
                current_url = driver.current_url
                log(f"🔍 DEBUG: Fallback URL check: {current_url}")
                if "feed" in current_url or "home" in current_url or "mynetwork" in current_url:
                    log("✅ Existing profile login successful! (URL check)")
                    login_successful = True
                else:
                    log("⚠️ Profile not logged in (URL check failed)")
            except Exception as url_error:
                log(f"❌ DEBUG: Error getting URL in fallback: {str(url_error)}")

        if not login_successful:
            log("=" * 60)
            log("🔍 DEBUG: Profile not logged in, checking for email/password login...")
            log(f"🔍 DEBUG: LINKEDIN_EMAIL env = {'SET' if LINKEDIN_EMAIL else 'NOT SET'}")
            log(f"🔍 DEBUG: LINKEDIN_PASSWORD env = {'SET' if LINKEDIN_PASSWORD else 'NOT SET'}")
            log("=" * 60)
            log("🔄 Profile not logged in, attempting email/password login")

        if not login_successful and LINKEDIN_EMAIL and LINKEDIN_PASSWORD:
            # Use email/password login - this will save session in the same profile directory
            log("🔐 Attempting email/password login...")
            login_result = linkedin_login(driver, LINKEDIN_EMAIL, LINKEDIN_PASSWORD)
            if login_result:
                login_successful = True
                log("✅ Email/password login successful - session saved to profile")
            else:
                log("❌ Email/password login failed")
                error_msg = "LinkedIn login failed. Please check your credentials or complete 2FA verification."
                print(f"❌ ERROR: {error_msg}", flush=True)
                driver.quit()
                raise Exception(error_msg)

        if not login_successful:
            error_msg = "No login method succeeded - cannot proceed with automation"
            log(f"❌ {error_msg}")
            print(f"❌ ERROR: {error_msg}", flush=True)
            driver.quit()
            raise Exception(error_msg)
        else:
            log("✅ Proceeding with job search...")
        
        # Continue with job search...
    except Exception as e:
        error_msg = f"❌ Failed to launch Chrome: {str(e)}"
        log(error_msg)
        print(error_msg)
        raise

    try:
        # Get search parameters from function args or fallback to profile preferences
        db = firestore.client()
        profile_doc = db.collection('user_profiles').document(user_email).get()
        profile_data = profile_doc.to_dict() if profile_doc.exists else {}

        # Use passed-in search parameters if provided, otherwise fall back to profile preferences
        if not search_role:
            search_role = profile_data.get('searchRole', 'devops, cloud, site reliability')
        if not search_time:
            search_time = profile_data.get('searchTimePeriod', 'past-week')
        
        # Convert roles to LinkedIn search format
        roles = [role.strip() for role in search_role.split(',')]
        search_keywords = ' OR '.join(f'{role.strip()} hiring' for role in roles)
        
        # Build LinkedIn search URL
        base_url = "https://www.linkedin.com/search/results/content/?"
        params = {
            'datePosted': f'"{search_time}"',
            'keywords': search_keywords
        }
        
        # URL encode parameters
        from urllib.parse import urlencode
        search_url = base_url + urlencode(params)
        log(f"🔍 Using search URL: {search_url}")
        
        search_urls = [search_url]
        all_emails = set()

        for url in search_urls:
            log(f"🌐 Opening {url}")
            driver.get(url)
            time.sleep(5)
            # Scroll with dynamic wait
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_attempts = 18
            
            while scroll_attempts < max_attempts:
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)  # Wait for content to load
                
                # Calculate new scroll height and compare with last scroll height
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    # If heights are the same, content might be fully loaded
                    break

                last_height = new_height
                scroll_attempts += 1
                log(f"📜 Scrolling... ({scroll_attempts}/{max_attempts})")
            
            # Add wait for job posts
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            log("⏳ Waiting for posts to load...")
            wait = WebDriverWait(driver, 20)
            
            # Try multiple possible selectors for job posts
            selectors = [
                ".feed-shared-update-v2",
                "article.ember-view",
                ".update-components-actor",
                ".social-details-social-activity"
            ]
            
            job_posts = []
            for selector in selectors:
                try:
                    # Wait for elements to be present
                    elements = wait.until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    if elements:
                        log(f"✅ Found posts using selector: {selector}")
                        job_posts = elements
                        break
                except Exception as e:
                    log(f"⚠️ Selector {selector} failed: {str(e)}")
                    continue
            
            if not job_posts:
                log("❌ No job posts found with any selector")
                return
                
            for post in job_posts:
                try:
                    # Try multiple selectors for title and description
                    title_selectors = [
                        ".feed-shared-text",
                        ".feed-shared-text-view",
                        ".update-components-text",
                        ".share-update-card__update-text",
                        ".feed-shared-update-v2__description",
                        "span.break-words"
                    ]
                    
                    title_elem = None
                    for selector in title_selectors:
                        try:
                            title_elem = post.find_element(By.CSS_SELECTOR, selector)
                            if title_elem:
                                break
                        except:
                            continue
                    
                    title = title_elem.text if title_elem else "Job Title Not Found"
                    
                    # Try multiple selectors for company name
                    company_selectors = [
                        ".feed-shared-actor__name",
                        ".update-components-actor__name",
                        ".share-update-card__actor-name",
                        ".feed-shared-actor__sub-description"
                    ]
                    
                    company_elem = None
                    for selector in company_selectors:
                        try:
                            company_elem = post.find_element(By.CSS_SELECTOR, selector)
                            if company_elem:
                                break
                        except:
                            continue
                    
                    company = company_elem.text if company_elem else "Company Not Found"
                    
                    description = title_elem.text[:200] + "..." if len(title_elem.text) > 200 else title_elem.text
                    
                    # Find mailto links in the post
                    mailtos = post.find_elements(By.XPATH, ".//a[contains(@href, 'mailto:')]")
                    for m in mailtos:
                        email = m.get_attribute("href").replace("mailto:", "")
                        all_emails.add(email)
                        
                        # Save job post with email
                        job_post = {
                            "title": title,
                            "company": company,
                            "description": description,
                            "email": email,
                            "location": "Remote/On-site",  # You can enhance this with actual location parsing
                            "job_type": "Full-time",      # You can enhance this with actual job type parsing
                            "posted_date": datetime.now().strftime("%Y-%m-%d"),
                            "url": url
                        }
                        save_job_post(job_post)
                        
                except Exception as e:
                    log(f"Error extracting job post: {e}")
                    continue

        log(f"📧 Found {len(all_emails)} email(s).")

        # Function to check if email was already sent (directly in Firestore if available)
        def is_duplicate_email(email, subject):
            try:
                if firestore is not None:
                    db = firestore.client()
                    # Query Firestore directly for this email+subject combination
                    query = (db.collection(FIRESTORE_COLLECTIONS['sent_emails'])
                            .where('email', '==', email)
                            .where('subject', '==', subject)
                            .where('status', 'in', ['sent', 'skipped'])
                            .limit(1))
                    
                    docs = list(query.stream())
                    if docs:
                        # Found a match in Firestore
                        return True, docs[0].to_dict().get('sent_at', '')
                
                # If no match in Firestore or Firestore not available, check local storage
                sent_records = load_sent_emails()
                for record in sent_records:
                    if (record.get('email') == email and 
                        record.get('subject') == subject and
                        record.get('status') in ['sent', 'skipped']):
                        return True, record.get('sent_at', '')
                
                return False, None
                
            except Exception as e:
                print(f"❌ Error checking for duplicate email: {str(e)}")
                # If we can't check reliably, assume it might be a duplicate
                return True, None

        # Send emails with enhanced duplicate checking
        for receiver_email in all_emails:
            try:
                # Check if this exact email+subject was already sent
                is_duplicate, last_sent = is_duplicate_email(receiver_email, subject)
                
                if is_duplicate:
                    when = f" (last sent: {last_sent})" if last_sent else ""
                    log(f"⚠️ Already sent to {receiver_email} with subject '{subject}'{when} — skipping.")
                    
                    # Record skip with detailed reason
                    save_sent_email({
                        "email": receiver_email,
                        "subject": subject if subject else "",
                        "cc": cc_email,
                        "sent_at": datetime.now().isoformat(),
                        "status": "skipped",
                        "reason": "duplicate",
                        "last_sent": last_sent,
                        "source_url": ",".join(search_urls)
                    })
                    continue

                # Create message
                msg = MIMEMultipart()
                msg["From"] = sender_email
                msg["To"] = receiver_email
                msg["Cc"] = cc_email  # Add CC
                msg["Subject"] = subject if subject else "Application"
                
                # Handle email content
                if email_content is None:
                    email_content = "No content provided"
                # Ensure content is string and properly encoded
                email_content = str(email_content).encode('utf-8').decode('utf-8')
                msg.attach(MIMEText(email_content, "plain", "utf-8"))

                # Handle attachment
                if attachment_path and os.path.exists(attachment_path):
                    with open(attachment_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={os.path.basename(attachment_path)}"
                        )
                        msg.attach(part)

                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, receiver_email, msg.as_string())
                server.quit()

                log(f"✅ Sent to {receiver_email}")
                # Persist sent email record
                save_sent_email({
                    "email": receiver_email,
                    "subject": subject if subject else "",
                    "cc": cc_email,
                    "sent_at": datetime.now().isoformat(),
                    "status": "sent",
                    "source_url": ",".join(search_urls)
                }, run_id, user_email)
            except Exception as e:
                log(f"❌ Failed to send email to {receiver_email}: {e}")
                # Persist failure
                try:
                    save_sent_email({
                        "email": receiver_email,
                        "subject": subject if subject else "",
                        "cc": cc_email,
                        "sent_at": datetime.now().isoformat(),
                        "status": "failed",
                        "error": str(e),
                        "source_url": ",".join(search_urls)
                    }, run_id, user_email)
                except Exception:
                    pass

    except Exception as automation_error:
        # Catch ANY unhandled exception in the automation
        log("=" * 80)
        log("❌ CRITICAL ERROR IN AUTOMATION!")
        log(f"❌ Error type: {type(automation_error).__name__}")
        log(f"❌ Error message: {str(automation_error)}")
        log("=" * 80)
        import traceback
        error_traceback = traceback.format_exc()
        log("❌ Full traceback:")
        log(error_traceback)
        log("=" * 80)
        
        # Also print to stdout for visibility in logs
        print("=" * 80, flush=True)
        print("❌ CRITICAL ERROR IN AUTOMATION!", flush=True)
        print(f"❌ Error: {str(automation_error)}", flush=True)
        print(error_traceback, flush=True)
        print("=" * 80, flush=True)
        
    finally:
        try:
            # Force close any remaining Chrome instances
            if driver:
                driver.quit()
            cleanup_chrome_processes()
            # Note: We don't delete the profile directory since it's persistent (D:\Profile)
            log("🧹 Browser and Chrome instances closed.")

            # Send completion status back to the frontend
            log("✅ Automation completed successfully!")
            log(f"📊 Summary:")
            log(f"   - Emails found: {len(all_emails)}")
            log(f"   - Emails processed: {sum(1 for _ in all_emails)}")
            
            # Return status if this was called from a route
            return {
                "status": "completed",
                "emails_found": len(all_emails),
                "message": "Automation completed successfully!"
            }
            
        except Exception as e:
            log(f"❌ Error during cleanup: {str(e)}")
            # Still try to kill Chrome processes even if driver.quit() fails
            cleanup_chrome_processes()


# --- START AUTOMATION ---
@app.route("/run_automation", methods=["POST"])
@login_required
def send_email():
    print("📥 Received automation request")
    
    # Get the logged-in user's email for CC
    user_email = session.get("user")
    print(f"👤 User email: {user_email}")
    
    # Get form data
    subject = request.form.get("subject", "Application")
    email_content = request.form.get("content", "").strip()
    search_role = request.form.get("searchRole", "").strip()
    search_time_period = request.form.get("searchTimePeriod", "past-week")
    use_saved_resume = request.form.get("useSavedResume") == "true"
    
    # Save search preferences to user profile
    try:
        if firestore is not None:
            db = firestore.client()
            db.collection('user_profiles').document(user_email).update({
                'searchRole': search_role,
                'searchTimePeriod': search_time_period,
                'lastSearchAt': datetime.now()
            })
    except Exception as e:
        print(f"⚠️ Could not save search preferences: {e}")
    print(f"📧 Subject: {subject}")
    print(f"📝 Content length: {len(email_content)} characters")
    print(f"📎 Using saved resume: {use_saved_resume}")
    
    resume_path = None
    
    if use_saved_resume:
        # Get saved resume from Firestore and create temporary file
        try:
            db = firestore.client()
            doc = db.collection('user_profiles').document(user_email).get()
            if doc.exists:
                profile_data = doc.to_dict()
                
                # Check if resume data exists in Firestore
                if profile_data.get('resumeData') and profile_data.get('resumeFilename'):
                    resume_filename = profile_data['resumeFilename']
                    resume_data_b64 = profile_data['resumeData']
                    
                    print(f"📄 Retrieving saved resume from Firestore: {resume_filename}")
                    
                    try:
                        # Decode base64 resume data
                        resume_bytes = base64.b64decode(resume_data_b64)
                        
                        # Create temporary file for the resume
                        temp_dir = tempfile.gettempdir()
                        resume_path = os.path.join(temp_dir, f"{user_email}_{resume_filename}")
                        
                        with open(resume_path, 'wb') as f:
                            f.write(resume_bytes)
                        
                        print(f"✅ Resume restored to temporary file: {resume_path}")
                        print(f"✅ Resume size: {len(resume_bytes)} bytes")
                        
                    except Exception as decode_error:
                        print(f"❌ Error decoding resume: {str(decode_error)}")
                        flash("Error loading saved resume. Please upload a new resume.", "error")
                        return redirect(url_for("send_page"))
                else:
                    flash("No resume found in your profile. Please upload a resume.", "error")
                    return redirect(url_for("send_page"))
            else:
                flash("Profile not found. Please upload a resume.", "error")
                return redirect(url_for("send_page"))
        except Exception as e:
            print(f"❌ Error accessing profile: {str(e)}")
            import traceback
            traceback.print_exc()
            flash("Error accessing profile. Please upload a resume.", "error")
            return redirect(url_for("send_page"))
    else:
        # Handle new file upload - save to temporary location
        if "resume" not in request.files:
            print("❌ No resume file in request")
            flash("Please upload a resume or use your saved resume.", "error")
            return redirect(url_for("send_page"))
            
        resume = request.files["resume"]
        if resume.filename == "":
            print("❌ Empty resume filename")
            flash("No resume file selected. Please choose a file or use your saved resume.", "error")
            return redirect(url_for("send_page"))

        # Save the uploaded resume to temporary location (works in Docker)
        temp_dir = tempfile.gettempdir()
        resume_path = os.path.join(temp_dir, f"{user_email}_{resume.filename}")
        resume.save(resume_path)
        print(f"📄 Resume saved to temporary file: {resume_path}")

    # Clean up any existing Chrome instances before starting
    print("🧹 DEBUG: Cleaning up Chrome processes...")
    cleanup_chrome_processes()
    print("✅ DEBUG: Chrome cleanup complete")

    # Generate a unique run ID
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"🆔 DEBUG: Generated run_id: {run_id}")

    # Initialize automation run in Firestore (if available)
    if db_ops:
        print("💾 DEBUG: Saving automation run to Firestore...")
        db_ops.save_automation_run(run_id, user_email, {
            'subject': subject,
            'usesSavedResume': use_saved_resume,
            'resumePath': resume_path
        })
        print("✅ DEBUG: Automation run saved to Firestore")
    else:
        print(f"⚠️ Firestore not available - automation run {run_id} not saved")

    # Start automation in background thread
    print("=" * 60)
    print("🧵 DEBUG: Starting automation thread...")
    print(f"🧵 DEBUG: Thread args: subject={subject}, content_len={len(email_content)}, resume={resume_path}")
    print(f"🧵 DEBUG: Thread args: run_id={run_id}, user={user_email}, role={search_role}, time={search_time_period}")
    print("=" * 60)
    
    thread = threading.Thread(
        target=run_automation,
        args=(subject, email_content, resume_path, user_email, run_id, user_email, search_role, search_time_period),
        daemon=True
    )
    thread.start()
    print(f"✅ DEBUG: Thread started, thread is alive: {thread.is_alive()}")
    print(f"✅ DEBUG: Thread name: {thread.name}")

    flash("🚀 Automation started in background. Check console logs for updates.", "success")
    return redirect(url_for("send_page"))


if __name__ == "__main__":
    # Get port from environment variable (Render provides this)
    port = int(os.environ.get("PORT", 5000))
    # Use 0.0.0.0 to accept connections from all interfaces
    app.run(host="0.0.0.0", port=port, debug=False)
