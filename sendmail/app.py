from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Response
from functools import wraps
import firebase_admin
from firebase_admin import credentials, auth
# Firestore is optional; we'll import if available at runtime
try:
    from firebase_admin import firestore
    from firebase_admin.firestore import FieldFilter  # Add FieldFilter import
except Exception:
    firestore = None
    FieldFilter = None
import threading
from queue import Queue, Empty
import os
import smtplib
import time
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


app = Flask(__name__)

# Server-Sent Events clients (each client gets a Queue)
clients = []
clients_lock = threading.Lock()

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

def load_job_posts():
    try:
        with open(JOB_POSTS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_job_post(post):
    posts = load_job_posts()
    posts.append(post)
    with open(JOB_POSTS_FILE, 'w') as f:
        json.dump(posts, f)
    # Notify connected clients that a new job post was saved
    try:
        send_event(f"NEW_JOB: {post.get('title')} | {post.get('company')} | {post.get('email')}")
    except Exception:
        pass


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
# Initialize Firebase with credentials from the local directory
cred_path = os.path.join(os.path.dirname(__file__), "linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json")
print(f"🔑 Loading Firebase credentials from: {cred_path}")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)
print("✅ Firebase initialized successfully")

# Initialize Firestore operations
from firestore_ops import FirestoreOps
db_ops = FirestoreOps()


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
    'automation_runs': 'automation_runs'    # Stores automation run data
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
    
    # Handle resume file
    resume_filename = None
    if "resumeFile" in request.files:
        resume = request.files["resumeFile"]
        if resume.filename:
            # Save resume to user-specific folder
            user_uploads = os.path.join("uploads", user_email)
            os.makedirs(user_uploads, exist_ok=True)
            resume_filename = os.path.join(user_uploads, resume.filename)
            resume.save(resume_filename)
    
    try:
        db = firestore.client()
        profile_data = {
            "emailSubject": email_subject,
            "emailContent": email_content,
            "resumeFilename": resume_filename,
            "updatedAt": datetime.now()
        }
        
        db.collection('user_profiles').document(user_email).set(profile_data, merge=True)
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error saving profile: {str(e)}")
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


# --- AUTOMATION FUNCTION ---
def run_automation(subject, email_content, attachment_path, cc_email, run_id=None, user_email=None):
    log("🚀 Starting automation...")
    log(f"📝 Run ID: {run_id}")
    if user_email:
        log(f"👤 User: {user_email}")
    
    try:
        # Log initial state
        log("⚙️ Initializing automation process...")

        # Fixed email credentials
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "manudrive06@gmail.com"
        sender_password = "ozds nrqo gduy mnwd"

        # Chrome setup
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--user-data-dir=D:\\Profile")
        options.page_load_strategy = 'normal'
        log("✅ Chrome options configured")
    except Exception as e:
        error_msg = f"❌ Error during initialization: {str(e)}"
        log(error_msg)
        print(error_msg)
        raise
    
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    
    try:
        print("🔄 Installing ChromeDriver...")
        service = Service(ChromeDriverManager().install())
        print("🚀 Launching Chrome...")
        driver = webdriver.Chrome(service=service, options=options)
        log("✅ Chrome launched successfully.")
        print("✅ Chrome instance ready")
    except Exception as e:
        error_msg = f"❌ Failed to launch Chrome: {str(e)}"
        log(error_msg)
        print(error_msg)
        raise

    try:
        search_urls = [
            "https://www.linkedin.com/search/results/content/?datePosted=%22past-week%22&keywords=devops%20hiring%20OR%20cloud%20hiring%20OR%20site-reliability%20hiring",
           
        ]

        all_emails = set()

        for url in search_urls:
            log(f"🌐 Opening {url}")
            driver.get(url)
            time.sleep(5)
            # Scroll with dynamic wait
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_attempts = 16
            
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

        # Load already-sent emails to avoid duplicates
        sent_records = load_sent_emails()
        sent_emails_set = set((r.get('email'), r.get('subject')) for r in sent_records)

        # Send emails
        for receiver_email in all_emails:
            try:
                # Skip if this email+subject combo was already sent
                key = (receiver_email, subject if subject else "")
                if key in sent_emails_set:
                    log(f"⚠️ Already sent to {receiver_email} with same subject — skipping.")
                    # Record skipped event (optional)
                    save_sent_email({
                        "email": receiver_email,
                        "subject": subject if subject else "",
                        "cc": cc_email,
                        "sent_at": datetime.now().isoformat(),
                        "status": "skipped",
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

    finally:
        try:
            # Force close any remaining Chrome instances
            driver.quit()
            os.system('taskkill /f /im chrome.exe')
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
            os.system('taskkill /f /im chrome.exe')


# --- START AUTOMATION ---
@app.route("/run_automation", methods=["POST"])
@login_required
def send_email():
    print("📥 Received automation request")
    
    # Get the logged-in user's email for CC
    user_email = session.get("user")
    print(f"👤 User email: {user_email}")
    
    subject = request.form.get("subject", "Application")
    email_content = request.form.get("content", "").strip()
    use_saved_resume = request.form.get("useSavedResume") == "true"
    print(f"📧 Subject: {subject}")
    print(f"📝 Content length: {len(email_content)} characters")
    print(f"📎 Using saved resume: {use_saved_resume}")
    
    resume_path = None
    
    if use_saved_resume:
        # Get saved resume path from user profile
        try:
            db = firestore.client()
            doc = db.collection('user_profiles').document(user_email).get()
            if doc.exists:
                profile_data = doc.to_dict()
                if profile_data.get('resumeFilename'):
                    resume_path = profile_data['resumeFilename']
                    print(f"📄 Using saved resume: {resume_path}")
                    if not os.path.exists(resume_path):
                        flash("Saved resume file not found. Please upload a new resume.", "error")
                        return redirect(url_for("send_page"))
                else:
                    flash("No resume found in your profile. Please upload a resume.", "error")
                    return redirect(url_for("send_page"))
            else:
                flash("Profile not found. Please upload a resume.", "error")
                return redirect(url_for("send_page"))
        except Exception as e:
            print(f"❌ Error accessing profile: {str(e)}")
            flash("Error accessing profile. Please upload a resume.", "error")
            return redirect(url_for("send_page"))
    else:
        # Handle new file upload
        if "resume" not in request.files:
            print("❌ No resume file in request")
            flash("Please upload a resume or use your saved resume.", "error")
            return redirect(url_for("send_page"))
            
        resume = request.files["resume"]
        if resume.filename == "":
            print("❌ Empty resume filename")
            flash("No resume file selected. Please choose a file or use your saved resume.", "error")
            return redirect(url_for("send_page"))

        # Save the uploaded resume
        upload_folder = "uploads"
        os.makedirs(upload_folder, exist_ok=True)
        resume_path = os.path.join(upload_folder, resume.filename)
        resume.save(resume_path)

    # Clean up any existing Chrome instances before starting
    os.system('taskkill /f /im chrome.exe')

    # Generate a unique run ID
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Initialize automation run in Firestore
    db_ops.save_automation_run(run_id, user_email, {
        'subject': subject,
        'usesSavedResume': use_saved_resume,
        'resumePath': resume_path
    })

    # Start automation in background thread
    threading.Thread(
        target=run_automation,
        args=(subject, email_content, resume_path, user_email, run_id, user_email),
        daemon=True
    ).start()

    flash("🚀 Automation started in background. Check console logs for updates.", "success")
    return redirect(url_for("send_page"))


if __name__ == "__main__":
    app.run(debug=True)
