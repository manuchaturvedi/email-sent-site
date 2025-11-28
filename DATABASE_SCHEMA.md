# Database Schema Documentation

## Overview
The application uses SQLite database (`justmailit.db`) with the following tables.

---

## Table: `user_profiles`

Stores user profile information including resume and email templates.

### Schema
```sql
CREATE TABLE IF NOT EXISTS user_profiles (
    email TEXT PRIMARY KEY,
    resume_data TEXT,           -- Base64 encoded resume file
    resume_filename TEXT,       -- Original filename of resume
    email_content TEXT,         -- Email body template
    email_subject TEXT,         -- Email subject line
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Field Mapping (Critical!)
- **Database**: Uses `resume_data`, `resume_filename` (snake_case with underscores)
- **Code**: Access via `profile_data.get('resume_data')`, `profile_data.get('resume_filename')`
- **⚠️ DO NOT use**: `resumeData`, `resumeFilename` (camelCase will break!)

### Usage
```python
# Saving profile
db.save_profile(user_email, {
    'resume_data': base64_encoded_string,
    'resume_filename': 'resume.pdf',
    'email_content': 'Email body...',
    'email_subject': 'Job Application'
})

# Getting profile
profile = db.get_profile(user_email)
resume_data = profile.get('resume_data')  # ✅ Correct
resume_filename = profile.get('resume_filename')  # ✅ Correct
```

---

## Table: `sent_emails`

Stores all sent email records with job and run information.

### Schema
```sql
CREATE TABLE IF NOT EXISTS sent_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL,
    recipient_email TEXT,       -- Job recruiter email
    subject TEXT,               -- Email subject
    body TEXT,                  -- Email body content
    job_title TEXT,             -- Job position title
    company TEXT,               -- Company name
    status TEXT DEFAULT 'sent', -- Status: 'sent', 'failed', 'skipped'
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    run_id TEXT,                -- Unique ID for automation run (e.g., 'manual_20231118_143022')
    run_time TEXT,              -- Timestamp of the run
    source_url TEXT,            -- Job posting URL
    description TEXT,           -- Job description snippet
    FOREIGN KEY (user_email) REFERENCES user_profiles(email)
)
```

### Field Mapping (Critical!)
- **Database**: `recipient_email`, `sent_at`, `run_id`, `run_time`, `source_url` (snake_case)
- **Templates**: Map `recipient_email` → `email` for backward compatibility
- **⚠️ Important**: Always include `run_id` and `run_time` to group emails by automation run

### Usage
```python
# Saving sent email
db.save_sent_email(user_email, {
    'recipient_email': 'recruiter@company.com',  # ✅ Required
    'subject': 'Job Application',
    'body': 'Email content...',
    'job_title': 'Software Engineer',
    'company': 'Tech Corp',
    'status': 'sent',
    'run_id': 'manual_20231118_143022',  # ✅ Required for grouping
    'run_time': '2023-11-18T14:30:22',   # ✅ Required for sorting
    'source_url': 'https://...',
    'description': 'Job description...'
})

# Getting sent emails
emails = db.get_sent_emails(user_email, limit=100)
for email in emails:
    recipient = email.get('recipient_email')  # ✅ From database
    email['email'] = email.get('recipient_email')  # ✅ Map for template
```

### Display in Templates
```python
# In route handlers, always map fields for templates:
for email_record in emails:
    # Map recipient_email to email for template compatibility
    email_record['email'] = email_record.get('recipient_email')
    # Ensure timestamp field exists
    email_record['timestamp'] = email_record.get('sent_at', '')
    # Add cc field (user receives copy)
    email_record['cc'] = user_email
```

---

## Table: `job_posts`

Stores scraped job postings (universal/shared across all users).

### Schema
```sql
CREATE TABLE IF NOT EXISTS job_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT,            -- Original scraper user (but posts are shared)
    title TEXT,
    company TEXT,
    location TEXT,
    posted_date TEXT,
    recruiter_email TEXT,       -- Job contact email
    job_url TEXT,
    full_text TEXT,
    required_skills TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Field Mapping (Critical!)
- **Database**: `recruiter_email` (snake_case)
- **Templates**: Map `recruiter_email` → `email` for consistency
- **⚠️ Important**: Job posts are universal (not filtered by user_email)

### Processing Required in Routes
```python
# 1. Get sent emails for current user
sent_emails = set()
for email_record in db.get_sent_emails(user_email):
    if email_record.get('status') == 'sent':
        sent_emails.add(email_record['recipient_email'])

# 2. Get job posts (universal, not user-specific)
job_posts = db.get_job_posts(user_email, limit=100)

# 3. Process each post (REQUIRED!)
for post in job_posts:
    # Map recruiter_email to email
    post['email'] = post.get('recruiter_email') or post.get('email')
    
    # Mark if already sent
    post['already_sent'] = post['email'] in sent_emails if post.get('email') else False
    
    # Extract company from email if missing
    if not post.get('company') or post.get('company') in ['Company Not Found', 'Company Not Specified', '']:
        if post['email'] and '@' in post['email']:
            post['company'] = extract_company_from_email(post['email'])
```

---

## Table: `subscriptions`

Stores user subscription/plan information.

### Schema
```sql
CREATE TABLE IF NOT EXISTS subscriptions (
    user_email TEXT PRIMARY KEY,
    plan TEXT DEFAULT 'free',   -- 'free' or 'pro'
    status TEXT DEFAULT 'active',
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    FOREIGN KEY (user_email) REFERENCES user_profiles(email)
)
```

### Usage
```python
# Check subscription
subscription = db.get_subscription(user_email)
plan = subscription.get('plan', 'free')

if plan == 'free':
    # Apply 10 emails/day limit
    can_send, count, msg = check_email_limit(user_email)
else:
    # Pro users have unlimited emails
    can_send = True
```

---

## Common Errors & Solutions

### ❌ Error: "Resume uploaded but still asking"
**Cause**: Using camelCase `resumeData` instead of snake_case `resume_data`
**Solution**: Always use `resume_data` and `resume_filename` in code

### ❌ Error: "Email and CC blank in sent emails"
**Cause**: Not mapping `recipient_email` → `email` for templates
**Solution**: Always map fields in route handlers:
```python
email_record['email'] = email_record.get('recipient_email')
email_record['cc'] = user_email
```

### ❌ Error: "Company Not Found" in dashboard
**Cause**: Not running company extraction logic in route
**Solution**: Process job posts with `extract_company_from_email()` helper

### ❌ Error: "Apply button shows on already-sent jobs"
**Cause**: Not checking sent_emails and marking `already_sent` status
**Solution**: Always load sent emails and mark posts before rendering

### ❌ Error: "TypeError: '<' not supported between instances of 'str' and 'NoneType'"
**Cause**: Sorting by `run_time` when some records have `None` value
**Solution**: Use `x.get('run_time') or ''` in sort key

### ❌ Error: "Sent emails not showing in sent mail page"
**Cause**: Missing fields (`run_id`, `run_time`, `source_url`, `description`) in database
**Solution**: 
1. Add columns to table (done via ALTER TABLE in save_sent_email)
2. Always include these fields when saving emails

---

## Database Migration Strategy

The app uses **auto-migration** in `save_sent_email()`:

```python
# Check if columns exist, add if missing
cursor.execute("PRAGMA table_info(sent_emails)")
columns = [col[1] for col in cursor.fetchall()]

if 'run_id' not in columns:
    cursor.execute('ALTER TABLE sent_emails ADD COLUMN run_id TEXT')
if 'run_time' not in columns:
    cursor.execute('ALTER TABLE sent_emails ADD COLUMN run_time TEXT')
# ... etc
```

This ensures backward compatibility with existing databases.

---

## Critical Rules for Developers

### ✅ Always Do:
1. Use snake_case for database field names (`resume_data`, `recipient_email`, `run_id`)
2. Map fields for template compatibility (`recipient_email` → `email`)
3. Process job posts in routes (check already_sent, extract company)
4. Include `run_id` and `run_time` when saving sent emails
5. Handle None values in sort operations (`x.get('field') or ''`)
6. Use `extract_company_from_email()` helper for company extraction

### ❌ Never Do:
1. Use camelCase for database fields (will cause field not found errors)
2. Skip field mapping between database and templates
3. Render job posts without processing (will show wrong button states)
4. Filter job_posts by user (posts are universal/shared)
5. Sort by fields that can be None without handling it
6. Save sent emails without `run_id` (breaks grouping in sent emails page)

---

## Helper Functions Reference

### `extract_company_from_email(email)`
Extracts company name from email domain.
```python
# Example
extract_company_from_email('recruiter@techcorp.com')  # → "Techcorp"
extract_company_from_email('hr@startup.io')           # → "Startup"
```

### `check_email_limit(user_email)`
Checks if user can send email based on plan and daily limit.
```python
can_send, emails_sent, message = check_email_limit(user_email)
if not can_send:
    return jsonify({"success": False, "message": message, "limit_reached": True})
```

### `save_sent_email(record, run_id, user_email)`
Saves email record to database with auto-migration.
```python
save_sent_email({
    'recipient_email': 'job@company.com',
    'subject': 'Application',
    'status': 'sent',
    'company': 'Company Name',
    'job_title': 'Position',
    'source_url': 'https://...',
    'description': 'Job details...'
}, run_id='manual_20231118_143022', user_email='user@email.com')
```

---

## Testing Checklist

When making changes, always test:

- [ ] Dashboard shows correct company names (not "Company Not Found")
- [ ] Already-sent jobs show "Sent" button (green, disabled)
- [ ] New jobs show "Apply" button (yellow, enabled)
- [ ] Sent emails appear in "Sent Emails" page
- [ ] Sent emails grouped by run_id properly
- [ ] Email and CC fields show correctly in sent emails
- [ ] Resume uploads work (no "please upload resume" error)
- [ ] Free users hit 10/day limit correctly
- [ ] Pro users can send unlimited emails
- [ ] Notifications use toast (not alert popups)

---

Last Updated: November 18, 2025
