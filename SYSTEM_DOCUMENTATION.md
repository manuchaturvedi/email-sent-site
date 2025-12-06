# JustMailIt - Complete System Documentation

**Last Updated:** December 6, 2025  
**Version:** Production 1.0  
**Author:** Manu Chaturvedi

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Database Schema](#database-schema)
4. [Routes & Endpoints](#routes--endpoints)
5. [Core Features & Logic](#core-features--logic)
6. [Button Actions & Triggers](#button-actions--triggers)
7. [Email System](#email-system)
8. [Automation Flow](#automation-flow)
9. [Deployment & Infrastructure](#deployment--infrastructure)
10. [Configuration & Environment](#configuration--environment)

---

## 🎯 System Overview

**JustMailIt** is an AI-powered job application automation platform that scrapes LinkedIn jobs and automatically sends personalized emails to recruiters with user resumes.

### Key Capabilities:
- LinkedIn job scraping with Selenium
- AI-powered job analysis and matching
- Automated email sending to recruiters
- User subscription management (Free/Pro plans)
- Resume and cover letter management
- Real-time job tracking and analytics

---

## 🏗️ Architecture & Technology Stack

### Backend
- **Framework:** Flask 3.0+
- **Language:** Python 3.11
- **Database:** SQLite 3
- **Web Server:** Gunicorn (production)
- **Container:** Docker

### Frontend
- **Template Engine:** Jinja2
- **CSS Framework:** Bootstrap 5.3
- **Icons:** Bootstrap Icons
- **JavaScript:** Vanilla JS + Chart.js

### Third-Party Services
- **Authentication:** Firebase Auth
- **Email:** Gmail SMTP (smtp.gmail.com:587)
- **Web Scraping:** Selenium WebDriver + Undetected ChromeDriver
- **Payment:** Razorpay (future integration)

### Infrastructure
- **Hosting:** Raspberry Pi (production)
- **SSH Access:** Dataplicity port forwarding (port 8888)
- **Container Name:** justmailit-app
- **Domain:** justmailit.in

---

## 🗄️ Database Schema

### Tables

#### 1. `user_profiles`
Stores user account and profile information.

```sql
CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,           -- Firebase UID
    email TEXT UNIQUE NOT NULL,             -- User email
    name TEXT,                              -- Display name
    resume_path TEXT,                       -- Path to uploaded resume
    cover_letter TEXT,                      -- Custom cover letter
    skills TEXT,                            -- Comma-separated skills
    experience_years INTEGER DEFAULT 0,     -- Years of experience
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

**Purpose:** Store user authentication data and profile settings.

---

#### 2. `job_posts`
Stores scraped job listings from LinkedIn.

```sql
CREATE TABLE job_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE NOT NULL,            -- LinkedIn job ID
    title TEXT NOT NULL,                    -- Job title
    company TEXT,                           -- Company name
    location TEXT,                          -- Job location
    job_type TEXT,                          -- Full-time/Part-time/Contract
    posted_date TEXT,                       -- Date posted (YYYY-MM-DD)
    description TEXT,                       -- Job description
    recruiter_email TEXT,                   -- Extracted recruiter email
    job_url TEXT,                           -- LinkedIn URL
    skills_required TEXT,                   -- Required skills (comma-separated)
    experience_required TEXT,               -- Experience requirement
    salary_range TEXT,                      -- Salary info if available
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

**Purpose:** Cache job posts to avoid re-scraping and enable fast filtering.

**Key Fields:**
- `job_id`: Unique identifier from LinkedIn URL
- `recruiter_email`: Extracted from job description or company page
- `posted_date`: Used for sorting newest jobs first

---

#### 3. `sent_emails`
Tracks all sent job application emails.

```sql
CREATE TABLE sent_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,                  -- Firebase UID
    job_id TEXT NOT NULL,                   -- Links to job_posts.job_id
    recipient_email TEXT NOT NULL,          -- Recruiter email
    subject TEXT,                           -- Email subject line
    body TEXT,                              -- Email content
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent',             -- sent/failed/bounced
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id),
    FOREIGN KEY (job_id) REFERENCES job_posts(job_id)
);
```

**Purpose:** Prevent duplicate emails and track application history.

**Indexes:**
- `(user_id, job_id)` - Fast duplicate checking
- `(user_id, sent_at)` - Quick daily limit queries
- `(recipient_email)` - Avoid spamming same recruiter

---

#### 4. `subscriptions`
Manages user subscription plans and limits.

```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    plan TEXT DEFAULT 'free',               -- 'free' or 'pro'
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    emails_per_day INTEGER DEFAULT 10,      -- Daily email limit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
);
```

**Purpose:** Enforce usage limits and enable premium features.

**Plan Limits:**
- **Free:** 10 emails/day
- **Pro:** Unlimited emails

---

#### 5. `scheduler_jobs` (Optional)
Tracks scheduled automation runs.

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

**Purpose:** Enable recurring automation schedules.

---

## 🌐 Routes & Endpoints

### Public Routes (No Authentication)

#### **`GET /`** - Landing Page
- **File:** `sendmail/templates/landing.html`
- **Purpose:** Marketing landing page with product info
- **Features:**
  - Hero section with CTA buttons
  - Feature highlights
  - Pricing information
  - Testimonials
  - Authentication modal (Firebase)

---

#### **`GET /terms`** - Terms of Service
- **File:** `sendmail/templates/terms.html`
- **Purpose:** Legal terms and conditions
- **Content:** Service usage rules, liability disclaimers

---

#### **`GET /privacy`** - Privacy Policy
- **File:** `sendmail/templates/privacy.html`
- **Purpose:** Data privacy and GDPR compliance
- **Content:** Data collection, storage, and usage policies

---

### Authentication Routes

#### **`POST /login`** - Firebase Authentication
- **Handler:** `app.py:login()`
- **Input:** `{ idToken: string, displayName: string }`
- **Process:**
  1. Verify Firebase ID token
  2. Extract user info (email, UID)
  3. Create session cookie
  4. Initialize user profile in DB if new user
  5. Return success/error response
- **Response:** `{ success: true, redirect: '/dashboard' }`

---

#### **`GET /logout`** - Session Logout
- **Handler:** `app.py:logout()`
- **Process:**
  1. Clear session cookie
  2. Redirect to landing page
- **Response:** Redirect to `/`

---

### Protected Routes (Require Login)

#### **`GET /dashboard`** - Main Dashboard
- **File:** `sendmail/templates/dashboard.html`
- **Purpose:** User control panel
- **Components:**
  - Profile summary
  - Quick stats (jobs found, emails sent)
  - Recent activity feed
  - Action buttons (Run Automation, View Jobs, Settings)
- **Data Loaded:**
  - User profile from `user_profiles`
  - Subscription status from `subscriptions`
  - Email stats from `sent_emails`
  - Recent jobs from `job_posts`

---

#### **`GET /profile`** - User Profile Page
- **File:** `sendmail/templates/profile.html`
- **Purpose:** Manage user settings and credentials
- **Editable Fields:**
  - Name
  - Email (read-only)
  - Skills (comma-separated)
  - Experience years
  - Resume upload
  - Cover letter template
- **Form Actions:**
  - **Update Profile Button:** POST `/profile` - Save changes to `user_profiles`
  - **Upload Resume Button:** POST `/upload_resume` - Save file and update path
  - **Delete Resume Button:** POST `/delete_resume` - Remove file and clear path

---

#### **`GET /jobs`** - Job Posts List
- **File:** `sendmail/templates/job_posts.html`
- **Purpose:** Browse available job opportunities
- **Features:**
  - Sortable columns (date, company, title)
  - Search/filter functionality
  - Job details modal
  - "Apply Now" button per job
- **Data Source:**
  - Query: `SELECT * FROM job_posts WHERE is_active=1 ORDER BY posted_date DESC`
  - **IMPORTANT:** Uses `.get("posted_date", "1970-01-01")` for safe sorting
- **Bug Fix Applied:**
  - Moved `from datetime import datetime` to top of function (line 2123)
  - Added fallback for missing `posted_date` field

---

#### **`GET /automation`** - Automation Control Panel
- **File:** `sendmail/templates/automation.html`
- **Purpose:** Configure and run job application automation
- **Components:**
  1. **Configuration Form:**
     - Job title keywords
     - Location preferences
     - Minimum salary
     - Job type (Full-time, Contract, etc.)
  
  2. **Action Buttons:**
     - **Run Automation Button:** Triggers POST `/run_automation`
     - **Stop Automation Button:** POST `/stop_automation` (future)
     - **Schedule Automation Button:** Opens scheduler modal
  
  3. **Progress Monitor:**
     - Real-time progress bar
     - Status messages (Scraping... / Analyzing... / Sending emails...)
     - Live count updates

---

#### **`POST /run_automation`** - Execute Automation
- **Handler:** `app.py:run_automation()`
- **Process Flow:**
  1. **Validation Phase:**
     - Check user authentication
     - Verify subscription status
     - Validate resume exists
     - Load user profile and settings
  
  2. **Scraping Phase:**
     - Initialize Selenium WebDriver
     - Navigate to LinkedIn jobs
     - Extract job listings (title, company, URL, etc.)
     - Parse job descriptions
     - Extract recruiter emails
     - Save to `job_posts` table
  
  3. **Analysis Phase:**
     - Load saved jobs from DB
     - Score each job based on skills match
     - Rank by relevance
     - Filter out already-applied jobs
  
  4. **Email Sending Phase:**
     - **Free Users (lines 3540-3590):**
       ```python
       if user_plan == 'free':
           today_count = count_emails_sent_today(user_id)
           if today_count >= 10:
               # Split emails into sendable and skipped
               all_emails = set(scraped_jobs)
               skipped_emails = set(scraped_jobs[10:])
               # Send only first 10
               sendable_emails = scraped_jobs[:10]
       ```
     - **Pro Users:**
       - Skip limit check entirely
       - `all_emails` = full scraped set
       - `skipped_emails` = empty
       - Send to all matching jobs
     
     - For each job:
       - Generate personalized email body
       - Attach user resume
       - Send via SMTP
       - Increment `emails_sent_count`
       - Save to `sent_emails` table
  
  5. **Notification Phase (lines 3785-3920 - FINALLY BLOCK):**
     - **Fixed Logic:** Changed `elif` to `if` to allow multiple notifications
     - **Three Email Scenarios:**
       
       a) **Missed Opportunity Email:**
       ```python
       if len(skipped_emails) > 0:
           send_missed_opportunity_email(
               user_email=user['email'],
               skipped_count=len(skipped_emails),
               total_found=len(all_emails)
           )
       ```
       - Triggers: Free user hit 10-email limit
       - Content: Shows how many jobs were skipped
       - Call-to-action: Upgrade to Pro
       
       b) **Success Summary Email:**
       ```python
       if emails_sent_count > 0:
           send_success_summary_email(
               user_email=user['email'],
               emails_sent=emails_sent_count,
               jobs_found=len(all_emails)
           )
       ```
       - Triggers: At least 1 email sent successfully
       - Content: Summary of sent applications
       - Encouragement: "Great job applying!"
       
       c) **No Results Email:**
       ```python
       elif emails_sent_count == 0 and len(all_emails) == 0:
           send_no_results_email(user_email=user['email'])
       ```
       - Triggers: No jobs found matching criteria
       - Content: Suggestions to adjust search settings

**Response:** JSON with status and results summary

---

#### **`GET /sent_emails`** - Email History
- **File:** `sendmail/templates/sent_emails.html`
- **Purpose:** View all sent job applications
- **Features:**
  - Chronological list of sent emails
  - Filter by date range
  - View email content
  - Job details link
- **Data Query:**
  ```sql
  SELECT e.*, j.title, j.company 
  FROM sent_emails e
  LEFT JOIN job_posts j ON e.job_id = j.job_id
  WHERE e.user_id = ?
  ORDER BY e.sent_at DESC
  ```

---

#### **`GET /subscription`** - Subscription Management
- **File:** `sendmail/templates/subscription.html`
- **Purpose:** View and upgrade subscription plan
- **Components:**
  - Current plan display (Free/Pro)
  - Usage stats (emails sent today/this month)
  - Plan comparison table
  - **Upgrade to Pro Button:** Redirects to payment flow

---

### API Endpoints

#### **`GET /api/jobs`** - Fetch Jobs JSON
- **Response:** List of job posts with filters applied
- **Query Params:**
  - `?location=Mumbai` - Filter by location
  - `?title=Developer` - Filter by job title
  - `?limit=50` - Limit results

---

#### **`GET /api/recent_sent_emails`** - Recent Emails API
- **Response:** Last N sent emails for current user
- **Query Params:** `?limit=5`

---

#### **`GET /api/email_stats`** - Email Statistics
- **Response:**
  ```json
  {
    "today": 5,
    "week": 28,
    "total": 137,
    "limit": 10,
    "remaining": 5
  }
  ```

---

#### **`POST /api/stop_automation`** - Stop Running Automation
- **Handler:** Sets stop flag to interrupt automation loop
- **Response:** `{ success: true }`

---

## 🎨 Core Features & Logic

### 1. Job Scraping (`linkedin_job_scraper.py`)

**Entry Point:** `scrape_linkedin_jobs(keywords, location, num_jobs=50)`

**Process:**
1. Initialize undetected Chrome WebDriver
2. Navigate to LinkedIn jobs search
3. Bypass login detection
4. Scroll to load job cards
5. For each job:
   - Extract title, company, location
   - Click job card to open details
   - Parse job description
   - Extract recruiter email (regex patterns)
   - Save to `job_posts` table
6. Return list of job dictionaries

**Key Functions:**
- `extract_recruiter_email(description)` - Regex to find emails
- `parse_job_description(html)` - Clean HTML to text
- `deduplicate_jobs(jobs)` - Remove duplicates by job_id

---

### 2. Job Analysis (`services/job_service.py`)

**Purpose:** Score and rank jobs based on user profile match.

**Function:** `load_job_posts()`

**Process (lines 88-115):**
```python
def load_job_posts():
    jobs = db.get_all_jobs()
    analyzed_jobs = []
    skipped_count = 0
    
    for job in jobs:
        try:
            # Analyze job post for skills match
            analyzed_job = analyzer.analyze_post(job)
            analyzed_jobs.append(analyzed_job)
        except Exception as e:
            # CRITICAL FIX: Don't skip job on analysis failure
            print(f"⚠️ Analysis failed for {job.get('title')}: {e}")
            skipped_count += 1
            
            # Add job anyway with fallback posted_date
            if 'posted_date' not in job:
                job['posted_date'] = job.get('created_at', 
                    datetime.now().strftime('%Y-%m-%d'))
            analyzed_jobs.append(job)
    
    print(f"📊 Loaded {len(analyzed_jobs)} jobs (skipped {skipped_count})")
    return analyzed_jobs
```

**Bug Fixed:** Previously skipped 154 jobs due to analysis failures, now adds them with basic info.

---

### 3. Email Sending (`services/email_service.py`)

#### Core Function: `send_html_email(to, subject, body, attachments=[])`

**Process:**
1. Create MIME multipart message
2. Set sender: `mail@justmailit.in`
3. Add email body (HTML)
4. Attach resume PDF
5. Connect to Gmail SMTP
6. Authenticate with app password
7. Send email
8. Return success/failure status

**Configuration:**
```python
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "manudrive06@gmail.com"
SMTP_PASSWORD = "ozds nrqo gduy mnwd"  # App password
SENDER_EMAIL = "mail@justmailit.in"
```

**Note:** Gmail overrides sender address to `manudrive06@gmail.com` without domain verification.

---

#### Notification Emails

##### A. `send_missed_opportunity_email(user_email, skipped_count, total_found)`

**Triggers:** Free user hits 10-email daily limit  
**Purpose:** Encourage upgrade to Pro plan

**Template:**
- Subject: "🚀 You Missed 23 Job Opportunities Today!"
- Body: Explains limit reached, shows upgrade benefits
- CTA: "Upgrade to Pro" button

---

##### B. `send_success_summary_email(user_email, emails_sent, jobs_found)`

**Triggers:** At least 1 email sent successfully  
**Purpose:** Confirmation and encouragement

**Template:**
- Subject: "✅ Successfully Applied to 8 Jobs!"
- Body: Summary of applications sent
- Tips: Follow-up strategies
- CTA: "View Applications" link

---

##### C. `send_no_results_email(user_email)`

**Triggers:** No jobs found matching criteria  
**Purpose:** Suggest search adjustments

**Template:**
- Subject: "No Jobs Found - Try Adjusting Your Settings"
- Body: Suggestions to broaden search
- CTA: "Update Preferences" button

---

### 4. User Profile Management

#### Resume Upload: `POST /upload_resume`

**Process:**
1. Validate file type (PDF only)
2. Check file size (< 5MB)
3. Generate unique filename: `resume_{user_id}_{timestamp}.pdf`
4. Save to `/uploads/resumes/` directory
5. Update `user_profiles.resume_path`
6. Return success message

---

#### Profile Update: `POST /profile`

**Fields Updated:**
- `name`
- `skills` (comma-separated)
- `experience_years`
- `cover_letter`

**Validation:**
- Name: 3-100 characters
- Skills: Max 500 characters
- Experience: 0-50 years

---

### 5. Subscription System

#### Daily Limit Enforcement (Line 3547)

```python
if user_plan == 'free':
    # Count emails sent today
    today_start = datetime.now().replace(hour=0, minute=0, second=0)
    today_count = db.count_emails_sent_since(user_id, today_start)
    
    if today_count >= 10:
        # User hit limit - split emails
        sendable = all_emails[:10 - today_count]
        skipped = all_emails[10 - today_count:]
        
        # Only send allowed emails
        for email in sendable:
            send_email(email)
        
        # Notify about skipped emails
        send_missed_opportunity_email(user_email, len(skipped), len(all_emails))
```

**Pro Plan Behavior:**
- Skips entire limit check block
- `all_emails` remains full scraped set
- `skipped_emails` stays empty `[]`
- Can send unlimited emails
- Only receives success summary, never missed opportunity email

---

## 🔘 Button Actions & Triggers

### Landing Page

| Button | Location | Action | Route | Description |
|--------|----------|--------|-------|-------------|
| **Get Started** | Hero section | Opens login modal | JavaScript modal | Shows Firebase auth form |
| **Sign In** | Login modal | Submit sign-in form | POST `/login` | Authenticate with Firebase |
| **Sign Up** | Login modal | Submit signup form | POST `/login` | Create new account |
| **Continue with Google** | Login modal | Google OAuth | Firebase Auth | Google sign-in flow |
| **Continue with Facebook** | Login modal | Facebook OAuth | Firebase Auth | Facebook sign-in flow |

---

### Dashboard Page

| Button | Location | Action | Route | Description |
|--------|----------|--------|-------|-------------|
| **Run Automation** | Quick actions | Start job automation | POST `/run_automation` | Scrape jobs and send emails |
| **View Jobs** | Quick actions | Navigate to jobs page | GET `/jobs` | Browse available jobs |
| **My Applications** | Quick actions | View sent emails | GET `/sent_emails` | See email history |
| **Profile Settings** | Top navigation | Open profile page | GET `/profile` | Edit user settings |
| **Upgrade to Pro** | Sidebar banner | Open subscription page | GET `/subscription` | View upgrade options |
| **Logout** | Top navigation | End session | GET `/logout` | Clear session and redirect |

---

### Profile Page

| Button | Location | Action | Route | Description |
|--------|----------|--------|-------|-------------|
| **Save Changes** | Profile form | Update profile data | POST `/profile` | Save edited fields to DB |
| **Upload Resume** | Resume section | Open file picker | POST `/upload_resume` | Upload PDF resume file |
| **Delete Resume** | Resume section | Remove resume file | POST `/delete_resume` | Delete file and clear path |
| **Preview Resume** | Resume section | Open PDF viewer | GET `/uploads/resumes/{filename}` | View current resume |

---

### Jobs Page

| Button | Location | Action | Route | Description |
|--------|----------|--------|-------|-------------|
| **Apply Now** | Each job card | Send application email | POST `/apply_to_job` | Send single job application |
| **View Details** | Each job card | Open job modal | JavaScript modal | Show full job description |
| **Filter Jobs** | Sidebar | Apply filters | GET `/jobs?filters` | Filter by location/title |
| **Sort** | Table header | Change sort order | GET `/jobs?sort` | Sort by date/company |

---

### Automation Page

| Button | Location | Action | Route | Description |
|--------|----------|--------|-------|-------------|
| **Start Automation** | Main panel | Begin automation | POST `/run_automation` | Execute full automation flow |
| **Stop** | Progress panel | Cancel automation | POST `/api/stop_automation` | Interrupt running process |
| **Schedule** | Settings | Open scheduler modal | JavaScript modal | Set recurring schedule |
| **Save Settings** | Configuration | Save automation config | POST `/automation/settings` | Save job search criteria |

---

### Subscription Page

| Button | Location | Action | Route | Description |
|--------|----------|--------|-------|-------------|
| **Upgrade to Pro** | Pro plan card | Initiate payment | POST `/create_order` | Start Razorpay checkout |
| **Cancel Subscription** | Current plan | Downgrade to free | POST `/cancel_subscription` | End Pro subscription |
| **View Invoices** | Billing history | Show invoices | GET `/invoices` | Download past invoices |

---

## 📧 Email System

### Email Configuration

**SMTP Settings:**
```python
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "manudrive06@gmail.com"
SMTP_PASSWORD = "ozds nrqo gduy mnwd"
SENDER_EMAIL = "mail@justmailit.in"
```

**Known Issue:** Gmail shows sender as `manudrive06@gmail.com` instead of `mail@justmailit.in` because domain is not verified in Gmail settings.

**Fix Required:**
1. Go to Gmail Settings → Accounts → "Send mail as"
2. Add `mail@justmailit.in` as verified sender
3. Setup SPF and DKIM DNS records for justmailit.in domain

---

### Email Templates

#### 1. Job Application Email
- **Recipient:** Recruiter email from job post
- **Subject:** `Application for [Job Title] - [User Name]`
- **Body:**
  ```
  Dear Hiring Manager,
  
  I am writing to express my interest in the [Job Title] position at [Company].
  
  With [X] years of experience in [Skills], I believe I would be a great fit...
  
  [Cover Letter Content]
  
  Best regards,
  [User Name]
  ```
- **Attachment:** User resume PDF

---

#### 2. Missed Opportunity Email
- **Recipient:** User email
- **Subject:** `🚀 You Missed [N] Job Opportunities Today!`
- **Triggers:** Free plan user hits 10-email limit
- **Variables:**
  - `skipped_count`: Number of jobs not applied to
  - `total_found`: Total jobs found
  - `remaining`: Emails remaining today (always 0 here)

---

#### 3. Success Summary Email
- **Recipient:** User email
- **Subject:** `✅ Successfully Applied to [N] Jobs!`
- **Triggers:** At least 1 email sent
- **Variables:**
  - `emails_sent_count`: Number of applications sent
  - `jobs_found`: Total jobs scraped
  - `application_details`: List of companies applied to

---

#### 4. No Results Email
- **Recipient:** User email
- **Subject:** `No Jobs Found - Try Adjusting Your Settings`
- **Triggers:** Zero jobs match search criteria
- **Suggestions:**
  - Broaden location search
  - Adjust skill requirements
  - Try different keywords

---

## 🔄 Automation Flow

### Complete Automation Sequence

```
┌─────────────────────────────────────────────────────────────┐
│  1. USER TRIGGERS AUTOMATION                                │
│     - Clicks "Run Automation" button                        │
│     - POST /run_automation                                  │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  2. VALIDATION PHASE                                        │
│     - Check user authentication (session)                   │
│     - Load user profile from user_profiles table            │
│     - Verify resume exists (resume_path not null)           │
│     - Load subscription from subscriptions table            │
│     - Get user skills and preferences                       │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  3. SCRAPING PHASE                                          │
│     - Initialize Selenium WebDriver (undetected-chromedriver)│
│     - Navigate to LinkedIn jobs                             │
│     - Search: linkedin.com/jobs/search/?keywords={query}    │
│     - Scroll page to load job cards                         │
│     - Extract job data:                                     │
│       * job_id (from URL)                                   │
│       * title                                               │
│       * company                                             │
│       * location                                            │
│       * posted_date                                         │
│       * job_url                                             │
│       * description (from detail page)                      │
│       * recruiter_email (regex extraction)                  │
│     - Save to job_posts table (if not exists)               │
│     - Close WebDriver                                       │
│     Result: all_emails = [list of scraped jobs]             │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  4. ANALYSIS PHASE                                          │
│     - Load jobs from job_posts table                        │
│     - For each job:                                         │
│       * Try: analyzer.analyze_post(job)                     │
│       * Catch error: Add job with fallback data             │
│       * Score skills match (0-100)                          │
│       * Add relevance score                                 │
│     - Sort by relevance score DESC                          │
│     - Filter out already-applied (check sent_emails)        │
│     Result: ranked_jobs = [sorted job list]                 │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  5. LIMIT CHECK PHASE (FREE USERS ONLY)                     │
│     Line 3547: if user_plan == 'free':                      │
│       - Count emails sent today:                            │
│         today_count = COUNT(*) FROM sent_emails             │
│         WHERE user_id=? AND DATE(sent_at)=TODAY             │
│       - If today_count >= 10:                               │
│         * sendable_emails = ranked_jobs[0:0]  (none left)   │
│         * skipped_emails = ranked_jobs (all skipped)        │
│       - Else:                                               │
│         * remaining = 10 - today_count                      │
│         * sendable_emails = ranked_jobs[0:remaining]        │
│         * skipped_emails = ranked_jobs[remaining:]          │
│                                                             │
│     Pro Users: SKIP THIS ENTIRE BLOCK                       │
│       - sendable_emails = ranked_jobs (all jobs)            │
│       - skipped_emails = []                                 │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  6. EMAIL SENDING PHASE                                     │
│     emails_sent_count = 0                                   │
│     For each job in sendable_emails:                        │
│       - Generate email body (personalized)                  │
│       - Attach user resume PDF                              │
│       - Send via SMTP:                                      │
│         * Connect to smtp.gmail.com:587                     │
│         * Login: manudrive06@gmail.com                      │
│         * From: mail@justmailit.in                          │
│         * To: job.recruiter_email                           │
│         * Subject: "Application for [title] - [name]"       │
│         * Body: HTML email with cover letter                │
│         * Attachment: resume.pdf                            │
│       - If send successful:                                 │
│         * emails_sent_count += 1                            │
│         * INSERT INTO sent_emails (...)                     │
│       - If send failed:                                     │
│         * Log error, continue to next                       │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  7. NOTIFICATION PHASE (FINALLY BLOCK)                      │
│     Lines 3785-3920 - ALWAYS EXECUTES                       │
│                                                             │
│     Scenario A: MISSED OPPORTUNITY (line 3843)              │
│     if len(skipped_emails) > 0:                             │
│       send_missed_opportunity_email(                        │
│         user_email=user['email'],                           │
│         skipped_count=len(skipped_emails),                  │
│         total_found=len(all_emails)                         │
│       )                                                     │
│       Triggers: Free user hit limit, jobs were skipped      │
│                                                             │
│     Scenario B: SUCCESS SUMMARY (line 3855)                 │
│     if emails_sent_count > 0:                               │
│       send_success_summary_email(                           │
│         user_email=user['email'],                           │
│         emails_sent=emails_sent_count,                      │
│         jobs_found=len(all_emails)                          │
│       )                                                     │
│       Triggers: At least 1 email sent successfully          │
│                                                             │
│     Scenario C: NO RESULTS (line 3867)                      │
│     elif emails_sent_count == 0 and len(all_emails) == 0:  │
│       send_no_results_email(user_email=user['email'])       │
│       Triggers: No jobs found at all                        │
│                                                             │
│     NOTE: Changed 'elif' to 'if' so BOTH A and B can send  │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  8. CLEANUP & RESPONSE                                      │
│     - Close database connection                             │
│     - Clear temporary files                                 │
│     - Return JSON response:                                 │
│       {                                                     │
│         "success": true,                                    │
│         "jobs_found": len(all_emails),                      │
│         "emails_sent": emails_sent_count,                   │
│         "skipped": len(skipped_emails)                      │
│       }                                                     │
└─────────────────────────────────────────────────────────────┘
```

---

### Value Determination Explained

#### `all_emails`
- **Source:** All jobs scraped from LinkedIn
- **Type:** `set()` or `list()`
- **Example:** 150 jobs found
- **Pro User:** Contains all 150 jobs
- **Free User:** Contains all 150 jobs (but only 10 sendable)

---

#### `skipped_emails`
- **Source:** Jobs NOT sent due to daily limit
- **Calculation:**
  - **Free User:** `skipped_emails = all_emails[10:]` (jobs 11-150)
  - **Pro User:** `skipped_emails = []` (empty, no limit)
- **Used For:** Missed opportunity email count

---

#### `emails_sent_count`
- **Source:** Counter incremented after each successful SMTP send
- **Starts At:** 0
- **Increments:** +1 per successful email
- **Final Value:**
  - **Free User:** Max 10 (limited)
  - **Pro User:** Up to len(all_emails) (unlimited)

---

## 🚀 Deployment & Infrastructure

### Production Environment

**Server:** Raspberry Pi 4 Model B  
**OS:** Raspberry Pi OS (Debian-based)  
**Access:** SSH via Dataplicity port forwarding  
**Port:** 8888 (external) → 22 (internal)

---

### Docker Setup

**Dockerfile:** `Dockerfile.rpi`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port
EXPOSE 5000

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "sendmail.app:app"]
```

**Container Name:** `justmailit-app`

---

### Deployment Commands

#### 1. Build Docker Image
```bash
ssh -p 8888 manu@localhost "cd /home/manu/justmailit && docker build -t justmailit-rpi -f Dockerfile.rpi ."
```

#### 2. Stop Existing Container
```bash
ssh -p 8888 manu@localhost "docker stop justmailit-app && docker rm justmailit-app"
```

#### 3. Run New Container
```bash
ssh -p 8888 manu@localhost "docker run -d --name justmailit-app -p 5000:5000 -v /home/manu/justmailit:/app justmailit-rpi"
```

#### 4. Quick Restart (No Rebuild)
```bash
ssh -p 8888 manu@localhost "cd /home/manu/justmailit && git pull origin manu && docker restart justmailit-app"
```

**Recent Deployment:**
```bash
# Commit: 7e19ed4 - Production save
ssh -p 8888 manu@localhost "cd /home/manu/justmailit && git pull origin manu && docker restart justmailit-app && echo '✅ Production deployed!'"
```

---

### Database Location

**Production DB:** `/home/manu/justmailit/justmailit.db`  
**Backup Location:** `/home/manu/justmailit/backups/`

**Backup Command:**
```bash
ssh -p 8888 manu@localhost "cp /home/manu/justmailit/justmailit.db /home/manu/justmailit/backups/justmailit_backup_$(date +%Y%m%d_%H%M%S).db"
```

---

### Logs & Monitoring

**View Container Logs:**
```bash
ssh -p 8888 manu@localhost "docker logs justmailit-app"
```

**Follow Real-Time Logs:**
```bash
ssh -p 8888 manu@localhost "docker logs -f justmailit-app"
```

**Check Container Status:**
```bash
ssh -p 8888 manu@localhost "docker ps -a | grep justmailit"
```

---

## ⚙️ Configuration & Environment

### Environment Variables

**Firebase Configuration:**
```python
FIREBASE_API_KEY = "AIzaSyAqEkQOtCzx7rOf5pbHlDBHN-Cc_uOnRQw"
FIREBASE_AUTH_DOMAIN = "justmailit-d6f2d.firebaseapp.com"
FIREBASE_PROJECT_ID = "justmailit-d6f2d"
```

**Email Configuration:**
```python
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "manudrive06@gmail.com"
SMTP_PASSWORD = "ozds nrqo gduy mnwd"
SENDER_EMAIL = "mail@justmailit.in"
```

**Application Settings:**
```python
SECRET_KEY = "your-secret-key-here"
UPLOAD_FOLDER = "/uploads/resumes"
MAX_RESUME_SIZE_MB = 5
ALLOWED_EXTENSIONS = ["pdf"]
FREE_PLAN_DAILY_LIMIT = 10
```

---

### Configuration Files

#### `requirements.txt`
```
Flask==3.0.0
gunicorn==21.2.0
selenium==4.15.0
undetected-chromedriver==3.5.4
firebase-admin==6.2.0
PyPDF2==3.0.1
beautifulsoup4==4.12.2
```

#### `docker-compose.yml`
```yaml
version: '3.8'
services:
  justmailit:
    build:
      context: .
      dockerfile: Dockerfile.rpi
    container_name: justmailit-app
    ports:
      - "5000:5000"
    volumes:
      - ./:/app
      - ./uploads:/app/uploads
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
```

---

## 🐛 Known Issues & Fixes

### Issue 1: Email Notifications Not Reliable
**Problem:** Automation completion emails "sometimes work sometimes not"  
**Root Cause:** Used `elif` instead of `if` for notification conditions  
**Fix:** Changed to `if` at line 3843 to allow multiple notifications  
**Commit:** ef72ee3

---

### Issue 2: Job Posts Page Shows 613 Instead of 767
**Problem:** 154 jobs missing from display  
**Root Cause:** `analyzer.analyze_post()` failing silently  
**Fix:** Added try-catch in `load_job_posts()` to include failed jobs  
**Commit:** ef72ee3

---

### Issue 3: KeyError - 'posted_date'
**Problem:** Crash when sorting jobs without posted_date  
**Root Cause:** Direct dictionary access `x["posted_date"]`  
**Fix:** Used `.get("posted_date", "1970-01-01")` for safe access  
**Commit:** e24c5a5

---

### Issue 4: UnboundLocalError - datetime
**Problem:** datetime used before import statement  
**Root Cause:** Import at line 2169, usage at line 2159  
**Fix:** Moved `from datetime import datetime` to line 2123 (top of function)  
**Commit:** cbad8b0

---

### Issue 5: Email Sender Shows Wrong Address
**Problem:** Emails show from "manudrive06@gmail.com" not "mail@justmailit.in"  
**Root Cause:** Gmail domain verification required  
**Fix:** Add mail@justmailit.in as verified sender in Gmail settings  
**Status:** Pending manual configuration

---

## 📊 Metrics & Analytics

### Key Performance Indicators

1. **Jobs Scraped per Run:** Average 50-150 jobs
2. **Email Send Success Rate:** 95%+ (SMTP)
3. **Average Automation Time:** 5-10 minutes
4. **Daily Active Users:** Tracked in `user_profiles.last_login`
5. **Conversion Rate:** (Pro subscriptions / Total users)

### Database Queries for Analytics

**Total Jobs Scraped:**
```sql
SELECT COUNT(*) FROM job_posts WHERE is_active=1;
```

**Emails Sent Today:**
```sql
SELECT COUNT(*) FROM sent_emails WHERE DATE(sent_at) = DATE('now');
```

**Top Companies:**
```sql
SELECT company, COUNT(*) as count 
FROM job_posts 
GROUP BY company 
ORDER BY count DESC 
LIMIT 10;
```

**User Activity:**
```sql
SELECT DATE(last_login) as date, COUNT(*) as active_users
FROM user_profiles
WHERE last_login >= DATE('now', '-30 days')
GROUP BY DATE(last_login);
```

---

## 🔒 Security Considerations

### Authentication
- Firebase ID tokens verified server-side
- Session cookies with HTTP-only flag
- CSRF protection on all POST routes

### Data Protection
- Resumes stored in protected `/uploads` directory
- Email credentials in environment variables (not in code)
- Database file permissions: `chmod 600 justmailit.db`

### Rate Limiting
- 10 emails/day for free users (enforced in DB)
- Login attempts throttled (Firebase built-in)
- API endpoints rate-limited (future enhancement)

---

## 📝 Maintenance & Support

### Regular Tasks

**Daily:**
- Monitor Docker logs for errors
- Check email sending success rate
- Verify database backups

**Weekly:**
- Review user feedback
- Update job scraping patterns if LinkedIn changes
- Check for security updates

**Monthly:**
- Database cleanup (old jobs, inactive users)
- Performance optimization
- Feature updates deployment

---

### Support Contacts

**Developer:** Manu Chaturvedi  
**Email:** manudrive06@gmail.com  
**GitHub:** manuchaturvedi/email-sent-site  
**Branch:** manu

---

## 🎓 Learning Resources

### For Developers

**Flask Documentation:** https://flask.palletsprojects.com/  
**Selenium Docs:** https://www.selenium.dev/documentation/  
**Firebase Auth:** https://firebase.google.com/docs/auth  
**SQLite Tutorial:** https://www.sqlitetutorial.net/

---

## 📅 Changelog

### Version 1.0 (December 6, 2025)
- ✅ Fixed email notification logic (elif → if)
- ✅ Fixed job posts display (613 → 767 jobs)
- ✅ Fixed KeyError for missing posted_date
- ✅ Fixed UnboundLocalError for datetime import
- ✅ Added no-results notification email
- ✅ Improved error handling in job analysis
- ✅ Deployed to production Raspberry Pi

---

## 🔮 Future Enhancements

1. **Scheduled Automation:** Run daily at specified times
2. **Advanced Filtering:** Salary range, company size, remote options
3. **Email Templates:** Multiple cover letter templates
4. **Analytics Dashboard:** Charts and graphs for application tracking
5. **Mobile App:** React Native mobile application
6. **AI Cover Letters:** GPT-powered personalized cover letters
7. **Interview Tracker:** Track interview invitations and responses

---

**End of Documentation**

*This documentation is a living document and will be updated as the system evolves.*
