"""
Job and email tracking service.
Handles job posts, sent emails, and email limits.
"""
from datetime import datetime, date
import json
from database import Database

# Initialize database
db = Database()

# File storage constants (fallback)
JOB_POSTS_FILE = 'job_posts.json'
SENT_EMAILS_FILE = 'sent_emails.json'


def is_duplicate_job_post(post, existing_posts=None, user_email=None):
    """
    Check if a job post is a duplicate based on email, title, and company.
    
    Args:
        post: Job post dict to check
        existing_posts: Optional list of existing posts to check against
        user_email: User email for database query
        
    Returns:
        bool: True if duplicate found, False otherwise
    """
    try:
        # Check SQLite database for duplicates
        if user_email:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as count FROM job_posts
                WHERE user_email = ? AND company = ? AND LOWER(TRIM(title)) = LOWER(TRIM(?))
            ''', (user_email, post.get('company', ''), post.get('title', '')))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result['count'] > 0:
                return True
        
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
        print(f"[ERROR] Error checking for duplicate job post: {str(e)}")
        # If we can't check duplicates, assume it's not a duplicate
        return False


def load_job_posts():
    """
    Load job posts from SQLite or fall back to local JSON storage.
    
    Returns:
        List of job post dicts
    """
    from job_analyzer import JobAnalyzer
    
    # Initialize job analyzer
    print("[DEBUG] Initializing JobAnalyzer...")
    analyzer = JobAnalyzer()
    print("[DEBUG] JobAnalyzer initialized")

    try:
        # Load from SQLite database
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM job_posts
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        posts = []
        skipped_count = 0
        for i, row in enumerate(rows):
            try:
                post_data = dict(row)
                post_data['skills'] = json.loads(post_data['skills']) if post_data.get('skills') else []
                # Map recruiter_email to email for template compatibility
                if 'recruiter_email' in post_data and post_data['recruiter_email']:
                    post_data['email'] = post_data['recruiter_email']
                
                # Set default posted_date if missing
                if not post_data.get('posted_date'):
                    post_data['posted_date'] = post_data.get('created_at', datetime.now().strftime('%Y-%m-%d'))
                
                analyzed = analyzer.analyze_post(post_data)
                posts.append(analyzed)
            except Exception as analyze_error:
                skipped_count += 1
                print(f"[WARN] Failed to analyze post {i+1}: {str(analyze_error)}")
                # Add post without analysis if it fails
                if post_data.get('recruiter_email'):
                    posts.append(post_data)
        
        if skipped_count > 0:
            print(f"[WARN] Skipped analyzing {skipped_count} posts due to errors")
        print(f"[OK] Loaded {len(posts)} job posts from SQLite database (total in DB: {len(rows)})")
        return posts

    except Exception as e:
        print(f"[ERROR] Error loading from SQLite: {str(e)}")
        # Continue to try local storage

    try:
        with open(JOB_POSTS_FILE, 'r') as f:
            posts = json.load(f)
            # Analyze each post from local storage
            posts = [analyzer.analyze_post(post) for post in posts]
            print(f"[OK] Loaded {len(posts)} job posts from local storage")
            return posts
    except FileNotFoundError:
        return []


def save_job_post(post, user_email=None):
    """
    Save a job post to SQLite and local storage, avoiding duplicates.
    Uses JobAnalyzer to extract proper location and other details before saving.
    
    Args:
        post: Job post dict to save
        user_email: User email who found this job
        
    Returns:
        bool: True if saved successfully, False if duplicate or error
    """
    from job_analyzer import JobAnalyzer
    
    try:
        # Analyze the post BEFORE checking for duplicates or saving
        # This ensures location and other fields are properly extracted
        analyzer = JobAnalyzer()
        post = analyzer.analyze_post(post)
        print(f"[ANALYZER] Analyzed post - Location: {post.get('location')}, Role: {post.get('role')}")
        
        # First check if this is a duplicate
        if is_duplicate_job_post(post, user_email=user_email):
            print(f"[WARN] Duplicate job post found for {post.get('company')} - {post.get('title')}")
            return False
            
        # Save to SQLite first
        if user_email:
            try:
                # Add timestamp and clean up post data
                post_to_save = post.copy()
                post_to_save.update({
                    'posted_date': post.get('posted_date') or datetime.now().strftime("%Y-%m-%d"),
                    'user_email': user_email
                })
                
                # Save to SQLite using Database class
                db.save_job_posts(user_email, [post_to_save])
                print(f"[OK] Job post saved to SQLite database")
                
                # Notify connected clients (SSE)
                try:
                    from app import send_event
                    send_event(f"NEW_JOB: {post.get('title')} | {post.get('company')} | {post.get('email')}")
                except Exception:
                    pass
                
                return True
                    
            except Exception as e:
                print(f"[ERROR] Error saving to SQLite: {str(e)}")
                # Continue to local storage as fallback
        
        # Fallback to local storage
        try:
            posts = load_job_posts()
            posts.append(post)
            with open(JOB_POSTS_FILE, 'w') as f:
                json.dump(posts, f, indent=2)
                
            # Notify connected clients
            try:
                from app import send_event
                send_event(f"NEW_JOB: {post.get('title')} | {post.get('company')} | {post.get('email')}")
            except Exception:
                pass
                
            print(f"[OK] Job post saved to local storage")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error saving to local storage: {str(e)}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error in save_job_post: {str(e)}")
        return False


def load_sent_emails(user_email=None):
    """
    Load sent emails for a specific user or all emails if no user specified.
    
    Args:
        user_email: Optional email to filter by user
    
    Returns:
        List of email records sorted by sent time
    """
    emails = []
    
    try:
        # Load from SQLite database
        if user_email:
            emails = db.get_sent_emails(user_email)
            print(f"[OK] Loaded {len(emails)} emails from SQLite database")
            return emails
        else:
            # Get all emails (no user filter)
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM sent_emails
                ORDER BY sent_at DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            emails = [dict(row) for row in rows]
            print(f"[OK] Loaded {len(emails)} emails from SQLite database")
            return emails
            
    except Exception as e:
        print(f"[ERROR] Error loading from SQLite: {str(e)}")
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
                print(f"[OK] Loaded {len(emails)} emails from local storage")
                return emails
                
        except FileNotFoundError:
            print("ℹ️ No local email records found")
            return []
            
    except Exception as e:
        print(f"[ERROR] Error in load_sent_emails: {str(e)}")
        return []


def get_user_email_stats(user_email):
    """
    Get user email statistics from SQLite.
    
    Args:
        user_email: User email to get stats for
        
    Returns:
        Tuple of (emails_list, stats_dict)
    """
    try:
        # Get email stats from SQLite
        stats_data = db.get_email_stats(user_email)
        emails = db.get_sent_emails(user_email)
        
        # Build detailed stats
        stats = {
            "sent": sum(1 for e in emails if e.get('status') == 'sent'),
            "skipped": sum(1 for e in emails if e.get('status') == 'skipped'),
            "failed": sum(1 for e in emails if e.get('status') == 'failed'),
            "duplicates": 0,
            "total": stats_data.get('total_emails', 0),
            "unique_recipients": len(set(e.get('recipient_email') for e in emails if e.get('recipient_email'))),
            "runs": len(set(e.get('run_id') for e in emails if e.get('run_id'))),
            "last_run": max((e.get('sent_at', '') for e in emails), default='')
        }
        
        # Add timestamp field and email field mapping for template compatibility
        for email in emails:
            email['timestamp'] = email.get('sent_at', '')
            # Map recipient_email to email for template
            if 'recipient_email' in email and 'email' not in email:
                email['email'] = email['recipient_email']
            # Add cc field (use user_email as cc since emails are sent with user in cc)
            if 'cc' not in email:
                email['cc'] = user_email
        
        print(f"[OK] Processed {len(emails)} email records for user {user_email}")
        return emails, stats
    except Exception as e:
        print(f"[ERROR] Error querying SQLite: {str(e)}")
        return None, {}


def prepare_email_record(record, run_id=None, user_email=None):
    """
    Prepare an email record for storage by adding necessary fields.
    
    Args:
        record: Email record dict
        run_id: Automation run ID
        user_email: User email
        
    Returns:
        dict: Prepared email record
    """
    record_to_save = record.copy()
    record_to_save.update({
        'created_at': datetime.now().isoformat(),
        'user_id': user_email,
        'user_email': user_email,  # For backwards compatibility
        'run_id': run_id,
        'status': record.get('status', 'unknown'),
        'timestamp': datetime.now().isoformat(),
        'run_time': datetime.now().isoformat(),  # Add run_time for consistency
        'subject': record.get('subject', 'No Subject'),
        'email': record.get('email', ''),
        'recipient_email': record.get('email', ''),  # For SQLite compatibility
        'action_type': record.get('status', 'unknown'),
        'error': record.get('error', None),  # Store any error messages
    })
    return record_to_save


def count_emails_sent_today(user_email):
    """
    Count how many emails a user has sent today.
    
    Args:
        user_email: User email to count for
        
    Returns:
        Tuple of (count, error_message)
    """
    try:
        print(f"[EMAIL] Counting emails for user: {user_email}")
        
        today = date.today()
        print(f"[DATE] Today's date: {today}")
        
        # Query SQLite for emails sent today
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM sent_emails
            WHERE user_email = ? 
            AND status = 'sent'
            AND DATE(sent_at) = DATE('now')
        ''', (user_email,))
        
        result = cursor.fetchone()
        conn.close()
        
        emails_today = result['count'] if result else 0
        print(f"[OK] Total emails sent today: {emails_today}")
        return emails_today, None
        
    except Exception as e:
        error_msg = f"Error counting emails: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return 0, error_msg


def check_email_limit(user_email):
    """
    Check if user has reached their daily email limit.
    
    Args:
        user_email: User email to check
        
    Returns:
        Tuple of (can_send: bool, emails_sent: int, message: str)
    """
    try:
        print(f"[DEBUG] Checking email limit for user: {user_email}")
        
        # Get user subscription from SQLite
        subscription = db.get_subscription(user_email)
        user_plan = subscription.get('plan', 'free')
        
        print(f"💳 User plan: {user_plan}")
        
        # Pro users have no limit
        if user_plan != 'free':
            print(f"[OK] Pro user - no limits")
            return True, 0, None
        
        # Count today's emails for free users
        emails_today, error = count_emails_sent_today(user_email)
        
        print(f"[COUNT] Emails sent today: {emails_today}/10")
        
        if error:
            # If we can't check reliably, allow (fail open)
            print(f"[WARN] Error counting emails: {error}, allowing send")
            return True, 0, None
        
        if emails_today >= 10:
            print(f"🔒 LIMIT REACHED! User has sent {emails_today} emails today")
            return False, emails_today, f"Daily limit reached! You've sent {emails_today}/10 emails today. Upgrade to Pro for unlimited emails."
        
        print(f"[OK] Limit check passed - can send")
        return True, emails_today, None
        
    except Exception as e:
        print(f"[ERROR] Error checking email limit: {str(e)}")
        # Fail open - allow if we can't check
        return True, 0, None


def save_sent_email(record, run_id=None, user_email=None):
    """
    Save a single sent-email record to SQLite.
    
    Args:
        record: Email record dict to save
        run_id: Automation run ID
        user_email: User email
        
    Returns:
        bool: True if saved successfully
    """
    try:
        # Add user information
        if user_email:
            record['user_email'] = user_email
        
        # Add run information
        if run_id:
            record['run_id'] = run_id
            record['run_time'] = datetime.now().isoformat()
        
        # Prepare the record
        record_to_save = prepare_email_record(record, run_id, user_email)
        
        # Save to SQLite
        db.save_sent_email(user_email, record_to_save)
        
        # Notify connected clients (SSE)
        try:
            from app import send_event
            send_event(f"NEW_EMAIL: {record_to_save.get('email')} | {record_to_save.get('status')} | {record_to_save.get('run_id')}")
        except Exception:
            pass
        
        print(f"[OK] Saved email record to SQLite: {record.get('email')}")
        return True
            
    except Exception as e:
        print(f"[ERROR] Error in save_sent_email: {str(e)}")
        
        # Fallback to local storage
        try:
            existing = load_sent_emails()
            
            # Check for duplicates in local storage
            for r in existing:
                if (r.get('email') == record.get('email') and 
                    r.get('subject') == record.get('subject') and
                    r.get('run_id') == record.get('run_id') and
                    r.get('user_email') == record.get('user_email')):
                    print(f"[SKIP] Duplicate email record - not saving")
                    return False
            
            # Add to list and save
            existing.append(prepare_email_record(record, run_id, user_email))
            with open(SENT_EMAILS_FILE, 'w') as f:
                json.dump(existing, f, indent=2)
            
            print(f"[OK] Saved email record to local storage")
            return True
            
        except Exception as local_error:
            print(f"[ERROR] Error saving to local storage: {str(local_error)}")
            return False
