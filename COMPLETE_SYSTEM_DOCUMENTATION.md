# 🚀 JustMailIt - Complete System Documentation

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Architecture & File Structure](#architecture--file-structure)
3. [Database Schema & Data Flow](#database-schema--data-flow)
4. [Security Analysis & Threats](#security-analysis--threats)
5. [Deployment Infrastructure](#deployment-infrastructure)
6. [API Endpoints & Routes](#api-endpoints--routes)
7. [Payment Integration](#payment-integration)
8. [Authentication & Authorization](#authentication--authorization)
9. [File Locations (Local vs Docker)](#file-locations-local-vs-docker)
10. [Environment Variables & Secrets](#environment-variables--secrets)
11. [Backup & Recovery](#backup--recovery)
12. [Monitoring & Maintenance](#monitoring--maintenance)

---

## 🎯 System Overview

**JustMailIt** is an automated job application platform that:
- Scrapes LinkedIn job postings using Selenium WebDriver
- Automatically sends personalized emails to recruiters
- Uses AI to analyze job descriptions and generate custom cover letters
- Integrates Firebase authentication and Razorpay payments
- Operates on a freemium model (10 emails/day free, unlimited with Pro)

### Technology Stack
- **Backend**: Flask (Python 3.11)
- **Database**: SQLite (`justmailit.db`)
- **Authentication**: Firebase Admin SDK
- **Payment Gateway**: Razorpay
- **Web Scraping**: Selenium + undetected-chromedriver
- **Frontend**: Bootstrap 5, Jinja2 templates
- **Deployment**: Docker on Raspberry Pi (192.168.31.36)
- **Container**: `justmailit-app`

---

## 📁 Architecture & File Structure

### Local Directory Structure (Windows)
```
C:\Users\windows 10\Desktop\AI_support\
├── sendmail/                          # Main application directory
│   ├── app.py                         # Core Flask application (3,170 lines)
│   ├── database.py                    # SQLite database manager (488 lines)
│   ├── job_analyzer.py                # AI-powered job description analyzer
│   ├── firestore_ops.py               # Firestore database operations
│   ├── justmailit.db                  # SQLite database (PRIMARY DATA STORE)
│   ├── justmailit-d6f2d-firebase-adminsdk-fbsvc-552f0c36ab.json  # Firebase credentials ⚠️
│   ├── requirements.txt               # Python dependencies
│   ├── templates/                     # HTML templates (Jinja2)
│   │   ├── landing.html              # Public landing page (4,190 lines)
│   │   ├── pricing.html              # Subscription pricing (844 lines)
│   │   ├── home.html                 # User dashboard
│   │   ├── profile.html              # User profile management
│   │   ├── sent_emails.html          # Email history (596 lines)
│   │   ├── admin.html                # Admin dashboard
│   │   ├── job_posts.html            # Job listings view
│   │   ├── privacy.html              # Privacy policy
│   │   ├── terms.html                # Terms of service
│   │   └── [30+ other templates]
│   ├── static/                        # Static assets
│   │   ├── css/                      # Stylesheets
│   │   └── images/                   # Logo, icons, branding
│   └── uploads/                       # User-uploaded resumes (temporary)
├── chrome-profile/                    # Persistent Chrome session data
├── uploads/                           # Additional upload directory
├── job_posts.json                     # Legacy job posts (being migrated to DB)
├── sent_emails.json                   # Legacy sent emails (being migrated to DB)
├── Dockerfile                         # Production Docker image
├── docker-compose.yml                 # Docker Compose configuration
├── requirements.txt                   # Python dependencies
├── .env.production                    # Production environment variables
└── [60+ documentation files]
```

### Docker Container Structure
```
/app/                                  # Container working directory
├── sendmail/                          # Application code
│   ├── app.py                        # Main Flask app
│   ├── database.py                   # Database manager
│   ├── justmailit.db                 # SQLite database (PERSISTED)
│   ├── templates/                    # HTML templates
│   ├── static/                       # Static files
│   └── uploads/                      # Resume uploads
├── chrome-profile/                    # Chrome session data (PERSISTED)
├── requirements.txt
└── start.sh                          # Startup script
```

---

## 🗄️ Database Schema & Data Flow

### SQLite Database: `justmailit.db`

#### Table: `user_profiles`
**Purpose**: Stores user account data and preferences
```sql
CREATE TABLE user_profiles (
    email TEXT PRIMARY KEY,              -- Firebase user email (unique identifier)
    display_name TEXT,                   -- User's display name
    photo_url TEXT,                      -- Profile picture URL
    email_subject TEXT,                  -- Default email subject line
    email_content TEXT,                  -- Default email template
    search_role TEXT,                    -- Job search role preference
    search_time_period TEXT DEFAULT 'past-week',  -- LinkedIn search filter
    resume_data BLOB,                    -- Resume file stored as binary
    resume_filename TEXT,                -- Original resume filename
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```
**Sensitive Data**: Resume files, email templates, personal information

#### Table: `job_posts`
**Purpose**: Stores scraped job listings and prevents duplicates
```sql
CREATE TABLE job_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL,            -- User who found this job
    title TEXT NOT NULL,                 -- Job title
    company TEXT,                        -- Company name
    location TEXT,                       -- Job location
    job_url TEXT,                        -- LinkedIn job posting URL
    email TEXT,                          -- Recruiter email (extracted)
    posted_date TEXT,                    -- When job was posted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_email) REFERENCES user_profiles(email)
)
```
**Index**: Unique index on (user_email, company, title) to prevent duplicate applications

#### Table: `sent_emails`
**Purpose**: Tracks all emails sent by the system
```sql
CREATE TABLE sent_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL,            -- User who sent the email
    recipient_email TEXT NOT NULL,       -- Recruiter email
    subject TEXT,                        -- Email subject
    content TEXT,                        -- Email body
    company TEXT,                        -- Company name
    job_title TEXT,                      -- Job title applied for
    sent_date TEXT,                      -- ISO format timestamp
    status TEXT DEFAULT 'sent',          -- sent/failed/pending
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_email) REFERENCES user_profiles(email)
)
```
**Index**: Index on (user_email, sent_date) for daily limit enforcement

#### Table: `subscriptions`
**Purpose**: Manages user subscription plans and payment status
```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT UNIQUE NOT NULL,     -- One subscription per user
    plan TEXT DEFAULT 'free',            -- free/pro
    status TEXT DEFAULT 'inactive',      -- active/inactive/cancelled
    razorpay_order_id TEXT,              -- Razorpay order identifier
    razorpay_payment_id TEXT,            -- Razorpay payment identifier
    amount REAL,                         -- Payment amount in INR
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                -- Subscription expiry
    FOREIGN KEY (user_email) REFERENCES user_profiles(email)
)
```
**Critical**: Payment verification happens via Razorpay webhooks

### Data Flow Diagram
```
User Registration (Firebase)
    ↓
user_profiles created
    ↓
User configures profile → resume_data, email_content saved
    ↓
User runs automation → Selenium scrapes LinkedIn
    ↓
job_posts table populated → Duplicate check performed
    ↓
Emails sent via SMTP → sent_emails table updated
    ↓
Daily limit check → Count sent_emails for user today
    ↓
If limit reached → Show upgrade prompt → /pricing
    ↓
Payment via Razorpay → subscriptions table updated
    ↓
Pro user → Unlimited emails
```

---

## 🔒 Security Analysis & Threats

### ⚠️ CRITICAL SECURITY VULNERABILITIES

#### 1. **Hardcoded Credentials in Source Code**
**Location**: `sendmail/app.py` lines 246-247, 270-271, 664
```python
# ❌ EXPOSED IN CODE
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_live_RgNB6M60lUvK2l")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "i4GM8FcOw34g438OMecg2z78")
LINKEDIN_EMAIL = "manudrive04@gmail.com"
LINKEDIN_PASSWORD = "Jpking@232"
app.secret_key = "super-secret-key-change-this"
```
**Risk**: HIGH - Anyone with code access can:
- Access Razorpay account and initiate fraudulent transactions
- Access LinkedIn account
- Forge session cookies with weak secret key

**Mitigation**:
```python
# ✅ CORRECT APPROACH
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")
LINKEDIN_EMAIL = os.environ.get("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.environ.get("LINKEDIN_PASSWORD")
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32).hex())
```

#### 2. **Firebase Admin Credentials in Repository**
**Location**: `sendmail/justmailit-d6f2d-firebase-adminsdk-fbsvc-552f0c36ab.json`
**Risk**: CRITICAL - This file grants full admin access to Firebase:
- Read/write all Firestore data
- Create/delete user accounts
- Bypass all security rules

**Mitigation**:
- Add to `.gitignore` immediately
- Rotate credentials in Firebase Console
- Use environment variable for base64-encoded JSON
- Enable Firebase security rules

#### 3. **SQL Injection Vulnerability**
**Location**: `database.py` - Some queries use f-strings
```python
# ❌ VULNERABLE (if exists)
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")

# ✅ SAFE (currently used)
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
```
**Status**: Most queries use parameterized statements (✅), but verify all DB calls

#### 4. **No HTTPS Enforcement**
**Current**: Running on HTTP (192.168.31.36:5000)
**Risk**: 
- Session cookies transmitted in plaintext
- Man-in-the-middle attacks possible
- Payment data potentially exposed

**Mitigation**:
```python
# Add to app.py
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
```
Use Nginx reverse proxy with Let's Encrypt SSL certificate

#### 5. **Weak Session Management**
```python
app.secret_key = "super-secret-key-change-this"  # ❌ Predictable
```
**Attack**: Session hijacking, CSRF attacks
**Fix**: Use strong random secret key, enable CSRF protection

#### 6. **File Upload Vulnerabilities**
**Location**: Resume upload functionality
**Risks**:
- No file type validation
- No size limits
- Could upload malicious executables
- Path traversal attacks

**Mitigation**:
```python
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
```

#### 7. **Rate Limiting Issues**
**Current**: Only checks daily email limit for logged-in users
**Missing**:
- Login attempt rate limiting (brute force protection)
- API endpoint rate limiting
- Payment endpoint abuse protection

**Mitigation**: Use `flask-limiter`
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: session.get('user'))
@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    ...
```

#### 8. **Exposed Admin Panel**
**Location**: `/admin` route (line 2938)
**Current Protection**: Basic `is_admin()` decorator
**Risks**:
- Admin credentials could be hardcoded
- No IP whitelisting
- No 2FA for admin access

**Verify**: Check `is_admin()` implementation for hardcoded emails

#### 9. **Database Backup Missing**
**Critical**: `justmailit.db` has NO automated backups
**Data at Risk**:
- User profiles and resumes
- Payment records
- Email history

**Mitigation**: Set up daily automated backups to external storage

#### 10. **Insecure Direct Object References (IDOR)**
**Example**: `/admin/user/<email>` route
**Risk**: User could access other users' data by manipulating URL
**Fix**: Verify user owns the resource or is admin before serving data

### 🛡️ Security Checklist

| Item | Status | Priority |
|------|--------|----------|
| Remove hardcoded credentials | ❌ | CRITICAL |
| Rotate Firebase credentials | ❌ | CRITICAL |
| Move to HTTPS | ❌ | HIGH |
| Implement CSRF protection | ❌ | HIGH |
| Add rate limiting | ❌ | HIGH |
| File upload validation | ⚠️ Partial | MEDIUM |
| SQL injection audit | ✅ Mostly safe | MEDIUM |
| Setup automated backups | ❌ | HIGH |
| Environment variable migration | ⚠️ Partial | CRITICAL |
| Admin access 2FA | ❌ | MEDIUM |

### 🎯 Potential Attack Vectors

1. **Credential Theft**: Hardcoded secrets in GitHub repo
2. **Session Hijacking**: Weak secret key + no HTTPS
3. **Payment Fraud**: Razorpay keys exposed → unauthorized transactions
4. **Data Breach**: Firebase admin access → all user data compromised
5. **LinkedIn Account Takeover**: Credentials in code
6. **Brute Force**: No rate limiting on login
7. **Malicious File Upload**: Execute code via resume upload
8. **Database Poisoning**: Inject malicious data via scraping
9. **IDOR**: Access other users' profiles/emails
10. **DDoS**: No rate limiting on expensive operations (scraping)

---

## 🚀 Deployment Infrastructure

### Raspberry Pi Server
- **IP Address**: 192.168.31.36
- **OS**: Raspberry Pi OS (Linux-based)
- **Docker Version**: Docker Engine
- **Container Name**: `justmailit-app`
- **Port Mapping**: 5000:5000
- **Access**: SSH via `manu@192.168.31.36`

### Docker Container Details
```bash
# Container details
Name: justmailit-app
Base Image: python:3.11-slim
Exposed Ports: 5000
Volumes: 
  - /app/sendmail/justmailit.db (persisted)
  - /app/chrome-profile (persisted)
```

### Deployment Workflow (from Windows to Raspberry Pi)
```powershell
# Step 1: Transfer file from local to Raspberry Pi
scp "C:\Users\windows 10\Desktop\AI_support\sendmail\templates\pricing.html" `
    manu@192.168.31.36:/home/manu/justmailit/sendmail/templates/pricing.html

# Step 2: Copy file into running Docker container
ssh manu@192.168.31.36 `
    "sudo docker cp /home/manu/justmailit/sendmail/templates/pricing.html `
     justmailit-app:/app/sendmail/templates/pricing.html"

# Step 3: Restart container to apply changes
ssh manu@192.168.31.36 "sudo docker restart justmailit-app"
```

### File Persistence
**Persisted Data** (survives container restart):
- `/app/sendmail/justmailit.db` - SQLite database
- `/app/chrome-profile/` - Chrome session data
- `/home/manu/justmailit/` - Raspberry Pi filesystem (backup)

**Ephemeral Data** (lost on container rebuild):
- `/app/sendmail/uploads/` - Temporary resume files
- Container logs
- Chrome cache

---

## 🌐 API Endpoints & Routes

### Public Routes (No Authentication)
| Route | Method | Purpose | Template |
|-------|--------|---------|----------|
| `/` | GET | Landing page | `landing.html` |
| `/about` | GET | About page | `about.html` |
| `/pricing` | GET | Subscription plans | `pricing.html` |
| `/contact` | GET | Contact form | `contact.html` |
| `/privacy` | GET | Privacy policy | `privacy.html` |
| `/terms` | GET | Terms of service | `terms.html` |
| `/login` | GET/POST | User login | `login.html` |
| `/sessionLogin` | POST | Firebase session creation | JSON response |
| `/logout` | GET | User logout | Redirect to `/` |

### Protected Routes (Login Required)
| Route | Method | Purpose | Template |
|-------|--------|---------|----------|
| `/dashboard` | GET | User dashboard | `home.html` |
| `/profile` | GET | User profile page | `profile.html` |
| `/get_profile` | GET | Get profile data | JSON response |
| `/save_profile` | POST | Save profile settings | JSON response |
| `/send` | GET | Email composition | `home.html` |
| `/jobs` | GET | Job listings | `job_posts.html` |
| `/sent_emails` | GET | Email history | `sent_emails.html` |
| `/run_automation` | POST | Start LinkedIn scraping | SSE stream |
| `/progress` | GET | Automation progress | SSE stream |

### Payment Routes
| Route | Method | Purpose | Description |
|-------|--------|---------|-------------|
| `/create_payment` | POST | Initialize payment | Creates Razorpay order |
| `/payment/success` | POST | Payment verification | Verifies Razorpay signature |
| `/payment/webhook` | POST | Razorpay webhook | Handles payment events |
| `/payment/callback` | GET | Payment redirect | After payment completion |
| `/check_payment_status/<order_id>` | GET | Poll payment status | AJAX polling |

### Admin Routes
| Route | Method | Purpose | Access |
|-------|--------|---------|--------|
| `/admin` | GET | Admin dashboard | Admin only |
| `/admin/api/stats` | GET | System statistics | Admin only |
| `/admin/user/<email>` | GET | User details | Admin only |

### API Routes (JSON Responses)
| Route | Method | Purpose | Returns |
|-------|--------|---------|---------|
| `/api/sent_emails` | GET | Email history data | JSON array |
| `/api/sent_email_stats` | GET | Email statistics | JSON object |
| `/generate_email_template` | POST | AI email generation | JSON template |
| `/send_job_email` | POST | Send single email | JSON status |
| `/submit_2fa_code` | POST | LinkedIn 2FA | JSON response |

---

## 💳 Payment Integration

### Razorpay Configuration
```python
RAZORPAY_KEY_ID = "rzp_live_RgNB6M60lUvK2l"      # ⚠️ LIVE PRODUCTION KEY
RAZORPAY_KEY_SECRET = "i4GM8FcOw34g438OMecg2z78" # ⚠️ EXPOSED SECRET
```

### Payment Flow
```
User clicks "Upgrade to Pro" → /pricing
    ↓
JavaScript calls /create_payment
    ↓
Server creates Razorpay order
    ↓
Razorpay checkout modal opens
    ↓
User completes payment
    ↓
Razorpay callback → /payment/success
    ↓
Server verifies signature
    ↓
subscriptions table updated (plan=pro, status=active)
    ↓
Webhook confirms payment → /payment/webhook
```

### Payment Security
**Current Issues**:
1. ❌ Payment keys hardcoded in source
2. ❌ No webhook signature verification
3. ⚠️ Relying on client-side payment confirmation

**Best Practices**:
```python
# Verify webhook signature
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Subscription Plans
| Plan | Price | Email Limit | Features |
|------|-------|-------------|----------|
| Free | ₹0 | 10/day | Basic automation |
| Pro | ₹999 | Unlimited | Priority support, AI templates |

---

## 🔐 Authentication & Authorization

### Firebase Authentication
**Service**: Firebase Admin SDK
**Credentials**: `justmailit-d6f2d-firebase-adminsdk-fbsvc-552f0c36ab.json`
**Project ID**: `justmailit-d6f2d`

### Authentication Flow
```python
# Login decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated
```

### Session Management
- **Storage**: Flask server-side sessions
- **Cookie Name**: `session`
- **Expiry**: Browser session (no persistent login)
- **Secret Key**: `super-secret-key-change-this` ⚠️ WEAK

### User Roles
1. **Free User**: Default, 10 emails/day limit
2. **Pro User**: Subscription active, unlimited emails
3. **Admin**: Access to `/admin` routes (email-based check)

### Email Limit Enforcement
```python
def check_email_limit(user_email):
    # Count emails sent today
    today = datetime.now().strftime('%Y-%m-%d')
    count = db.count_emails_sent_today(user_email, today)
    
    # Check subscription status
    subscription = db.get_subscription(user_email)
    if subscription and subscription['plan'] == 'pro':
        return True, count, None  # Unlimited
    
    if count >= 10:
        return False, count, "Daily limit reached (10 emails)"
    return True, count, None
```

---

## 📂 File Locations (Local vs Docker)

### Configuration Files
| File | Local Path | Docker Path | Purpose |
|------|-----------|-------------|---------|
| Main app | `C:\Users\windows 10\Desktop\AI_support\sendmail\app.py` | `/app/sendmail/app.py` | Flask application |
| Database | `C:\Users\windows 10\Desktop\AI_support\sendmail\justmailit.db` | `/app/sendmail/justmailit.db` | SQLite data |
| Firebase creds | `C:\Users\windows 10\Desktop\AI_support\sendmail\justmailit-d6f2d-*.json` | `/app/sendmail/*.json` | Auth credentials |
| Templates | `C:\Users\windows 10\Desktop\AI_support\sendmail\templates\*.html` | `/app/sendmail/templates\*.html` | HTML files |
| Static files | `C:\Users\windows 10\Desktop\AI_support\sendmail\static\` | `/app/sendmail/static\` | CSS, images |
| Chrome profile | `C:\Users\windows 10\Desktop\AI_support\chrome-profile\` | `/app/chrome-profile\` | Browser data |
| Uploads | `C:\Users\windows 10\Desktop\AI_support\sendmail\uploads\` | `/app/sendmail/uploads\` | Resumes |

### Raspberry Pi File System
```
/home/manu/justmailit/               # Deployment directory
├── sendmail/
│   ├── app.py                       # Latest deployed code
│   ├── templates/                   # HTML templates
│   ├── static/                      # Assets
│   └── justmailit.db               # Database backup
└── docker-compose.yml               # Container config
```

### Backup Locations
- **Database**: No automated backups configured ⚠️
- **Code**: Git repository (manuchaturvedi/email-sent-site)
- **Uploads**: Not backed up (ephemeral)

---

## 🔧 Environment Variables & Secrets

### Current Environment Variables
```bash
# Flask Configuration
FLASK_APP=sendmail/app.py
FLASK_ENV=production
SECRET_KEY=super-secret-key-change-this  # ⚠️ CHANGE THIS

# Chrome Configuration
CHROME_PROFILE_DIR=/app/chrome-profile

# Firebase (Base64-encoded JSON)
GOOGLE_APPLICATION_CREDENTIALS_JSON=<base64_encoded_json>  # Not configured

# Razorpay
RAZORPAY_KEY_ID=rzp_live_RgNB6M60lUvK2l        # ⚠️ Currently hardcoded
RAZORPAY_KEY_SECRET=i4GM8FcOw34g438OMecg2z78   # ⚠️ Currently hardcoded

# LinkedIn
LINKEDIN_EMAIL=manudrive04@gmail.com           # ⚠️ Currently hardcoded
LINKEDIN_PASSWORD=Jpking@232                   # ⚠️ Currently hardcoded
```

### Recommended Environment Setup
```bash
# Create .env file (DO NOT COMMIT)
cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
RAZORPAY_KEY_ID=your_key_here
RAZORPAY_KEY_SECRET=your_secret_here
LINKEDIN_EMAIL=your_email@gmail.com
LINKEDIN_PASSWORD=your_password
FIREBASE_CREDS=$(base64 -w 0 firebase-creds.json)
EOF

# Load in Docker
docker run --env-file .env justmailit-app
```

---

## 💾 Backup & Recovery

### Current Backup Status: ❌ NO AUTOMATED BACKUPS

### Critical Data to Backup
1. **SQLite Database** (`justmailit.db`)
   - User profiles and resumes
   - Payment records
   - Email history
   
2. **Firebase Credentials**
   - Admin SDK JSON file
   
3. **Chrome Profile**
   - Persistent LinkedIn login session

### Recommended Backup Strategy

#### Daily Database Backup Script
```bash
#!/bin/bash
# backup-db.sh

BACKUP_DIR="/home/manu/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="justmailit.db"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Copy database from container
docker cp justmailit-app:/app/sendmail/$DB_NAME \
    "$BACKUP_DIR/${DB_NAME}.${DATE}.backup"

# Keep only last 30 days
find "$BACKUP_DIR" -name "*.backup" -mtime +30 -delete

# Compress old backups
find "$BACKUP_DIR" -name "*.backup" -mtime +7 -exec gzip {} \;

echo "Backup completed: ${DB_NAME}.${DATE}.backup"
```

#### Cron Job Setup
```bash
# Run daily at 2 AM
0 2 * * * /home/manu/scripts/backup-db.sh >> /var/log/backup.log 2>&1
```

#### Off-site Backup
```bash
# Upload to cloud storage (example: AWS S3)
aws s3 cp "$BACKUP_DIR/${DB_NAME}.${DATE}.backup" \
    s3://justmailit-backups/database/
```

### Disaster Recovery Plan
1. **Database Corruption**:
   ```bash
   # Restore from backup
   docker cp /home/manu/backups/justmailit.db.latest justmailit-app:/app/sendmail/justmailit.db
   docker restart justmailit-app
   ```

2. **Container Failure**:
   ```bash
   # Rebuild container
   cd /home/manu/justmailit
   docker-compose down
   docker-compose up -d
   ```

3. **Raspberry Pi Failure**:
   - Restore database backup to new server
   - Redeploy Docker container
   - Restore Firebase credentials
   - Reconfigure DNS/IP address

---

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Check if container is running
docker ps | grep justmailit-app

# Check container logs
docker logs justmailit-app --tail 100

# Check database size
docker exec justmailit-app ls -lh /app/sendmail/justmailit.db

# Check memory usage
docker stats justmailit-app --no-stream
```

### Performance Metrics
- **Database Size**: Monitor `justmailit.db` growth
- **Email Throughput**: Track emails sent per day
- **Payment Success Rate**: Monitor Razorpay conversions
- **Scraping Success Rate**: LinkedIn automation errors

### Maintenance Tasks
| Task | Frequency | Command |
|------|-----------|---------|
| Database vacuum | Weekly | `VACUUM;` in SQLite |
| Clear old uploads | Daily | Delete files >7 days |
| Update dependencies | Monthly | `pip install -U -r requirements.txt` |
| Review logs | Daily | `docker logs` |
| Security audit | Quarterly | Review credentials, patches |

### Log Locations
- **Container Logs**: `docker logs justmailit-app`
- **Application Logs**: `print()` statements (no file logging)
- **Nginx Logs**: Not configured (direct container access)

---

## 🚨 Immediate Action Items

### CRITICAL (Do Today)
1. ❌ Remove all hardcoded credentials from `app.py`
2. ❌ Rotate Firebase credentials immediately
3. ❌ Change `SECRET_KEY` to random value
4. ❌ Add `.gitignore` for `*.json` credential files
5. ❌ Setup database backups

### HIGH (This Week)
1. ⚠️ Implement HTTPS with SSL certificate
2. ⚠️ Add CSRF protection
3. ⚠️ Implement rate limiting
4. ⚠️ File upload validation
5. ⚠️ Environment variable migration

### MEDIUM (This Month)
1. ⚠️ Setup monitoring/alerting
2. ⚠️ Implement 2FA for admin
3. ⚠️ Security audit all routes
4. ⚠️ Setup off-site backups
5. ⚠️ Review payment security

---

## 📞 Emergency Contacts & Access

### Server Access
- **SSH**: `manu@192.168.31.36` (password-based)
- **Docker**: `sudo docker exec -it justmailit-app /bin/bash`

### Service Credentials
- **Firebase Console**: https://console.firebase.google.com/project/justmailit-d6f2d
- **Razorpay Dashboard**: https://dashboard.razorpay.com/
- **GitHub Repository**: https://github.com/manuchaturvedi/email-sent-site

### Database Access
```bash
# SSH into Raspberry Pi
ssh manu@192.168.31.36

# Access database in container
sudo docker exec -it justmailit-app sqlite3 /app/sendmail/justmailit.db

# Run queries
sqlite> SELECT COUNT(*) FROM user_profiles;
sqlite> SELECT * FROM subscriptions WHERE plan='pro';
```

---

## 📚 Additional Documentation Files

The repository contains 60+ documentation files covering:
- `DATABASE_SCHEMA.md` - Detailed database structure
- `DEPLOYMENT_GUIDE.md` - Full deployment instructions
- `PAYMENT_TEST_GUIDE.md` - Payment integration testing
- `SECURITY_AUDIT.md` - (Create this based on threats above)
- `FIREBASE_SETUP_RENDER.md` - Firebase configuration
- `RAZORPAY_INTEGRATION_COMPLETE.md` - Payment setup

---

**Document Version**: 1.0  
**Last Updated**: November 20, 2025  
**Maintained By**: System Administrator  
**Review Frequency**: Monthly or after major changes

