import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import os

class Database:
    def __init__(self, db_path='justmailit.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # User profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                email TEXT PRIMARY KEY,
                display_name TEXT,
                photo_url TEXT,
                email_subject TEXT,
                email_content TEXT,
                search_role TEXT,
                search_time_period TEXT DEFAULT 'past-week',
                resume_data BLOB,
                resume_filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Migrate existing user_profiles table if needed
        cursor.execute("PRAGMA table_info(user_profiles)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"[DEBUG] Existing columns in user_profiles: {existing_columns}")
        
        required_columns = {
            'email_subject': 'TEXT',
            'email_content': 'TEXT',
            'search_role': 'TEXT',
            'search_time_period': "TEXT DEFAULT 'past-week'",
            'resume_data': 'BLOB',
            'resume_filename': 'TEXT',
            'linkedin_email': 'TEXT',
            'linkedin_password': 'TEXT',
            'user_name': 'TEXT',
            'user_phone': 'TEXT'
        }
        
        for col_name, col_type in required_columns.items():
            if col_name not in existing_columns:
                try:
                    print(f"[INFO] Adding column {col_name}...")
                    cursor.execute(f'ALTER TABLE user_profiles ADD COLUMN {col_name} {col_type}')
                    conn.commit()
                    print(f'[OK] Added column {col_name} to user_profiles')
                except Exception as e:
                    print(f'[WARN] Could not add column {col_name}: {e}')
            else:
                print(f"[OK] Column {col_name} already exists")
        
        # Add recruiter_email column to job_posts if missing
        cursor.execute("PRAGMA table_info(job_posts)")
        job_cols = [row[1] for row in cursor.fetchall()]
        if 'recruiter_email' not in job_cols:
            try:
                cursor.execute('ALTER TABLE job_posts ADD COLUMN recruiter_email TEXT')
                conn.commit()
                print('[OK] Added recruiter_email column to job_posts')
            except Exception as e:
                print(f'[WARN] Could not add recruiter_email column: {e}')
        
        # Add bookmarked column to job_posts if missing
        if 'bookmarked' not in job_cols:
            try:
                cursor.execute('ALTER TABLE job_posts ADD COLUMN bookmarked INTEGER DEFAULT 0')
                conn.commit()
                print('[OK] Added bookmarked column to job_posts')
            except Exception as e:
                print(f'[WARN] Could not add bookmarked column: {e}')
        
        # Job posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                title TEXT,
                company TEXT,
                location TEXT,
                job_url TEXT,
                recruiter_email TEXT,
                skills TEXT,
                full_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES user_profiles(email)
            )
        ''')
        
        # Sent emails table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                recipient_email TEXT,
                subject TEXT,
                body TEXT,
                job_title TEXT,
                company TEXT,
                status TEXT DEFAULT 'sent',
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                run_id TEXT,
                run_time TEXT,
                source_url TEXT,
                description TEXT,
                FOREIGN KEY (user_email) REFERENCES user_profiles(email)
            )
        ''')
        
        # Automation runs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS automation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                job_title TEXT,
                location TEXT,
                keywords TEXT,
                total_jobs_found INTEGER DEFAULT 0,
                emails_sent INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                FOREIGN KEY (user_email) REFERENCES user_profiles(email)
            )
        ''')
        
        # Subscriptions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_email TEXT PRIMARY KEY,
                plan TEXT DEFAULT 'free',
                status TEXT DEFAULT 'active',
                razorpay_order_id TEXT,
                razorpay_payment_id TEXT,
                razorpay_subscription_id TEXT,
                amount REAL,
                coupon_code TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES user_profiles(email)
            )
        ''')
        
        # Pending payments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_payments (
                order_id TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                plan TEXT NOT NULL,
                amount REAL NOT NULL,
                coupon_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES user_profiles(email)
            )
        ''')
        
        # Email verifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                verified BOOLEAN DEFAULT 0,
                verified_at TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES user_profiles(email)
            )
        ''')
        
        # Password resets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT 0,
                used_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_name TEXT NOT NULL,
                search_role TEXT NOT NULL,
                position TEXT,
                cron_expression TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                last_run TIMESTAMP,
                next_run TIMESTAMP,
                run_count INTEGER DEFAULT 0,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Auto-scheduler configuration table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_scheduler_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_keyword TEXT NOT NULL,
                scroll_count INTEGER DEFAULT 10,
                is_active BOOLEAN DEFAULT 1,
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Auto-scheduler runs log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_scheduler_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_type TEXT NOT NULL,
                skill_keyword TEXT NOT NULL,
                jobs_found INTEGER DEFAULT 0,
                jobs_saved INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                error_message TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("[OK] SQLite database initialized successfully")
    
    # User Profile Methods
    def create_or_update_profile(self, email: str, display_name: str = None, photo_url: str = None, 
                                 email_subject: str = None, email_content: str = None, 
                                 search_role: str = None, search_time_period: str = None,
                                 resume_data: str = None, resume_filename: str = None,
                                 user_name: str = None, user_phone: str = None):
        """Create or update user profile"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_profiles (email, display_name, photo_url, email_subject, email_content, 
                                      search_role, search_time_period, resume_data, resume_filename,
                                      user_name, user_phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                display_name = COALESCE(excluded.display_name, display_name),
                photo_url = COALESCE(excluded.photo_url, photo_url),
                email_subject = COALESCE(excluded.email_subject, email_subject),
                email_content = COALESCE(excluded.email_content, email_content),
                search_role = COALESCE(excluded.search_role, search_role),
                search_time_period = COALESCE(excluded.search_time_period, search_time_period),
                resume_data = COALESCE(excluded.resume_data, resume_data),
                resume_filename = COALESCE(excluded.resume_filename, resume_filename),
                user_name = COALESCE(excluded.user_name, user_name),
                user_phone = COALESCE(excluded.user_phone, user_phone),
                updated_at = CURRENT_TIMESTAMP
        ''', (email, display_name, photo_url, email_subject, email_content, 
              search_role, search_time_period, resume_data, resume_filename, user_name, user_phone))
        
        conn.commit()
        conn.close()
        return True
    
    def get_profile(self, email: str) -> Optional[Dict]:
        """Get user profile"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user_profiles WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    # Job Posts Methods
    def save_job_posts(self, user_email: str, jobs: List[Dict]):
        """Save multiple job posts (only saves posts with recruiter emails)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        saved_count = 0
        for job in jobs:
            # Only save if recruiter email is present
            recruiter_email = job.get('email') or job.get('recruiter_email')
            if not recruiter_email or '@' not in recruiter_email:
                print(f"⚠️ Skipping job post without recruiter email: {job.get('title')}")
                continue
                
            cursor.execute('''
                INSERT INTO job_posts (user_email, title, company, location, job_url, recruiter_email, skills, full_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_email,
                job.get('title', ''),
                job.get('company', ''),
                job.get('location', ''),
                job.get('job_url', ''),
                recruiter_email,
                json.dumps(job.get('skills', [])),
                job.get('full_text', '')
            ))
            saved_count += 1
        
        conn.commit()
        conn.close()
        print(f"[OK] Saved {saved_count}/{len(jobs)} job posts (only with recruiter emails)")
        return True
    
    def get_job_posts(self, user_email: str = None, limit: int = 100) -> List[Dict]:
        """Get job posts - returns ALL posts for all users (universal/shared)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get ALL job posts regardless of user (universal/shared)
        cursor.execute('SELECT COUNT(*) as total FROM job_posts')
        count_result = cursor.fetchone()
        total_posts = count_result['total'] if count_result else 0
        print(f"[INFO] DB Query: Found {total_posts} total job posts (universal/shared)")
        
        # Build query with optional LIMIT
        if limit is None:
            cursor.execute('''
                SELECT * FROM job_posts 
                ORDER BY created_at DESC
            ''')
        else:
            cursor.execute('''
                SELECT * FROM job_posts 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        jobs = []
        for row in rows:
            job = dict(row)
            # Parse skills JSON safely - handle empty strings and invalid JSON
            try:
                job['skills'] = json.loads(job['skills']) if (job['skills'] and job['skills'].strip()) else []
            except (json.JSONDecodeError, TypeError):
                job['skills'] = []
            # Map recruiter_email to email for template compatibility
            if 'recruiter_email' in job and job['recruiter_email']:
                job['email'] = job['recruiter_email']
            jobs.append(job)
        
        print(f"[INFO] Returning {len(jobs)} job posts (universal for all users)")
        return jobs
    
    def get_job_stats(self, user_email: str = None) -> Dict:
        """Get job statistics - universal for all users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get total jobs from ALL users (universal/shared)
        cursor.execute('SELECT COUNT(*) as total FROM job_posts')
        total = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(DISTINCT company) as companies FROM job_posts')
        companies = cursor.fetchone()['companies']
        
        cursor.execute('SELECT COUNT(DISTINCT location) as locations FROM job_posts')
        locations = cursor.fetchone()['locations']
        
        conn.close()
        
        print(f"[INFO] Job Stats (Universal): {total} total jobs, {companies} companies, {locations} locations")
        
        return {
            'total_jobs': total,
            'unique_companies': companies,
            'unique_locations': locations
        }
    
    # Sent Emails Methods
    def save_sent_email(self, user_email: str, email_data: Dict):
        """Save sent email record with all fields"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if new columns exist, if not add them
        cursor.execute("PRAGMA table_info(sent_emails)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'run_id' not in columns:
            print("Adding run_id column to sent_emails table")
            cursor.execute('ALTER TABLE sent_emails ADD COLUMN run_id TEXT')
        if 'run_time' not in columns:
            print("Adding run_time column to sent_emails table")
            cursor.execute('ALTER TABLE sent_emails ADD COLUMN run_time TEXT')
        if 'source_url' not in columns:
            print("Adding source_url column to sent_emails table")
            cursor.execute('ALTER TABLE sent_emails ADD COLUMN source_url TEXT')
        if 'description' not in columns:
            print("Adding description column to sent_emails table")
            cursor.execute('ALTER TABLE sent_emails ADD COLUMN description TEXT')
        
        conn.commit()
        
        # Now insert the record with all fields
        cursor.execute('''
            INSERT INTO sent_emails 
            (user_email, recipient_email, subject, body, job_title, company, status, run_id, run_time, source_url, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_email,
            email_data.get('recipient_email', ''),
            email_data.get('subject', ''),
            email_data.get('body', ''),
            email_data.get('job_title', ''),
            email_data.get('company', ''),
            email_data.get('status', 'sent'),
            email_data.get('run_id', ''),
            email_data.get('run_time', ''),
            email_data.get('source_url', ''),
            email_data.get('description', '')
        ))
        
        conn.commit()
        conn.close()
        print(f"[OK] Saved sent email to database: {email_data.get('recipient_email')} - {email_data.get('subject')}")
        return True
    
    def get_sent_emails(self, user_email: str, limit: int = 100) -> List[Dict]:
        """Get sent emails for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM sent_emails 
            WHERE user_email = ? 
            ORDER BY sent_at DESC 
            LIMIT ?
        ''', (user_email, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_email_stats(self, user_email: str) -> Dict:
        """Get email statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total FROM sent_emails WHERE user_email = ?', (user_email,))
        total = cursor.fetchone()['total']
        
        cursor.execute('''
            SELECT COUNT(*) as today 
            FROM sent_emails 
            WHERE user_email = ? AND DATE(sent_at) = DATE('now')
        ''', (user_email,))
        today = cursor.fetchone()['today']
        
        conn.close()
        
        return {
            'total_emails': total,
            'emails_today': today
        }
    
    # Subscription Methods
    def create_or_update_subscription(self, user_email: str, subscription_data: Dict):
        """Create or update subscription"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO subscriptions (
                user_email, plan, status, razorpay_order_id, razorpay_payment_id, 
                razorpay_subscription_id, amount, coupon_code, expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_email) DO UPDATE SET
                plan = excluded.plan,
                status = excluded.status,
                razorpay_order_id = COALESCE(excluded.razorpay_order_id, razorpay_order_id),
                razorpay_payment_id = COALESCE(excluded.razorpay_payment_id, razorpay_payment_id),
                razorpay_subscription_id = COALESCE(excluded.razorpay_subscription_id, razorpay_subscription_id),
                amount = COALESCE(excluded.amount, amount),
                coupon_code = COALESCE(excluded.coupon_code, coupon_code),
                expires_at = COALESCE(excluded.expires_at, expires_at)
        ''', (
            user_email,
            subscription_data.get('plan', 'free'),
            subscription_data.get('status', 'active'),
            subscription_data.get('razorpay_order_id'),
            subscription_data.get('razorpay_payment_id'),
            subscription_data.get('razorpay_subscription_id'),
            subscription_data.get('amount'),
            subscription_data.get('coupon_code'),
            subscription_data.get('expires_at')
        ))
        
        conn.commit()
        conn.close()
        return True
    
    def get_subscription(self, user_email: str) -> Optional[Dict]:
        """Get user subscription"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM subscriptions WHERE user_email = ?', (user_email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        
        # Return default free subscription
        return {
            'user_email': user_email,
            'plan': 'free',
            'status': 'active'
        }
    
    # Automation Run Methods
    def save_automation_run(self, user_email: str, run_data: Dict):
        """Save automation run"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO automation_runs (
                user_email, job_title, location, keywords, 
                total_jobs_found, emails_sent, status, completed_at, error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_email,
            run_data.get('job_title', ''),
            run_data.get('location', ''),
            run_data.get('keywords', ''),
            run_data.get('total_jobs_found', 0),
            run_data.get('emails_sent', 0),
            run_data.get('status', 'completed'),
            run_data.get('completed_at'),
            run_data.get('error_message')
        ))
        
        conn.commit()
        conn.close()
        return True
    
    def get_automation_runs(self, user_email: str, limit: int = 50) -> List[Dict]:
        """Get automation runs for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM automation_runs 
            WHERE user_email = ? 
            ORDER BY started_at DESC 
            LIMIT ?
        ''', (user_email, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # Email Verification Methods
    def create_verification_token(self, user_email: str, token: str, expires_at: datetime):
        """Create email verification token"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO email_verifications (user_email, token, expires_at)
            VALUES (?, ?, ?)
        ''', (user_email, token, expires_at))
        
        conn.commit()
        conn.close()
        return True
    
    def get_verification_by_token(self, token: str) -> Optional[Dict]:
        """Get verification record by token"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM email_verifications WHERE token = ?
        ''', (token,))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def mark_email_verified(self, user_email: str):
        """Mark user email as verified"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE email_verifications 
            SET verified = 1, verified_at = CURRENT_TIMESTAMP
            WHERE user_email = ?
        ''', (user_email,))
        
        conn.commit()
        conn.close()
        return True
    
    def is_email_verified(self, user_email: str) -> bool:
        """Check if user email is verified"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT verified FROM email_verifications 
            WHERE user_email = ? AND verified = 1
            LIMIT 1
        ''', (user_email,))
        
        row = cursor.fetchone()
        conn.close()
        
        return bool(row)
    
    def delete_old_verification_tokens(self, user_email: str):
        """Delete old verification tokens for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM email_verifications 
            WHERE user_email = ? AND verified = 0
        ''', (user_email,))
        
        conn.commit()
        conn.close()
        return True
    
    # Password Reset Methods
    def create_reset_token(self, user_email: str, token: str, expires_at: datetime):
        """Create password reset token"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO password_resets (user_email, token, expires_at)
            VALUES (?, ?, ?)
        ''', (user_email, token, expires_at))
        
        conn.commit()
        conn.close()
        return True
    
    def get_reset_by_token(self, token: str) -> Optional[Dict]:
        """Get password reset record by token"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM password_resets WHERE token = ? AND used = 0
        ''', (token,))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def mark_reset_token_used(self, token: str):
        """Mark password reset token as used"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE password_resets 
            SET used = 1, used_at = CURRENT_TIMESTAMP
            WHERE token = ?
        ''', (token,))
        
        conn.commit()
        conn.close()
        return True

    # Scheduled Jobs Methods
    def create_scheduled_job(self, job_name: str, search_role: str, position: str, 
                            cron_expression: str, created_by: str):
        """Create a new scheduled job"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO scheduled_jobs (job_name, search_role, position, cron_expression, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (job_name, search_role, position, cron_expression, created_by))
        
        job_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return job_id
    
    def get_all_scheduled_jobs(self):
        """Get all scheduled jobs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM scheduled_jobs ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_active_scheduled_jobs(self):
        """Get all active scheduled jobs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM scheduled_jobs 
            WHERE is_active = 1 
            ORDER BY next_run ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def update_scheduled_job(self, job_id: int, job_name: str = None, search_role: str = None, 
                            position: str = None, cron_expression: str = None, is_active: bool = None):
        """Update a scheduled job"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if job_name is not None:
            updates.append("job_name = ?")
            params.append(job_name)
        if search_role is not None:
            updates.append("search_role = ?")
            params.append(search_role)
        if position is not None:
            updates.append("position = ?")
            params.append(position)
        if cron_expression is not None:
            updates.append("cron_expression = ?")
            params.append(cron_expression)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(job_id)
            
            cursor.execute(f'''
                UPDATE scheduled_jobs 
                SET {", ".join(updates)}
                WHERE id = ?
            ''', params)
            
            conn.commit()
        
        conn.close()
        return True
    
    def update_job_run_info(self, job_id: int, last_run: datetime, next_run: datetime):
        """Update job run information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE scheduled_jobs 
            SET last_run = ?, next_run = ?, run_count = run_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (last_run, next_run, job_id))
        
        conn.commit()
        conn.close()
        return True
    
    def delete_scheduled_job(self, job_id: int):
        """Delete a scheduled job"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM scheduled_jobs WHERE id = ?', (job_id,))
        
        conn.commit()
        conn.close()
        return True
    
    # Auto-scheduler methods
    def get_all_auto_scheduler_skills(self):
        """Get all auto-scheduler skills"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM auto_scheduler_config 
            ORDER BY priority DESC, skill_keyword ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_active_auto_scheduler_skills(self):
        """Get active auto-scheduler skills"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM auto_scheduler_config 
            WHERE is_active = 1
            ORDER BY priority DESC, skill_keyword ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def add_auto_scheduler_skill(self, skill_keyword: str, scroll_count: int = 10, priority: int = 0):
        """Add a new skill to auto-scheduler"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO auto_scheduler_config (skill_keyword, scroll_count, priority)
            VALUES (?, ?, ?)
        ''', (skill_keyword, scroll_count, priority))
        
        conn.commit()
        skill_id = cursor.lastrowid
        conn.close()
        
        return skill_id
    
    def update_auto_scheduler_skill(self, skill_id: int, skill_keyword: str = None, 
                                   scroll_count: int = None, is_active: bool = None, priority: int = None):
        """Update an auto-scheduler skill"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if skill_keyword is not None:
            updates.append("skill_keyword = ?")
            params.append(skill_keyword)
        if scroll_count is not None:
            updates.append("scroll_count = ?")
            params.append(scroll_count)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(skill_id)
            
            cursor.execute(f'''
                UPDATE auto_scheduler_config 
                SET {", ".join(updates)}
                WHERE id = ?
            ''', params)
            
            conn.commit()
        
        conn.close()
        return True
    
    def delete_auto_scheduler_skill(self, skill_id: int):
        """Delete an auto-scheduler skill"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM auto_scheduler_config WHERE id = ?', (skill_id,))
        
        conn.commit()
        conn.close()
        return True
    
    def toggle_job_bookmark(self, job_id: int):
        """Toggle bookmark status for a job post"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get current bookmark status
        cursor.execute('SELECT bookmarked FROM job_posts WHERE id = ?', (job_id,))
        row = cursor.fetchone()
        
        if row is None:
            conn.close()
            return False
        
        current_status = row[0] if row[0] is not None else 0
        new_status = 0 if current_status == 1 else 1
        
        # Update bookmark status
        cursor.execute('UPDATE job_posts SET bookmarked = ? WHERE id = ?', (new_status, job_id))
        conn.commit()
        conn.close()
        
        return new_status
    
    def get_bookmarked_count(self, user_email: str = None):
        """Get count of bookmarked jobs (universal/shared across all users)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Count all bookmarked jobs regardless of user (universal/shared)
        cursor.execute('''
            SELECT COUNT(*) FROM job_posts 
            WHERE bookmarked = 1
        ''')
        
        count = cursor.fetchone()[0]
        conn.close()
        
        print(f"[INFO] Bookmarked count: {count} (universal/shared)")
        return count
    
    def log_auto_scheduler_run(self, run_type: str, skill_keyword: str, jobs_found: int = 0, 
                              jobs_saved: int = 0, status: str = 'success', error_message: str = None):
        """Log an auto-scheduler run"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO auto_scheduler_runs 
            (run_type, skill_keyword, jobs_found, jobs_saved, status, error_message, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (run_type, skill_keyword, jobs_found, jobs_saved, status, error_message))
        
        conn.commit()
        run_id = cursor.lastrowid
        conn.close()
        
        return run_id
    
    def get_auto_scheduler_run_history(self, limit: int = 100):
        """Get auto-scheduler run history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM auto_scheduler_runs 
            ORDER BY started_at DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
        
        conn.commit()
        conn.close()
        return True
