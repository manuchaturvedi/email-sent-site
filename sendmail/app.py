from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Response
from functools import wraps
import firebase_admin
from firebase_admin import credentials, auth
# Firestore is optional; we'll import if available at runtime
try:
    from firebase_admin import firestore
except Exception:
    firestore = None
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


def load_sent_emails():
    try:
        with open(SENT_EMAILS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_sent_email(record, run_id=None):
    """Save a single sent-email record locally and optionally to Firestore.

    record is a dict containing at least: email, subject, cc, sent_at, status, source_url
    run_id is the unique identifier for this automation run
    """
    # Load existing emails
    existing = load_sent_emails()
    
    # Add run information
    if run_id:
        record['run_id'] = run_id
        record['run_time'] = datetime.now().isoformat()
    
    # Avoid duplicates within the same run
    for r in existing:
        if (r.get('email') == record.get('email') and 
            r.get('subject') == record.get('subject') and
            r.get('run_id') == record.get('run_id')):
            return False

    existing.append(record)
    with open(SENT_EMAILS_FILE, 'w') as f:
        json.dump(existing, f, default=str, indent=2)

    # Try to save to Firestore if available
    try:
        if firestore is not None:
            db = firestore.client()
            # Use auto-generated doc id to allow multiple entries per email if needed
            db.collection('sent_emails').add(record)
    except Exception:
        # Firestore write failed, but local write remains
        pass

    # Notify connected clients that a new sent email was recorded
    try:
        send_event(f"SENT_EMAIL: {record.get('email')} | {record.get('subject')}")
    except Exception:
        pass

    return True
app.secret_key = "super-secret-key-change-this"

# Initialize Firebase Admin SDK
cred = credentials.Certificate("D:/linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json")
firebase_admin.initialize_app(cred)


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
    # Get sent email stats
    sent_emails = load_sent_emails()
    stats = {
        "sent": sum(1 for r in sent_emails if r.get("status") == "sent"),
        "skipped": sum(1 for r in sent_emails if r.get("status") == "skipped"),
        "failed": sum(1 for r in sent_emails if r.get("status") == "failed")
    }
    return render_template("home.html", user=session["user"], stats=stats)


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
    """Render a page listing all sent emails grouped by automation runs."""
    records = load_sent_emails()
    
    # Group emails by run_id
    runs = {}
    for record in records:
        run_id = record.get('run_id', 'unknown')
        run_time = record.get('run_time', record.get('sent_at', ''))
        if run_id not in runs:
            runs[run_id] = {
                'run_id': run_id,
                'run_time': run_time,
                'emails': [],
                'stats': {'sent': 0, 'failed': 0, 'skipped': 0}
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
    """Return JSON array of sent email records."""
    return jsonify(load_sent_emails())


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
def run_automation(subject, email_content, attachment_path, cc_email, run_id=None):
    log("🚀 Starting automation...")
    log(f"📝 Run ID: {run_id}")
    
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
            max_attempts = 8
            
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
                }, run_id)
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
                    })
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

    threading.Thread(
        target=run_automation,
        args=(subject, email_content, resume_path, user_email, run_id),
    ).start()

    flash("🚀 Automation started in background. Check console logs for updates.", "success")
    return redirect(url_for("send_page"))


if __name__ == "__main__":
    app.run(debug=True)
