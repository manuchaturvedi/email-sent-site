# Database Quick Reference Guide

**JustMailIt Database Schema & Mappings**

---

## 📊 Database Overview

**Database File:** `justmailit.db`  
**Type:** SQLite 3  
**Location (Production):** `/home/manu/justmailit/justmailit.db`  
**Backup Location:** `/home/manu/justmailit/backups/`

---

## 🗂️ Table Relationships

```
user_profiles (user_id)
    ↓
    ├─→ subscriptions (user_id) [1:1]
    ├─→ sent_emails (user_id) [1:Many]
    └─→ scheduler_jobs (user_id) [1:Many]

job_posts (job_id)
    ↓
    └─→ sent_emails (job_id) [1:Many]
```

---

## 📋 Table Schemas with Examples

### 1. user_profiles

**Purpose:** Store user account information and profile settings

```sql
CREATE TABLE user_profiles (
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
);
```

**Example Row:**
```
id: 1
user_id: "firebase_uid_abc123xyz"
email: "john.doe@gmail.com"
name: "John Doe"
resume_path: "/uploads/resumes/resume_abc123_20251206.pdf"
cover_letter: "I am a passionate developer..."
skills: "Python,Flask,JavaScript,React,SQL"
experience_years: 3
created_at: "2025-12-01 10:30:00"
last_login: "2025-12-06 15:45:00"
is_active: 1
```

**Related Routes:**
- `GET /profile` - Display profile page
- `POST /profile` - Update profile data
- `POST /upload_resume` - Upload resume file

**Key Queries:**
```sql
-- Get user profile by Firebase UID
SELECT * FROM user_profiles WHERE user_id = ?;

-- Update last login
UPDATE user_profiles SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?;

-- Count active users
SELECT COUNT(*) FROM user_profiles WHERE is_active = 1;
```

---

### 2. job_posts

**Purpose:** Cache scraped job listings from LinkedIn

```sql
CREATE TABLE job_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    job_type TEXT,
    posted_date TEXT,
    description TEXT,
    recruiter_email TEXT,
    job_url TEXT,
    skills_required TEXT,
    experience_required TEXT,
    salary_range TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

**Example Row:**
```
id: 45
job_id: "3754892156"
title: "Senior Python Developer"
company: "Tech Solutions Inc"
location: "Mumbai, India"
job_type: "Full-time"
posted_date: "2025-12-05"
description: "We are seeking a senior Python developer..."
recruiter_email: "hr@techsolutions.com"
job_url: "https://www.linkedin.com/jobs/view/3754892156"
skills_required: "Python,Django,PostgreSQL,Docker"
experience_required: "3-5 years"
salary_range: "₹12-18 LPA"
scraped_at: "2025-12-06 14:20:30"
is_active: 1
```

**Related Routes:**
- `GET /jobs` - Display job listings page
- `POST /run_automation` - Scrape and save new jobs
- `GET /api/jobs` - Fetch jobs as JSON

**Key Queries:**
```sql
-- Get all active jobs sorted by date
SELECT * FROM job_posts 
WHERE is_active = 1 
ORDER BY posted_date DESC;

-- Check if job already exists
SELECT COUNT(*) FROM job_posts WHERE job_id = ?;

-- Find jobs by skill
SELECT * FROM job_posts 
WHERE skills_required LIKE '%Python%' 
AND is_active = 1;

-- Get jobs posted today
SELECT * FROM job_posts 
WHERE DATE(posted_date) = DATE('now');
```

**Important Notes:**
- `job_id` extracted from LinkedIn URL: `/jobs/view/{job_id}`
- `posted_date` format: `YYYY-MM-DD` (fallback to `1970-01-01` if missing)
- `recruiter_email` extracted via regex from description

---

### 3. sent_emails

**Purpose:** Track all job application emails sent by users

```sql
CREATE TABLE sent_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    subject TEXT,
    body TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent',
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id),
    FOREIGN KEY (job_id) REFERENCES job_posts(job_id)
);
```

**Example Row:**
```
id: 128
user_id: "firebase_uid_abc123xyz"
job_id: "3754892156"
recipient_email: "hr@techsolutions.com"
subject: "Application for Senior Python Developer - John Doe"
body: "Dear Hiring Manager,\n\nI am writing to express..."
sent_at: "2025-12-06 14:25:45"
status: "sent"
```

**Related Routes:**
- `GET /sent_emails` - View email history
- `POST /run_automation` - Send emails and record
- `GET /api/recent_sent_emails` - Fetch recent emails

**Key Queries:**
```sql
-- Count emails sent today by user
SELECT COUNT(*) FROM sent_emails 
WHERE user_id = ? 
AND DATE(sent_at) = DATE('now');

-- Check if user already applied to job
SELECT COUNT(*) FROM sent_emails 
WHERE user_id = ? AND job_id = ?;

-- Get user's email history with job details
SELECT e.*, j.title, j.company 
FROM sent_emails e
LEFT JOIN job_posts j ON e.job_id = j.job_id
WHERE e.user_id = ?
ORDER BY e.sent_at DESC;

-- Total emails sent this week
SELECT COUNT(*) FROM sent_emails 
WHERE sent_at >= DATE('now', '-7 days');
```

**Status Values:**
- `sent` - Successfully delivered
- `failed` - SMTP error occurred
- `bounced` - Email bounced back

---

### 4. subscriptions

**Purpose:** Manage user subscription plans and limits

```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    plan TEXT DEFAULT 'free',
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    emails_per_day INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
);
```

**Example Rows:**

**Free Plan User:**
```
id: 1
user_id: "firebase_uid_abc123xyz"
plan: "free"
start_date: "2025-12-01 10:30:00"
end_date: NULL
is_active: 1
emails_per_day: 10
created_at: "2025-12-01 10:30:00"
```

**Pro Plan User:**
```
id: 5
user_id: "firebase_uid_def456uvw"
plan: "pro"
start_date: "2025-11-15 14:20:00"
end_date: "2026-11-15 14:20:00"
is_active: 1
emails_per_day: 9999
created_at: "2025-11-15 14:20:00"
```

**Related Routes:**
- `GET /subscription` - View subscription page
- `POST /upgrade` - Upgrade to Pro plan
- `POST /cancel_subscription` - Downgrade to Free

**Key Queries:**
```sql
-- Get user's subscription
SELECT * FROM subscriptions WHERE user_id = ?;

-- Check if user is Pro
SELECT plan FROM subscriptions 
WHERE user_id = ? AND is_active = 1;

-- Count Pro subscribers
SELECT COUNT(*) FROM subscriptions 
WHERE plan = 'pro' AND is_active = 1;

-- Find expiring subscriptions (next 7 days)
SELECT * FROM subscriptions 
WHERE plan = 'pro' 
AND end_date BETWEEN DATE('now') AND DATE('now', '+7 days');
```

**Plan Comparison:**

| Feature | Free | Pro |
|---------|------|-----|
| Daily Email Limit | 10 | Unlimited (9999) |
| Job Scraping | ✅ | ✅ |
| Resume Upload | ✅ | ✅ |
| Email History | ✅ | ✅ |
| Priority Support | ❌ | ✅ |
| Monthly Cost | ₹0 | ₹199 |

---

### 5. scheduler_jobs (Optional)

**Purpose:** Track scheduled automation runs

```sql
CREATE TABLE scheduler_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    job_name TEXT NOT NULL,
    next_run TIMESTAMP,
    last_run TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Example Row:**
```
id: 3
user_id: "firebase_uid_abc123xyz"
job_name: "Daily Job Search - Python Developer Mumbai"
next_run: "2025-12-07 09:00:00"
last_run: "2025-12-06 09:00:00"
is_active: 1
created_at: "2025-12-01 10:30:00"
```

**Key Queries:**
```sql
-- Get pending scheduled jobs
SELECT * FROM scheduler_jobs 
WHERE is_active = 1 
AND next_run <= CURRENT_TIMESTAMP
ORDER BY next_run ASC;

-- Update last run time
UPDATE scheduler_jobs 
SET last_run = CURRENT_TIMESTAMP,
    next_run = DATETIME(CURRENT_TIMESTAMP, '+1 day')
WHERE id = ?;
```

---

## 🔗 Common Join Queries

### Get User's Application History with Job Details
```sql
SELECT 
    e.sent_at,
    e.recipient_email,
    e.status,
    j.title AS job_title,
    j.company,
    j.location,
    j.job_url
FROM sent_emails e
INNER JOIN job_posts j ON e.job_id = j.job_id
WHERE e.user_id = ?
ORDER BY e.sent_at DESC
LIMIT 50;
```

### Get User Profile with Subscription Info
```sql
SELECT 
    u.name,
    u.email,
    u.skills,
    u.experience_years,
    s.plan,
    s.emails_per_day,
    s.end_date
FROM user_profiles u
LEFT JOIN subscriptions s ON u.user_id = s.user_id
WHERE u.user_id = ?;
```

### Find Jobs Not Yet Applied To
```sql
SELECT j.*
FROM job_posts j
WHERE j.is_active = 1
AND j.job_id NOT IN (
    SELECT job_id 
    FROM sent_emails 
    WHERE user_id = ?
)
ORDER BY j.posted_date DESC;
```

---

## 📈 Analytics Queries

### Daily Email Stats
```sql
SELECT 
    DATE(sent_at) as date,
    COUNT(*) as total_emails,
    COUNT(DISTINCT user_id) as unique_users
FROM sent_emails
WHERE sent_at >= DATE('now', '-30 days')
GROUP BY DATE(sent_at)
ORDER BY date DESC;
```

### Top Job Titles
```sql
SELECT 
    title,
    COUNT(*) as application_count
FROM sent_emails e
INNER JOIN job_posts j ON e.job_id = j.job_id
WHERE e.sent_at >= DATE('now', '-7 days')
GROUP BY title
ORDER BY application_count DESC
LIMIT 10;
```

### User Activity Report
```sql
SELECT 
    u.email,
    u.name,
    s.plan,
    COUNT(e.id) as emails_sent_today,
    u.last_login
FROM user_profiles u
LEFT JOIN subscriptions s ON u.user_id = s.user_id
LEFT JOIN sent_emails e ON u.user_id = e.user_id 
    AND DATE(e.sent_at) = DATE('now')
WHERE u.is_active = 1
GROUP BY u.user_id
ORDER BY emails_sent_today DESC;
```

---

## 🛠️ Maintenance Queries

### Cleanup Old Jobs (Over 30 Days)
```sql
UPDATE job_posts 
SET is_active = 0 
WHERE DATE(scraped_at) < DATE('now', '-30 days');
```

### Delete Inactive User Data
```sql
DELETE FROM user_profiles 
WHERE is_active = 0 
AND last_login < DATE('now', '-180 days');
```

### Reset Daily Email Counts (Midnight Job)
```sql
-- No action needed - counts calculated dynamically from sent_emails table
-- Just query: WHERE DATE(sent_at) = DATE('now')
```

---

## 🔍 Debugging Queries

### Check User's Daily Limit Status
```sql
SELECT 
    u.email,
    s.plan,
    s.emails_per_day as limit,
    COUNT(e.id) as sent_today,
    (s.emails_per_day - COUNT(e.id)) as remaining
FROM user_profiles u
LEFT JOIN subscriptions s ON u.user_id = s.user_id
LEFT JOIN sent_emails e ON u.user_id = e.user_id 
    AND DATE(e.sent_at) = DATE('now')
WHERE u.user_id = ?
GROUP BY u.user_id;
```

### Find Duplicate Job Entries
```sql
SELECT job_id, COUNT(*) as count
FROM job_posts
GROUP BY job_id
HAVING count > 1;
```

### Check Missing Recruiter Emails
```sql
SELECT job_id, title, company
FROM job_posts
WHERE recruiter_email IS NULL 
OR recruiter_email = ''
AND is_active = 1
LIMIT 20;
```

---

## 📊 Database Indexes (Performance)

### Recommended Indexes
```sql
-- Speed up duplicate email checks
CREATE INDEX idx_sent_emails_user_job ON sent_emails(user_id, job_id);

-- Speed up daily limit queries
CREATE INDEX idx_sent_emails_user_date ON sent_emails(user_id, sent_at);

-- Speed up job searches
CREATE INDEX idx_job_posts_active_date ON job_posts(is_active, posted_date);

-- Speed up job ID lookups
CREATE INDEX idx_job_posts_job_id ON job_posts(job_id);

-- Speed up user lookups
CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_email ON user_profiles(email);
```

---

## 🔐 Database Security

### Backup Strategy
```bash
# Daily automated backup
0 2 * * * cp /home/manu/justmailit/justmailit.db /home/manu/justmailit/backups/justmailit_$(date +\%Y\%m\%d).db

# Keep only last 30 days
0 3 * * * find /home/manu/justmailit/backups/ -name "justmailit_*.db" -mtime +30 -delete
```

### File Permissions
```bash
chmod 600 justmailit.db  # Owner read/write only
chown manu:manu justmailit.db
```

### Connection Settings
```python
# In Python code
import sqlite3

# Enable foreign key constraints
conn = sqlite3.connect('justmailit.db')
conn.execute("PRAGMA foreign_keys = ON")

# Enable WAL mode for better concurrency
conn.execute("PRAGMA journal_mode = WAL")
```

---

## 📱 Database Access Tools

### Command Line (SQLite3)
```bash
# Open database
sqlite3 justmailit.db

# Common commands
.tables                    # List all tables
.schema user_profiles      # Show table structure
.mode column              # Pretty print mode
.headers on               # Show column names

# Example query
SELECT * FROM user_profiles LIMIT 5;

# Exit
.quit
```

### GUI Tools
- **DB Browser for SQLite** - https://sqlitebrowser.org/
- **DBeaver** - https://dbeaver.io/
- **TablePlus** - https://tableplus.com/

---

## 🆘 Quick Troubleshooting

### User Can't Send Emails
```sql
-- Check subscription and limit
SELECT 
    u.email,
    s.plan,
    COUNT(e.id) as emails_sent_today
FROM user_profiles u
LEFT JOIN subscriptions s ON u.user_id = s.user_id
LEFT JOIN sent_emails e ON u.user_id = e.user_id 
    AND DATE(e.sent_at) = DATE('now')
WHERE u.email = 'user@example.com'
GROUP BY u.user_id;
```

### Jobs Not Showing Up
```sql
-- Check if jobs are active
SELECT 
    COUNT(*) as total_jobs,
    COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_jobs,
    COUNT(CASE WHEN recruiter_email IS NOT NULL THEN 1 END) as with_email
FROM job_posts;
```

### Duplicate Emails Being Sent
```sql
-- Find duplicate entries
SELECT user_id, job_id, COUNT(*) as count
FROM sent_emails
GROUP BY user_id, job_id
HAVING count > 1;
```

---

**End of Database Reference**

*Use this guide for quick lookups when working with the JustMailIt database.*
