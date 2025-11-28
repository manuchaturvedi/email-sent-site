# MIGRATION GUIDE: Firebase Firestore → SQLite

## What's Changed
- **Authentication**: Still using Firebase (no changes needed)
- **Data Storage**: Moved from Firestore to SQLite
- **Location**: Database file `justmailit.db` in root directory

## Benefits
✅ No quota limits
✅ Faster performance (local)
✅ No internet dependency
✅ Free forever
✅ Firebase only for authentication

## Files Created
1. `sendmail/database.py` - SQLite database wrapper

## Files to Update
1. `sendmail/app.py` - Replace all Firestore calls with SQLite

## Migration Steps

### 1. Update requirements.txt
No changes needed - SQLite is built into Python

### 2. Update app.py imports (DONE)
```python
from database import Database
db = Database()
```

### 3. Replace Firestore Operations

#### User Profiles
**OLD (Firestore):**
```python
db_firestore = firestore.client()
user_ref = db_firestore.collection('user_profiles').document(email)
user_doc = user_ref.get()
```

**NEW (SQLite):**
```python
profile = db.get_profile(email)
```

#### Job Posts
**OLD:**
```python
jobs_ref = db_firestore.collection('job_posts')
jobs_ref.add({'title': 'Software Engineer', ...})
```

**NEW:**
```python
db.save_job_posts(user_email, [{'title': 'Software Engineer', ...}])
jobs = db.get_job_posts(user_email)
```

#### Sent Emails
**OLD:**
```python
emails_ref = db_firestore.collection('sent_emails')
emails_ref.add({'recipient': 'test@example.com', ...})
```

**NEW:**
```python
db.save_sent_email(user_email, {'recipient_email': 'test@example.com', ...})
emails = db.get_sent_emails(user_email)
```

#### Subscriptions
**OLD:**
```python
sub_ref = db_firestore.collection('subscriptions').document(email)
sub_doc = sub_ref.get()
```

**NEW:**
```python
subscription = db.get_subscription(user_email)
```

## Quick Reference

### All Available Methods in database.py

**User Profiles:**
- `db.create_or_update_profile(email, display_name, photo_url)`
- `db.get_profile(email)`

**Job Posts:**
- `db.save_job_posts(user_email, jobs_list)`
- `db.get_job_posts(user_email, limit=100)`
- `db.get_job_stats(user_email)` → Returns: {total_jobs, unique_companies, unique_locations}

**Sent Emails:**
- `db.save_sent_email(user_email, email_data)`
- `db.get_sent_emails(user_email, limit=100)`
- `db.get_email_stats(user_email)` → Returns: {total_emails, emails_today}

**Subscriptions:**
- `db.create_or_update_subscription(user_email, subscription_data)`
- `db.get_subscription(user_email)`

**Automation Runs:**
- `db.save_automation_run(user_email, run_data)`
- `db.get_automation_runs(user_email, limit=50)`

## Testing
1. Start fresh: Delete `justmailit.db` if exists
2. Run app: `python sendmail/app.py`
3. Login → Creates user profile
4. Run automation → Saves jobs and emails
5. Check dashboard → Data loads from SQLite

## Deployment
1. Copy `sendmail/database.py` to Pi
2. Copy updated `sendmail/app.py` to Pi
3. Restart container
4. Database file auto-created on first run

## Backup
SQLite database is just one file: `justmailit.db`
- Backup: `cp justmailit.db justmailit.db.backup`
- Restore: `cp justmailit.db.backup justmailit.db`
