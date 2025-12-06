# 🔐 API Keys & Configuration Reference

**JustMailIt - Complete Configuration & Credentials Documentation**

**Last Updated:** December 6, 2025  
**⚠️ WARNING:** This file contains sensitive credentials. Keep secure and never commit to public repositories.

---

## 📋 Table of Contents

1. [Firebase Configuration](#firebase-configuration)
2. [Email SMTP Configuration](#email-smtp-configuration)
3. [Razorpay Payment Gateway](#razorpay-payment-gateway)
4. [Database Configuration](#database-configuration)
5. [OAuth Providers](#oauth-providers)
6. [Application Settings](#application-settings)
7. [Environment Variables](#environment-variables)
8. [Security Best Practices](#security-best-practices)

---

## 🔥 Firebase Configuration

### Firebase Admin SDK (Backend)
**Purpose:** Server-side authentication, user management  
**File Location:** `sendmail/justmailit-d6f2d-firebase-adminsdk-fbsvc-552f0c36ab.json`

```json
{
  "type": "service_account",
  "project_id": "justmailit-d6f2d",
  "private_key_id": "[REDACTED - See actual file]",
  "private_key": "-----BEGIN PRIVATE KEY-----\n[REDACTED]\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@justmailit-d6f2d.iam.gserviceaccount.com",
  "client_id": "[REDACTED]",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40justmailit-d6f2d.iam.gserviceaccount.com"
}
```

**Code Usage (Backend):**
```python
# sendmail/app.py (lines 45-60)
import firebase_admin
from firebase_admin import credentials, auth

# Initialize Firebase Admin SDK
cred = credentials.Certificate('sendmail/justmailit-d6f2d-firebase-adminsdk-fbsvc-552f0c36ab.json')
firebase_admin.initialize_app(cred)

# Verify ID token
def verify_firebase_token(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None
```

---

### Firebase Web Configuration (Frontend)
**Purpose:** Client-side authentication, OAuth  
**File Location:** `sendmail/templates/landing.html` (lines 850-860)

```javascript
// Firebase Web SDK Configuration
const firebaseConfig = {
    apiKey: "AIzaSyAqEkQOtCzx7rOf5pbHlDBHN-Cc_uOnRQw",  // Public key (safe to expose)
    authDomain: "justmailit-d6f2d.firebaseapp.com",
    projectId: "justmailit-d6f2d",
    storageBucket: "justmailit-d6f2d.appspot.com",
    messagingSenderId: "[REDACTED]",
    appId: "[REDACTED]"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
```

**Where Used:**
- Sign In: `auth.signInWithEmailAndPassword(email, password)`
- Sign Up: `auth.createUserWithEmailAndPassword(email, password)`
- Google OAuth: `auth.signInWithPopup(new firebase.auth.GoogleAuthProvider())`
- Facebook OAuth: `auth.signInWithPopup(new firebase.auth.FacebookAuthProvider())`
- Password Reset: `auth.sendPasswordResetEmail(email)`

---

### Firebase Project Details

| Property | Value | Description |
|----------|-------|-------------|
| **Project ID** | `justmailit-d6f2d` | Unique Firebase project identifier |
| **Project Number** | `[REDACTED]` | Numeric project identifier |
| **Web API Key** | `AIzaSyAqEkQOtCzx7rOf5pbHlDBHN-Cc_uOnRQw` | Public API key for web apps |
| **Auth Domain** | `justmailit-d6f2d.firebaseapp.com` | Authentication redirect domain |
| **Storage Bucket** | `justmailit-d6f2d.appspot.com` | Cloud storage location |
| **Database URL** | Not used (using SQLite instead) | Firestore/Realtime DB |

**Console Access:** https://console.firebase.google.com/project/justmailit-d6f2d

---

### Firebase Authentication Methods Enabled

| Method | Status | Configuration Required |
|--------|--------|------------------------|
| **Email/Password** | ✅ Enabled | None (default) |
| **Google OAuth** | ✅ Enabled | OAuth client ID configured |
| **Facebook OAuth** | ✅ Enabled | App ID: (configured in Firebase console) |
| **Phone** | ❌ Disabled | Not implemented |
| **Anonymous** | ❌ Disabled | Not needed |

---

### Firebase Security Rules

**Authentication Required:**
```javascript
// All authenticated users can access
if (request.auth != null) {
    allow read, write;
}
```

**Firestore Rules (if used):**
```javascript
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read, write: if request.auth.uid == userId;
    }
  }
}
```

---

## 📧 Email SMTP Configuration

### Gmail SMTP Settings
**Purpose:** Send job application emails and notifications  
**File Location:** `sendmail/app.py` (lines 70-80)

```python
# Email Configuration
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "manudrive06@gmail.com"
SMTP_PASSWORD = "[REDACTED - 16-char app password]"  # Gmail App Password (not account password)
SENDER_EMAIL = "mail@justmailit.in"    # Display email (requires domain verification)
SENDER_NAME = "JustMailIt"
```

**Connection String Format:**
```
smtp://manudrive06@gmail.com:[REDACTED]@smtp.gmail.com:587
```

---

### Gmail App Password Setup

**How to Generate:**
1. Go to Google Account: https://myaccount.google.com/
2. Navigate to Security → 2-Step Verification
3. Scroll to "App passwords"
4. Select app: "Mail" and device: "Other (Custom name)"
5. Generate password (16 characters, space-separated)
6. Use this instead of regular Google password

**Current App Password:**
```
Name: JustMailIt SMTP
Password: [REDACTED - See .env file]
Generated: November 2024
Expires: Never (unless revoked)
```

---

### SMTP Usage in Code

**Send Email Function:**
```python
# sendmail/services/email_service.py (lines 100-150)
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_html_email(to, subject, body, attachments=[]):
    """Send email via Gmail SMTP"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg['To'] = to
        msg['Subject'] = subject
        
        # Attach HTML body
        msg.attach(MIMEText(body, 'html'))
        
        # Attach files (resume)
        for file_path in attachments:
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 
                               f'attachment; filename={os.path.basename(file_path)}')
                msg.attach(part)
        
        # Connect to SMTP server
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()  # Enable TLS encryption
        server.login(SMTP_USER, SMTP_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False
```

---

### Email Types Sent

| Email Type | Recipient | Trigger | Template Location |
|------------|-----------|---------|-------------------|
| **Job Application** | Recruiter | User clicks "Apply" or automation runs | `services/email_service.py:200` |
| **Missed Opportunity** | User | Free user hits 10-email limit | `services/email_service.py:460` |
| **Success Summary** | User | Automation completes successfully | `services/email_service.py:571` |
| **No Results** | User | Zero jobs found | `services/email_service.py:650` |
| **Welcome Email** | User | New signup | `services/email_service.py:300` |
| **Password Reset** | User | Forgot password (Firebase handles) | Firebase Auth |

---

### Email Rate Limits

**Gmail SMTP Limits:**
- **Per Day:** 500 emails (for Gmail accounts)
- **Per Minute:** 60 emails (to avoid throttling)
- **Recipients per Message:** 100 (To + Cc + Bcc combined)

**Our Implementation:**
```python
# Add delay between emails to avoid rate limiting
import time

for job in jobs_to_apply:
    send_email(job)
    time.sleep(1)  # Wait 1 second between emails
```

---

### Known Email Issues

#### Issue: Sender Shows Wrong Email
**Problem:** Emails show from `manudrive06@gmail.com` instead of `mail@justmailit.in`  
**Cause:** Domain not verified in Gmail  
**Fix Required:**
1. Go to Gmail Settings → Accounts
2. Click "Add another email address"
3. Enter: `mail@justmailit.in`
4. Verify ownership via DNS or confirmation email
5. Set up SPF and DKIM records for justmailit.in domain

**SPF Record (Add to DNS):**
```
justmailit.in TXT "v=spf1 include:_spf.google.com ~all"
```

**DKIM Record (Add to DNS):**
```
google._domainkey.justmailit.in TXT "v=DKIM1; k=rsa; p=[public_key_from_gmail]"
```

---

## 💳 Razorpay Payment Gateway

### Razorpay API Keys
**Purpose:** Process Pro subscription payments  
**File Location:** `sendmail/app.py` (lines 85-95)

```python
# Razorpay Configuration
RAZORPAY_KEY_ID = "rzp_live_[REDACTED]"      # Public key (safe to expose)
RAZORPAY_KEY_SECRET = "[REDACTED]"  # Secret key (keep secure!)
RAZORPAY_WEBHOOK_SECRET = "whsec_[REDACTED]"    # Webhook signature verification
```

**Test Mode Keys (for development):**
```python
RAZORPAY_KEY_ID = "rzp_test_[REDACTED]"
RAZORPAY_KEY_SECRET = "[REDACTED]"
```

---

### Razorpay Integration Code

**Create Order (Backend):**
```python
# sendmail/app.py - create_order route
import razorpay

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@app.route('/create_order', methods=['POST'])
def create_order():
    """Create Razorpay order for subscription"""
    data = request.get_json()
    plan = data.get('plan')  # 'pro_monthly' or 'pro_yearly'
    
    # Determine amount based on plan
    amount = 19900 if plan == 'pro_monthly' else 199900  # In paise (₹199 or ₹1999)
    
    # Create order
    order_data = {
        'amount': amount,
        'currency': 'INR',
        'receipt': f'order_{user_id}_{int(time.time())}',
        'notes': {
            'user_id': user_id,
            'plan': plan
        }
    }
    
    order = razorpay_client.order.create(data=order_data)
    
    return jsonify({
        'id': order['id'],
        'amount': order['amount'],
        'currency': order['currency']
    })
```

---

**Payment Verification (Backend):**
```python
@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    """Verify Razorpay payment signature"""
    data = request.get_json()
    
    # Get payment details
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    
    # Verify signature
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    
    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        # Payment verified - update subscription
        db.execute("""
            UPDATE subscriptions 
            SET plan='pro', 
                start_date=CURRENT_TIMESTAMP,
                end_date=DATE(CURRENT_TIMESTAMP, '+1 year'),
                is_active=1
            WHERE user_id=?
        """, (user_id,))
        
        return jsonify({'success': True})
    except razorpay.errors.SignatureVerificationError:
        return jsonify({'success': False, 'error': 'Invalid signature'}), 400
```

---

**Frontend Integration:**
```javascript
// sendmail/templates/subscription.html
async function upgradeToPro() {
    // 1. Create order on backend
    const response = await fetch('/create_order', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({plan: 'pro_monthly'})
    });
    
    const order = await response.json();
    
    // 2. Open Razorpay checkout
    const options = {
        key: 'rzp_live_[REDACTED]',  // Public key
        amount: order.amount,
        currency: 'INR',
        name: 'JustMailIt',
        description: 'Pro Subscription - Monthly',
        image: '/static/images/logo.png',
        order_id: order.id,
        handler: function(response) {
            // 3. Payment successful - verify on backend
            verifyPayment(response);
        },
        prefill: {
            name: user.name,
            email: user.email,
            contact: user.phone
        },
        theme: {
            color: '#8b9fff'
        }
    };
    
    const rzp = new Razorpay(options);
    rzp.open();
}
```

---

### Razorpay Webhook Configuration

**Webhook URL:** `https://justmailit.in/razorpay/webhook`

**Events to Listen:**
- `payment.captured` - Payment successful
- `payment.failed` - Payment failed
- `subscription.cancelled` - User cancelled
- `subscription.expired` - Subscription expired

**Webhook Handler:**
```python
@app.route('/razorpay/webhook', methods=['POST'])
def razorpay_webhook():
    """Handle Razorpay webhook events"""
    # Verify webhook signature
    webhook_signature = request.headers.get('X-Razorpay-Signature')
    webhook_secret = RAZORPAY_WEBHOOK_SECRET
    
    payload = request.data.decode('utf-8')
    
    try:
        razorpay_client.utility.verify_webhook_signature(
            payload, 
            webhook_signature, 
            webhook_secret
        )
    except razorpay.errors.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Process event
    event = request.json
    event_type = event.get('event')
    
    if event_type == 'payment.captured':
        # Update subscription
        payment = event['payload']['payment']['entity']
        handle_payment_success(payment)
    
    elif event_type == 'payment.failed':
        # Notify user
        payment = event['payload']['payment']['entity']
        handle_payment_failure(payment)
    
    return jsonify({'status': 'ok'})
```

---

### Razorpay Dashboard Access

**Live Dashboard:** https://dashboard.razorpay.com/  
**Login:** manudrive06@gmail.com  
**Password:** [Your Razorpay password]

**Key Sections:**
- **Transactions:** View all payments
- **Customers:** User payment details
- **Subscriptions:** Recurring payments (if used)
- **Settings → API Keys:** Generate/view keys
- **Settings → Webhooks:** Configure webhook endpoints

---

## 🗄️ Database Configuration

### SQLite Database
**Purpose:** Store users, jobs, emails, subscriptions  
**File Location:** `/home/manu/justmailit/justmailit.db` (production)  
**File Location:** `justmailit.db` (development)

**Connection String:**
```python
# sendmail/database.py
import sqlite3

DATABASE_PATH = 'justmailit.db'

def get_db_connection():
    """Create database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
    conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for concurrency
    return conn
```

---

### Database Initialization

**Schema Creation:**
```python
# sendmail/database.py
def init_database():
    """Initialize database with tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables (see DATABASE_REFERENCE.md for full schemas)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            resume_path TEXT,
            cover_letter TEXT,
            skills TEXT,
            experience_years INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    
    # ... (other tables)
    
    conn.commit()
    conn.close()
```

---

### Database Backup Configuration

**Automated Backup Script:**
```bash
#!/bin/bash
# /home/manu/justmailit/backup_db.sh

DB_PATH="/home/manu/justmailit/justmailit.db"
BACKUP_DIR="/home/manu/justmailit/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/justmailit_backup_$DATE.db"

# Create backup
cp "$DB_PATH" "$BACKUP_FILE"

# Keep only last 30 days
find "$BACKUP_DIR" -name "justmailit_backup_*.db" -mtime +30 -delete

echo "Backup created: $BACKUP_FILE"
```

**Cron Job (runs daily at 2 AM):**
```cron
0 2 * * * /home/manu/justmailit/backup_db.sh >> /home/manu/justmailit/backup.log 2>&1
```

---

### Database Access Credentials

**SQLite has no authentication** (file-based)

**Security:**
- File permissions: `chmod 600 justmailit.db` (owner read/write only)
- Owner: `manu:manu`
- No network access (local file only)

**Access from Python:**
```python
import sqlite3
conn = sqlite3.connect('/home/manu/justmailit/justmailit.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM user_profiles LIMIT 5")
print(cursor.fetchall())
conn.close()
```

**Access from Command Line:**
```bash
sqlite3 /home/manu/justmailit/justmailit.db
.tables
SELECT * FROM user_profiles LIMIT 5;
.quit
```

---

## 🔐 OAuth Providers

### Google OAuth
**Purpose:** Allow users to sign in with Google account  
**Provider:** Firebase Authentication (Google Sign-In)

**Configuration:**
```javascript
// Frontend: landing.html
const googleProvider = new firebase.auth.GoogleAuthProvider();
googleProvider.addScope('email');
googleProvider.addScope('profile');

async function handleGoogleAuth() {
    try {
        const result = await auth.signInWithPopup(googleProvider);
        const user = result.user;
        const idToken = await user.getIdToken();
        
        // Send to backend
        await fetch('/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                idToken: idToken,
                displayName: user.displayName
            })
        });
    } catch (error) {
        console.error('Google auth error:', error);
    }
}
```

**OAuth Credentials:**
- **Client ID:** Configured in Firebase Console
- **Client Secret:** Managed by Firebase
- **Authorized Domains:** justmailit.in, justmailit-d6f2d.firebaseapp.com

**Scopes Requested:**
- `email` - User's email address
- `profile` - User's name and profile picture

---

### Facebook OAuth
**Purpose:** Allow users to sign in with Facebook account  
**Provider:** Firebase Authentication (Facebook Login)

**Configuration:**
```javascript
// Frontend: landing.html
const facebookProvider = new firebase.auth.FacebookAuthProvider();
facebookProvider.addScope('email');
facebookProvider.addScope('public_profile');

async function handleFacebookAuth() {
    try {
        const result = await auth.signInWithPopup(facebookProvider);
        const user = result.user;
        
        // Check if email is provided (Facebook may not give email)
        if (!user.email) {
            // Prompt user to provide email
            showEmailCollectionModal();
            return;
        }
        
        const idToken = await user.getIdToken();
        
        // Send to backend
        await fetch('/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                idToken: idToken,
                displayName: user.displayName
            })
        });
    } catch (error) {
        console.error('Facebook auth error:', error);
    }
}
```

**OAuth Credentials:**
- **App ID:** Configured in Firebase Console
- **App Secret:** Managed by Firebase
- **Valid OAuth Redirect URIs:** `https://justmailit-d6f2d.firebaseapp.com/__/auth/handler`

**Scopes Requested:**
- `email` - User's email (may be declined)
- `public_profile` - User's name and profile picture

---

## ⚙️ Application Settings

### Flask Secret Key
**Purpose:** Session encryption, CSRF protection  
**File Location:** `sendmail/app.py` (line 40)

```python
# Flask Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session expires after 7 days
```

**Generate New Secret Key:**
```python
import secrets
print(secrets.token_hex(32))
# Output: 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2'
```

---

### File Upload Settings
**Purpose:** Configure resume upload limits and storage  
**File Location:** `sendmail/app.py` (lines 100-110)

```python
# File Upload Configuration
UPLOAD_FOLDER = '/uploads/resumes'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
```

---

### Selenium WebDriver Configuration
**Purpose:** LinkedIn job scraping  
**File Location:** `linkedin_job_scraper.py` (lines 20-40)

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

def get_driver():
    """Initialize Chrome WebDriver with options"""
    options = Options()
    options.add_argument('--headless')  # Run without GUI
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Use undetected chromedriver to bypass bot detection
    driver = uc.Chrome(options=options)
    return driver
```

**ChromeDriver Path:**
- **Development:** Auto-downloaded by undetected-chromedriver
- **Production (Raspberry Pi):** `/usr/bin/chromium-driver`

---

### Rate Limiting Configuration
**Purpose:** Prevent API abuse and overload  
**File Location:** `sendmail/app.py` (lines 120-130)

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Apply to specific routes
@app.route('/run_automation', methods=['POST'])
@limiter.limit("5 per hour")  # Max 5 automation runs per hour
def run_automation():
    # ...
```

---

## 🌐 Environment Variables

### Production Environment (.env file)
**File Location:** `/home/manu/justmailit/.env`

```bash
# Flask
FLASK_ENV=production
SECRET_KEY=your-production-secret-key-here

# Database
DATABASE_PATH=/home/manu/justmailit/justmailit.db

# Firebase
FIREBASE_CREDENTIALS_PATH=/home/manu/justmailit/sendmail/justmailit-d6f2d-firebase-adminsdk-fbsvc-552f0c36ab.json

# Email SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=manudrive06@gmail.com
SMTP_PASSWORD=[REDACTED]
SENDER_EMAIL=mail@justmailit.in

# Razorpay
RAZORPAY_KEY_ID=rzp_live_[REDACTED]
RAZORPAY_KEY_SECRET=[REDACTED]
RAZORPAY_WEBHOOK_SECRET=whsec_[REDACTED]

# Application
UPLOAD_FOLDER=/home/manu/justmailit/uploads/resumes
MAX_FILE_SIZE_MB=5
FREE_PLAN_DAILY_LIMIT=10

# Server
HOST=0.0.0.0
PORT=5000
```

---

### Development Environment (.env.development)
**File Location:** Local development machine

```bash
# Flask
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=dev-secret-key-not-for-production

# Database
DATABASE_PATH=justmailit.db

# Firebase
FIREBASE_CREDENTIALS_PATH=sendmail/justmailit-d6f2d-firebase-adminsdk-fbsvc-552f0c36ab.json

# Email SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=manudrive06@gmail.com
SMTP_PASSWORD=[REDACTED]
SENDER_EMAIL=mail@justmailit.in

# Razorpay (Test Keys)
RAZORPAY_KEY_ID=rzp_test_[REDACTED]
RAZORPAY_KEY_SECRET=[REDACTED]

# Application
UPLOAD_FOLDER=uploads/resumes
MAX_FILE_SIZE_MB=5
FREE_PLAN_DAILY_LIMIT=10

# Server
HOST=127.0.0.1
PORT=5000
```

---

### Loading Environment Variables

```python
# sendmail/app.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Access variables
SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-key')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'justmailit.db')
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
```

**Install python-dotenv:**
```bash
pip install python-dotenv
```

---

## 🔒 Security Best Practices

### 1. Never Commit Credentials

**Add to .gitignore:**
```gitignore
# Credentials and secrets
.env
.env.*
*.json  # Firebase credentials
justmailit.db
*.db

# Upload folders
uploads/

# Python
__pycache__/
*.pyc
.venv/
```

---

### 2. Rotate Credentials Regularly

**Schedule:**
- **Firebase:** Review access every 6 months
- **SMTP Password:** Regenerate yearly
- **Razorpay Keys:** Check for leaks monthly
- **Flask Secret Key:** Change on suspected breach

---

### 3. Use Environment Variables

**Never hardcode in source:**
```python
# ❌ BAD
SMTP_PASSWORD = "ozds nrqo gduy mnwd"

# ✅ GOOD
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
```

---

### 4. Restrict File Permissions

```bash
# Credentials file
chmod 600 .env
chmod 600 *.json

# Database
chmod 600 justmailit.db

# Uploads directory
chmod 755 uploads/
chmod 644 uploads/resumes/*
```

---

### 5. Enable HTTPS Only

**Force HTTPS in Flask:**
```python
@app.before_request
def force_https():
    if not request.is_secure and app.config['ENV'] == 'production':
        return redirect(request.url.replace('http://', 'https://'))
```

---

### 6. Monitor for Breaches

**Services to check:**
- **Have I Been Pwned:** https://haveibeenpwned.com/
- **GitHub Secret Scanning:** Automatic for public repos
- **Google Security Checkup:** https://myaccount.google.com/security-checkup

---

### 7. Backup Credentials Securely

**Methods:**
1. **Password Manager:** 1Password, LastPass, Bitwarden
2. **Encrypted Cloud:** Google Drive with encryption
3. **Hardware Key:** YubiKey for 2FA
4. **Paper Backup:** Store in safe/vault

---

## 📊 Configuration Summary Table

| Service | Type | Key/Credential | Location | Public? |
|---------|------|----------------|----------|---------|
| **Firebase Web** | API Key | `AIzaSyAqEkQOtCzx7rOf5pbHlDBHN-Cc_uOnRQw` | Frontend JS | ✅ Yes (safe) |
| **Firebase Admin** | Service Account JSON | `justmailit-d6f2d-firebase-adminsdk...json` | Backend | ❌ Secret |
| **Gmail SMTP** | Username | `manudrive06@gmail.com` | Backend | ⚠️ Semi-public |
| **Gmail SMTP** | App Password | `[REDACTED]` | Backend | ❌ Secret |
| **Razorpay Live** | Key ID | `rzp_live_[REDACTED]` | Frontend/Backend | ✅ Yes (safe) |
| **Razorpay Live** | Key Secret | `[REDACTED]` | Backend | ❌ Secret |
| **Razorpay Webhook** | Secret | `whsec_[REDACTED]` | Backend | ❌ Secret |
| **Flask** | Secret Key | `your-secret-key-here` | Backend | ❌ Secret |
| **SQLite** | Database File | `justmailit.db` | Backend | ❌ Secure file |

---

## 🔧 Troubleshooting

### Firebase Connection Issues

**Error:** "Failed to initialize Firebase"

**Check:**
```bash
# Verify JSON file exists
ls -la sendmail/justmailit-d6f2d-firebase-adminsdk-fbsvc-552f0c36ab.json

# Check file permissions
chmod 600 sendmail/justmailit-d6f2d-firebase-adminsdk-fbsvc-552f0c36ab.json

# Verify JSON is valid
python -m json.tool sendmail/justmailit-d6f2d-firebase-adminsdk-fbsvc-552f0c36ab.json
```

---

### SMTP Connection Issues

**Error:** "Authentication failed" or "Connection refused"

**Solutions:**
1. **Verify credentials:**
   ```python
   import smtplib
   server = smtplib.SMTP('smtp.gmail.com', 587)
   server.starttls()
   server.login('manudrive06@gmail.com', '[REDACTED]')
   print("✅ Login successful")
   ```

2. **Check Gmail settings:**
   - 2FA enabled? (required for app passwords)
   - App password valid?
   - Less secure apps: OFF (use app passwords instead)

3. **Test with telnet:**
   ```bash
   telnet smtp.gmail.com 587
   ```

---

### Razorpay Payment Failures

**Error:** "Invalid key" or "Signature verification failed"

**Check:**
1. Using correct keys (live vs test)
2. Webhook secret matches
3. Network connectivity to Razorpay API

**Test API connection:**
```python
import razorpay
client = razorpay.Client(auth=('rzp_live_[REDACTED]', '[REDACTED]'))
print(client.payment.all())  # Should return payment list
```

---

## 📞 Support Contacts

### Service Providers

| Service | Support URL | Email | Phone |
|---------|-------------|-------|-------|
| **Firebase** | https://firebase.google.com/support | - | - |
| **Gmail** | https://support.google.com/mail | - | - |
| **Razorpay** | https://razorpay.com/support | support@razorpay.com | +91-80-6906-6999 |

---

## 📝 Change Log

| Date | Service | Change | Reason |
|------|---------|--------|--------|
| Nov 2024 | Gmail SMTP | Generated app password | Initial setup |
| Nov 2024 | Firebase | Created project | User authentication |
| Nov 2024 | Razorpay | Registered account | Payment processing |
| Dec 2025 | Documentation | Created this guide | Complete reference |

---

**⚠️ IMPORTANT SECURITY REMINDER:**

This document contains **sensitive credentials**. Keep it:
- ✅ In secure, encrypted storage
- ✅ Access-restricted (only authorized personnel)
- ❌ Never in public repositories
- ❌ Never in plain text emails
- ❌ Never shared via unsecured channels

**If any credential is compromised, rotate immediately!**

---

**End of API Keys & Configuration Reference**

*For implementation details, see SYSTEM_DOCUMENTATION.md*  
*For deployment, see PRODUCTION_SUMMARY.md*
