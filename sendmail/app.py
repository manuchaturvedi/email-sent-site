from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Response, send_file
from functools import wraps
import firebase_admin
from firebase_admin import credentials, auth
from job_analyzer import JobAnalyzer
from database import Database  # Import SQLite database

# Import logging
from logger_config import app_logger, error_logger, scraper_logger, auth_logger, email_logger, activity_logger, LOGS_DIR

# Import utilities from refactored modules
from utils.helpers import extract_company_from_email, parse_skills
from utils.decorators import login_required, admin_required, ADMIN_EMAIL
from services.email_service import (send_plain_email, send_admin_alert, 
                                   send_verification_email, send_password_reset_email,
                                   send_welcome_email, send_automation_summary_email,
                                   send_missed_opportunity_email, send_success_summary_email)
from services.job_service import (
    is_duplicate_job_post, load_job_posts, save_job_post,
    load_sent_emails, get_user_email_stats, prepare_email_record,
    count_emails_sent_today, check_email_limit, save_sent_email
)
import config

import uuid
import hashlib
import base64
import threading
from queue import Queue, Empty
import os
import smtplib
import time
import tempfile
import shutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime, timedelta
import json
import platform
import urllib3.exceptions
import http.client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


app = Flask(__name__)

# Activity logging middleware
@app.before_request
def log_request():
    """Log every request with user info"""
    user = session.get('user', 'anonymous')
    activity_logger.info(f"[{request.method}] {request.path} | User: {user} | IP: {request.remote_addr}")

@app.after_request
def log_response(response):
    """Log response status"""
    user = session.get('user', 'anonymous')
    activity_logger.info(f"[{request.method}] {request.path} | Status: {response.status_code} | User: {user}")
    return response

# Initialize SQLite database with absolute path
# Ensures admin panel and main functions use the same database
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'justmailit.db')
DB_PATH = os.path.abspath(DB_PATH)  # Normalize path: /app/justmailit.db
print(f"[DATABASE] Using database at: {DB_PATH}")
app_logger.info(f"Using database at: {DB_PATH}")
db = Database(db_path=DB_PATH)

# Cron Scheduler for scheduled jobs
scheduler_running = False
scheduler_thread = None

def run_scheduler():
    """Background thread that checks and runs scheduled jobs"""
    global scheduler_running
    from croniter import croniter
    
    print("[SCHEDULER] Starting job scheduler...")
    scheduler_running = True
    
    while scheduler_running:
        try:
            # Get all active scheduled jobs
            jobs = db.get_active_scheduled_jobs()
            now = datetime.now()
            
            if jobs:
                print(f"[SCHEDULER] Checking {len(jobs)} active job(s) at {now.strftime('%H:%M:%S')}", flush=True)
            
            for job in jobs:
                try:
                    # Calculate next run time if not set
                    if not job.get('next_run'):
                        cron = croniter(job['cron_expression'], now)
                        next_run = cron.get_next(datetime)
                        db.update_job_run_info(job['id'], None, next_run)
                        print(f"[SCHEDULER] Set next run for job #{job['id']} to {next_run}", flush=True)
                        continue
                    
                    # Check if job should run
                    next_run_time = datetime.fromisoformat(job['next_run'])
                    print(f"[SCHEDULER] Job #{job['id']} next run: {next_run_time.strftime('%H:%M:%S')}, now: {now.strftime('%H:%M:%S')}", flush=True)
                    if now >= next_run_time:
                        print(f"[SCHEDULER] Running scheduled job #{job['id']}: {job['job_name']}", flush=True)
                        
                        # Run scraping ONLY - save jobs to database without sending emails
                        def run_job(job_data):
                            try:
                                print(f"[SCHEDULER] Triggering job scraping for: {job_data['search_role']}", flush=True)
                                
                                # Call scraping function that only saves to DB (no email sending)
                                scrape_and_save_jobs(
                                    search_role=job_data['search_role'],
                                    search_time='past-week',
                                    user_email='scheduler@justmailit.in',
                                    scrolls=10
                                )
                                
                                # Calculate next run time
                                run_time = datetime.now()
                                cron = croniter(job_data['cron_expression'], run_time)
                                next_run = cron.get_next(datetime)
                                
                                db.update_job_run_info(job_data['id'], run_time, next_run)
                                print(f"[SCHEDULER] Completed job #{job_data['id']}. Next run: {next_run}", flush=True)
                                
                            except Exception as e:
                                print(f"[SCHEDULER] Error running job #{job_data['id']}: {str(e)}", flush=True)
                                import traceback
                                traceback.print_exc()
                        
                        job_thread = threading.Thread(target=run_job, args=(job,), daemon=True)
                        job_thread.start()
                        
                except Exception as job_error:
                    print(f"[SCHEDULER] Error processing job #{job.get('id', 'unknown')}: {str(job_error)}")
            
            # Sleep for 60 seconds before checking again
            time.sleep(60)
            
        except Exception as e:
            print(f"[SCHEDULER] Scheduler error: {str(e)}")
            time.sleep(60)
    
    print("[SCHEDULER] Scheduler stopped")

# Start scheduler in background thread
def start_scheduler():
    global scheduler_thread
    if not scheduler_thread or not scheduler_thread.is_alive():
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        print("[SCHEDULER] Scheduler thread started")

# Server-Sent Events clients (each client gets a Queue)
clients = []
clients_lock = threading.Lock()

# --- UTILITY FUNCTIONS (Moved to utils/helpers.py) ---
# Keeping original code commented for safety - DELETE AFTER TESTING

# def extract_company_from_email(email):
#     """Extract and format company name from email address"""
#     try:
#         # Get domain part
#         domain = email.split('@')[1]
#         
#         # Remove common TLDs
#         domain = domain.replace('.com', '').replace('.co.uk', '').replace('.org', '')
#         domain = domain.replace('.net', '').replace('.io', '').replace('.ai', '')
#         domain = domain.replace('.edu', '').replace('.gov', '').replace('.in', '')
#         
#         # Handle subdomains (e.g., hr.company.com -> company)
#         parts = domain.split('.')
#         if len(parts) > 1:
#             # Take the last part before TLD (usually company name)
#             domain = parts[-1]
#         
#         # Clean and format
#         domain = domain.strip().replace('-', ' ').replace('_', ' ')
#         
#         # Capitalize each word
#         company_name = ' '.join(word.capitalize() for word in domain.split())
#         
#         return company_name if company_name else "Unknown Company"
#     except:
#         return "Unknown Company"

# def parse_skills(skills_string):
#     """Parse skills from string - handles both commas and spaces as separators"""
#     if not skills_string:
#         return []
#     
#     import re
#     # Replace commas with spaces, then split by spaces and filter empty strings
#     # This handles: "python,java", "python, java", "python java", "python  java"
#     skills_string = skills_string.replace(',', ' ')
#     skill_list = [s.strip() for s in skills_string.split() if s.strip()]
#     return skill_list

def send_upgrade_notification_email(user_email, user_name, plan, duration_days=None, upgraded_by='self'):
    """Send email notification when user is upgraded to Pro"""
    from services.email_service import send_html_email, get_html_template
    from datetime import datetime, timedelta
    
    try:
        # Calculate expiry date
        if duration_days:
            expiry_date = (datetime.now() + timedelta(days=duration_days)).strftime('%B %d, %Y')
        else:
            expiry_date = (datetime.now() + timedelta(days=30)).strftime('%B %d, %Y')
        
        # Email subject and content based on who upgraded
        if upgraded_by == 'admin':
            subject = "🎉 Your JustMailIt Account Has Been Upgraded to Pro!"
            
            html_content = get_html_template(f'''
                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="font-size: 64px; margin-bottom: 20px;">🎉</div>
                    <h2 style="color: #2d3748; margin: 0 0 10px 0; font-size: 26px; font-weight: 700;">Congratulations!</h2>
                    <p style="color: #718096; margin: 0; font-size: 16px;">Your account has been upgraded to Pro</p>
                </div>
                
                <p style="color: #4a5568; margin: 0 0 25px 0; font-size: 15px; line-height: 1.6;">
                    Hi <strong>{user_name}</strong>,
                </p>
                
                <p style="color: #4a5568; margin: 0 0 25px 0; font-size: 15px; line-height: 1.6;">
                    Great news! Your JustMailIt account has been upgraded to <strong style="color: #667eea;">Pro plan</strong> by our admin team!
                </p>
                
                <div style="background: linear-gradient(135deg, #ffd89b, #19547b); padding: 30px; border-radius: 10px; margin: 25px 0;">
                    <h3 style="color: #ffffff; margin: 0 0 20px 0; font-size: 20px; font-weight: 700; text-align: center;">✨ Your Pro Benefits</h3>
                    <ul style="color: #ffffff; margin: 0; padding-left: 20px; line-height: 2; font-size: 15px;">
                        <li><strong>🚀 Unlimited job applications</strong> - no more daily limits</li>
                        <li><strong>⚡ Priority support</strong> from our team</li>
                        <li><strong>🤖 Advanced AI-powered</strong> job matching</li>
                        <li><strong>🎯 Extended profile</strong> customization</li>
                        <li><strong>📧 No restrictions</strong> on email sending</li>
                    </ul>
                </div>
                
                <div style="background-color: #f7fafc; padding: 20px; border-radius: 8px; margin: 25px 0; text-align: center;">
                    <p style="color: #718096; margin: 0 0 5px 0; font-size: 14px;">📅 Your Pro plan is active until</p>
                    <p style="color: #2d3748; margin: 0; font-size: 20px; font-weight: 700;">{expiry_date}</p>
                </div>
                
                <p style="color: #4a5568; margin: 25px 0; font-size: 15px; line-height: 1.6;">
                    You can now enjoy unlimited job applications and make the most of your job search!
                </p>
                
                <div style="text-align: center; margin: 35px 0;">
                    <a href="https://justmailit.in/dashboard" style="display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: #ffffff; text-decoration: none; padding: 16px 40px; border-radius: 8px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.4);">
                        Go to Dashboard
                    </a>
                </div>
                
                <div style="background-color: #ebf8ff; padding: 20px; border-radius: 8px; border-left: 4px solid #4299e1; margin: 30px 0;">
                    <p style="color: #2c5282; margin: 0; font-size: 14px; line-height: 1.6;">
                        <strong>💡 Need Help?</strong><br>
                        Reply to this email or visit our support page. We're here to help!
                    </p>
                </div>
            ''', "Account Upgraded to Pro")
            
            plain_text = f"""Hi {user_name},

Great news! Your JustMailIt account has been upgraded to Pro plan by our admin team!

✨ Your Pro Benefits:
• Unlimited job applications - no more daily limits
• Priority support from our team
• Advanced AI-powered job matching
• Extended profile customization
• No restrictions on email sending

📅 Your Pro plan is active until: {expiry_date}

You can now enjoy unlimited job applications and make the most of your job search!

Login to your dashboard: https://justmailit.in/dashboard

Need help? Reply to this email or visit our support page.

Best regards,
The JustMailIt Team"""
            
        else:
            subject = "🎉 Welcome to JustMailIt Pro!"
            
            html_content = get_html_template(f'''
                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="font-size: 64px; margin-bottom: 20px;">🚀</div>
                    <h2 style="color: #2d3748; margin: 0 0 10px 0; font-size: 26px; font-weight: 700;">Welcome to Pro!</h2>
                    <p style="color: #718096; margin: 0; font-size: 16px;">Your payment was successful</p>
                </div>
                
                <p style="color: #4a5568; margin: 0 0 25px 0; font-size: 15px; line-height: 1.6;">
                    Hi <strong>{user_name}</strong>,
                </p>
                
                <p style="color: #4a5568; margin: 0 0 25px 0; font-size: 15px; line-height: 1.6;">
                    Thank you for upgrading to <strong style="color: #667eea;">JustMailIt Pro</strong>! 🎉
                </p>
                
                <div style="background: linear-gradient(135deg, #a8edea, #fed6e3); padding: 25px; border-radius: 10px; margin: 25px 0; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 15px;">✅</div>
                    <h3 style="color: #2d3748; margin: 0; font-size: 18px; font-weight: 700;">Payment Successful</h3>
                    <p style="color: #4a5568; margin: 10px 0 0 0; font-size: 14px;">Your Pro subscription is now active</p>
                </div>
                
                <div style="background: linear-gradient(135deg, #667eea, #764ba2); padding: 30px; border-radius: 10px; margin: 25px 0;">
                    <h3 style="color: #ffffff; margin: 0 0 20px 0; font-size: 20px; font-weight: 700; text-align: center;">✨ Your Pro Benefits</h3>
                    <ul style="color: #ffffff; margin: 0; padding-left: 20px; line-height: 2; font-size: 15px;">
                        <li><strong>🚀 Unlimited job applications</strong> - send as many emails as you need</li>
                        <li><strong>⚡ Priority support</strong> from our team</li>
                        <li><strong>🤖 Advanced AI-powered</strong> job matching</li>
                        <li><strong>🎯 Extended profile</strong> customization</li>
                        <li><strong>📧 No daily email limits</strong></li>
                    </ul>
                </div>
                
                <div style="background-color: #f7fafc; padding: 20px; border-radius: 8px; margin: 25px 0; text-align: center;">
                    <p style="color: #718096; margin: 0 0 5px 0; font-size: 14px;">📅 Your subscription is valid until</p>
                    <p style="color: #2d3748; margin: 0; font-size: 20px; font-weight: 700;">{expiry_date}</p>
                </div>
                
                <div style="text-align: center; margin: 35px 0;">
                    <a href="https://justmailit.in/dashboard" style="display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: #ffffff; text-decoration: none; padding: 16px 40px; border-radius: 8px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.4);">
                        Start Sending Unlimited Emails
                    </a>
                </div>
                
                <div style="background-color: #fffff0; padding: 20px; border-radius: 8px; border-left: 4px solid #f6ad55; margin: 30px 0;">
                    <p style="color: #744210; margin: 0; font-size: 14px; line-height: 1.6;">
                        <strong>💡 Questions or need assistance?</strong><br>
                        Feel free to reach out to us. We're here to help you succeed!
                    </p>
                </div>
            ''', "Welcome to Pro")
            
            plain_text = f"""Hi {user_name},

Thank you for upgrading to JustMailIt Pro! 🚀

Your payment has been successfully processed, and your Pro subscription is now active.

✨ Your Pro Benefits:
• Unlimited job applications - send as many emails as you need
• Priority support from our team
• Advanced AI-powered job matching
• Extended profile customization
• No daily email limits

📅 Your subscription is valid until: {expiry_date}

Start sending unlimited job applications now: https://justmailit.in/dashboard

If you have any questions or need assistance, feel free to reach out to us.

Best regards,
The JustMailIt Team"""
        
        # Send HTML email
        success = send_html_email(user_email, subject, html_content, plain_text)
        
        if success:
            print(f"[OK] Upgrade notification email sent to {user_email}")
        return success
        
    except Exception as e:
        print(f"[ERROR] Failed to send upgrade notification email: {str(e)}")
        return False

def cleanup_chrome_processes():
    """Cross-platform Chrome process cleanup - kills all Chrome/Chromium processes"""
    try:
        system = platform.system().lower()
        if system == "windows":
            os.system('taskkill /f /im chrome.exe 2>nul')
            os.system('taskkill /f /im chromedriver.exe 2>nul')
        else:
            # Linux/Unix systems - kill Chrome, Chromium, and ChromeDriver
            os.system('pkill -9 -f "chrome|chromium" 2>/dev/null || true')
            os.system('pkill -9 chromedriver 2>/dev/null || true')
            # Extra cleanup for zombie processes
            os.system('pkill -9 -f "defunct.*chrome" 2>/dev/null || true')
        print("[DONE] Chrome processes cleaned up")
    except Exception as e:
        print(f"[WARN] Chrome cleanup failed: {e}")

def extract_resume_info(resume_path):
    """Extract key information from resume file"""
    try:
        import PyPDF2
        
        with open(resume_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
        
        print(f"[INFO] Extracted text length: {len(text)} characters")
        
        # Extract name (usually first few lines, look for capitalized words)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        name = "Candidate"
        
        # Try to find name in first 5 lines - look for pattern of capitalized words
        for line in lines[:5]:
            words = line.split()
            if len(words) >= 2 and len(words) <= 4:
                # Check if all words start with capital letter
                if all(w[0].isupper() for w in words if w.isalpha()):
                    name = line
                    break
        
        # Extract email and phone
        import re
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        phone_match = re.search(r'[\+\(]?[0-9][0-9 \-\(\)]{8,}[0-9]', text)
        
        email = email_match.group(0) if email_match else ""
        phone = phone_match.group(0) if phone_match else ""
        
        # Extract skills (look for common skill keywords with better matching)
        skills = []
        skill_keywords = {
            'python': 'Python', 'java': 'Java', 'javascript': 'JavaScript', 'react': 'React', 
            'node.js': 'Node.js', 'nodejs': 'Node.js', 'node': 'Node.js', 'aws': 'AWS', 'docker': 'Docker',
            'kubernetes': 'Kubernetes', 'sql': 'SQL', 'mysql': 'MySQL', 'postgresql': 'PostgreSQL',
            'mongodb': 'MongoDB', 'machine learning': 'Machine Learning', 'ai': 'AI', 'devops': 'DevOps',
            'angular': 'Angular', 'vue': 'Vue.js', 'django': 'Django', 'flask': 'Flask', 
            'spring': 'Spring', 'microservices': 'Microservices', 'typescript': 'TypeScript',
            'golang': 'Go', 'rust': 'Rust', 'c++': 'C++', 'ruby': 'Ruby', 'php': 'PHP', 
            'swift': 'Swift', 'kotlin': 'Kotlin', 'terraform': 'Terraform', 'jenkins': 'Jenkins',
            'git': 'Git', 'linux': 'Linux', 'azure': 'Azure', 'gcp': 'GCP', 'html': 'HTML',
            'css': 'CSS', 'sass': 'Sass', 'redux': 'Redux', 'express': 'Express', 'fastapi': 'FastAPI',
            'graphql': 'GraphQL', 'redis': 'Redis', 'elasticsearch': 'Elasticsearch',
            'tableau': 'Tableau', 'power bi': 'Power BI', 'excel': 'Excel', 'pandas': 'Pandas',
            'numpy': 'NumPy', 'tensorflow': 'TensorFlow', 'pytorch': 'PyTorch', 'scikit-learn': 'Scikit-learn'
        }
        
        text_lower = text.lower()
        found_skills = set()
        for keyword, display_name in skill_keywords.items():
            # Use word boundaries for better matching
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                found_skills.add(display_name)
        
        skills = list(found_skills)[:10]  # Top 10 skills
        
        # Extract position/title (look for common job title patterns)
        position = ''
        job_titles = [
            'software developer', 'software engineer', 'full stack developer', 'frontend developer',
            'backend developer', 'web developer', 'mobile developer', 'devops engineer',
            'data scientist', 'data analyst', 'data engineer', 'machine learning engineer',
            'ai engineer', 'cloud engineer', 'solutions architect', 'system administrator',
            'qa engineer', 'test engineer', 'product manager', 'project manager',
            'business analyst', 'ui/ux designer', 'graphic designer', 'technical lead',
            'senior developer', 'junior developer', 'intern', 'fresher'
        ]
        
        for title in job_titles:
            if re.search(r'\b' + re.escape(title) + r'\b', text_lower):
                position = title.title()
                break
        
        # Extract experience (look for years of experience)
        experience = "experienced professional"
        exp_match = re.search(r'(\d+)\s*(?:\+)?\s*(?:year|yr)s?\s+(?:of\s+)?experience', text_lower)
        if exp_match:
            years = exp_match.group(1)
            experience = f"{years}+ years experienced"
        
        print(f"[OK] Extracted - Name: {name}, Position: {position}, Skills: {len(skills)}, Email: {email}, Phone: {phone}")
        
        return {
            'name': name,
            'position': position,
            'skills': skills,
            'experience': experience,
            'email': email,
            'phone': phone
        }
    except Exception as e:
        print(f"[ERROR] Resume parsing error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'name': 'Candidate',
            'skills': [],
            'experience': 'experienced professional',
            'email': '',
            'phone': ''
        }

def generate_email_templates(role, resume_info):
    """Generate professional email subject and body based on role and resume"""
    
    name = resume_info.get('name', 'Candidate')
    skills = resume_info.get('skills', [])
    experience = resume_info.get('experience', 'experienced professional')
    email = resume_info.get('email', '')
    phone = resume_info.get('phone', '')
    
    # Generate subject lines with contact info
    subjects = [
        f"Application for {role} Position - {name}",
        f"{experience.title()} {role} Seeking Opportunities - {name}",
        f"{role} Application | {name} | {experience.title()}",
    ]
    
    # Generate email body
    skills_text = ", ".join(skills[:6]) if skills else "relevant technologies"
    
    # Add contact info section
    contact_info = []
    if email:
        contact_info.append(f"Email: {email}")
    else:
        contact_info.append("Email: [Add your email here]")
    
    if phone:
        contact_info.append(f"Phone: {phone}")
    else:
        contact_info.append("Phone: [Add your phone number here]")
    
    contact_section = "\n".join(contact_info)
    
    body = f"""Dear Hiring Manager,

I am writing to express my interest in the {role} position at your esteemed organization. As an {experience} with expertise in {skills_text}, I am confident that I can contribute effectively to your team.

Key Highlights:
• {experience.title()} in the field
• Strong proficiency in {skills_text}
• Proven track record of delivering quality results
• Excellent problem-solving and communication skills

I have attached my resume for your review. I would welcome the opportunity to discuss how my background aligns with your needs.

Thank you for considering my application. I look forward to hearing from you.

Best regards,
{name}
{contact_section}"""

    return {
        'subjects': subjects,
        'body': body,
        'name': name,
        'has_contact': bool(email and phone)
    }

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

# ========== CONFIGURATION (Moved to config.py) ==========
# Keeping original code commented for safety - DELETE AFTER TESTING
# # Razorpay Payment Gateway Configuration
# RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_live_RgNB6M60lUvK2l")
# RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "i4GM8FcOw34g438OMecg2z78")
# 
# # Optional persistent Chrome profile directory helps preserve LinkedIn login state.
# _env_profile = os.getenv("CHROME_PROFILE_DIR")
# _default_profile = r"D:\Profile"
# if _env_profile:
#     CHROME_PROFILE_DIR = _env_profile
# elif os.path.exists(_default_profile):
#     CHROME_PROFILE_DIR = _default_profile
# else:
#     CHROME_PROFILE_DIR = None
# 
# # LinkedIn credentials for programmatic login (fallback)
# LINKEDIN_EMAIL = "manudrive04@gmail.com"
# LINKEDIN_PASSWORD = "Jpking@232"

# Use configuration from config module
UPLOAD_FOLDER = config.UPLOAD_FOLDER
JOB_POSTS_FILE = config.JOB_POSTS_FILE
SENT_EMAILS_FILE = config.SENT_EMAILS_FILE
RAZORPAY_KEY_ID = config.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = config.RAZORPAY_KEY_SECRET
CHROME_PROFILE_DIR = config.CHROME_PROFILE_DIR
LINKEDIN_EMAIL = config.LINKEDIN_EMAIL
LINKEDIN_PASSWORD = config.LINKEDIN_PASSWORD

# Initialize Razorpay Client
try:
    import razorpay
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    print(f"[OK] Razorpay Payment Gateway initialized")
except ImportError:
    print("[WARN] Razorpay SDK not installed. Payment features will be limited.")
    razorpay_client = None

# Global variables for automation - Per-user session management
automation_sessions = {}  # {user_email: {'running': bool, 'driver': driver, 'stop_flag': bool, 'thread': thread}}

# Legacy global variables (kept for backward compatibility)
automation_driver = None
verification_code_submitted = None
verification_code_value = None
automation_stop_flag = False
automation_running = False

# ========== JOB AND EMAIL TRACKING FUNCTIONS (Moved to services/job_service.py) ==========
# Keeping original code commented for safety - DELETE AFTER TESTING
# All job post and email tracking functions have been moved to services/job_service.py:
# - is_duplicate_job_post()
# - load_job_posts()
# - save_job_post()
# - load_sent_emails()
# - get_user_email_stats()
# - prepare_email_record()
# - count_emails_sent_today()
# - check_email_limit()
# - save_sent_email()

# Flask secret key (moved to config.py)
app.secret_key = config.SECRET_KEY

# Initialize Firebase Admin SDK
# Initialize Firebase with credentials (cloud-compatible)
import base64
import json

def initialize_firebase():
    """Initialize Firebase with environment variable or local file"""
    try:
        # Try environment variable first (for cloud deployment)
        firebase_json_b64 = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        
        if firebase_json_b64:
            print("[LOGIN] Loading Firebase credentials from environment variable")
            # Decode base64 and parse JSON
            firebase_json_str = base64.b64decode(firebase_json_b64).decode('utf-8')
            firebase_config = json.loads(firebase_json_str)
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
            print("[OK] Firebase initialized from environment variable")
            return True
            
        else:
            # Fallback to local file (for development)
            cred_path = os.path.join(os.path.dirname(__file__), "justmailit-d6f2d-firebase-adminsdk-fbsvc-552f0c36ab.json")
            if os.path.exists(cred_path):
                print(f"[LOGIN] Loading Firebase credentials from local file: {cred_path}")
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("[OK] Firebase initialized from local file")
                return True
            else:
                print("[WARN] No Firebase credentials found - running without Firebase")
                return False
                
    except Exception as e:
        print(f"[ERROR] Firebase initialization failed: {e}")
        return False

# Initialize Firebase
firebase_initialized = initialize_firebase()

print("[OK] Using SQLite database for data storage")
print("[OK] Firebase is used for authentication only")


# --- LOGIN CONTROL (Moved to utils/decorators.py) ---
# Keeping original code commented for safety - DELETE AFTER TESTING
# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if "user" not in session:
#             flash("Please log in first!", "warning")
#             return redirect(url_for("login"))
#         return f(*args, **kwargs)
#     return decorated_function


# ========== EMAIL HELPERS FOR TRANSACTIONAL MAILS (Moved to services/email_service.py) ==========
# Keeping original code commented for safety - DELETE AFTER TESTING
# def _send_plain_email(recipient_email: str, subject: str, body: str) -> bool:
#     """Send a simple plain-text email using existing SMTP setup."""
#     try:
#         smtp_server = "smtp.gmail.com"
#         smtp_port = 587
#         sender_email = "mail@justmailit.in"
#         smtp_user = "manudrive06@gmail.com"
#         sender_password = "ozds nrqo gduy mnwd"
# 
#         msg = MIMEMultipart()
#         msg["From"] = f"JustMailIt <{sender_email}>"
#         msg["To"] = recipient_email
#         msg["Subject"] = subject
#         msg["Reply-To"] = sender_email
#         msg.attach(MIMEText(body, "plain", "utf-8"))
# 
#         server = smtplib.SMTP(smtp_server, smtp_port)
#         server.starttls()
#         server.login(smtp_user, sender_password)
#         server.sendmail(sender_email, recipient_email, msg.as_string())
#         server.quit()
#         print(f"[OK] Email sent to {recipient_email}: {subject}")
#         return True
#     except Exception as e:
#         print(f"[ERROR] Failed to send email to {recipient_email}: {e}")
#         return False
# 
# 
# def _send_admin_alert(user_email: str, error_type: str, error_message: str, additional_info: dict = None):
#     """Send alert email to admin when automation fails."""
#     try:
#         admin_email = "manudrive06@gmail.com"  # Admin email
#         
#         subject = f"🚨 JustMailIt Automation Failed - {error_type}"
#         
#         body = f"""
# AUTOMATION FAILURE ALERT
# ========================
# 
# User: {user_email}
# Error Type: {error_type}
# Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 
# Error Details:
# {error_message}
# 
# """
#         
#         if additional_info:
#             body += "\nAdditional Information:\n"
#             for key, value in additional_info.items():
#                 body += f"  {key}: {value}\n"
#         
#         body += f"""
# ---
# This is an automated alert from JustMailIt monitoring system.
# Please investigate and resolve the issue.
# 
# Dashboard: https://justmailit.in/admin
# """
#         
#         _send_plain_email(recipient_email=admin_email, subject=subject, body=body)
#         print(f"[ALERT] Admin notification sent for {error_type}")
#     except Exception as e:
#         print(f"[ERROR] Failed to send admin alert: {e}")

# Backward compatibility: keep old function names as aliases
_send_plain_email = send_plain_email
_send_admin_alert = send_admin_alert


# ========== EMAIL VERIFICATION ROUTES ==========
@app.route('/api/send-verification', methods=['POST'])
def api_send_verification():
    """Generate a verification token and email the user a verify link."""
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        if not data:
            print("[ERROR] No data received in /api/send-verification")
            return jsonify({"error": "No data provided"}), 400
            
        user_email = data.get('email', '').strip()
        print(f"[INFO] Verification email request for: {user_email}")
        
        if not user_email or '@' not in user_email:
            return jsonify({"error": "Invalid email"}), 400

        # Create token valid for 24h
        token = str(uuid.uuid4())
        from datetime import timedelta
        expires_at = datetime.now() + timedelta(hours=24)
        db.delete_old_verification_tokens(user_email)
        db.create_verification_token(user_email, token, expires_at)

        # Build verify link
        verify_link = url_for('verify_email', token=token, _external=True)

        ok = send_verification_email(user_email, verify_link)
        if not ok:
            print(f"[ERROR] Failed to send verification email to {user_email}")
            return jsonify({"error": "Failed to send verification email"}), 500

        print(f"[OK] Verification email sent successfully to {user_email}")
        return jsonify({"success": True}), 200
    except Exception as e:
        print(f"[ERROR] /api/send-verification exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500


@app.route('/verify', methods=['GET'])
def verify_email():
    """Handle email verification link clicks."""
    try:
        token = request.args.get('token', '').strip()
        if not token:
            return render_template('message.html', icon='❌', title='Invalid Link', message='Verification token missing.', action_url='/', action_text='Go Home'), 400

        rec = db.get_verification_by_token(token)
        if not rec:
            return render_template('message.html', icon='❌', title='Invalid Link', message='This verification link is invalid or already used.', action_url='/', action_text='Go Home'), 400

        user_email = rec['user_email']
        # Expiry check
        try:
            exp_str = rec['expires_at']
            exp_dt = datetime.fromisoformat(exp_str) if isinstance(exp_str, str) else exp_str
        except Exception:
            # Fallback: treat as expired if parse fails
            exp_dt = datetime.now() - timedelta(seconds=1)

        if exp_dt < datetime.now():
            return render_template('message.html', icon='⏰', title='Link Expired', message='Your verification link has expired. Please request a new one from the sign-in page.', action_url='/', action_text='Go Home'), 400

        # Mark verified in our DB
        db.mark_email_verified(user_email)

        # Update Firebase user flag if initialized
        try:
            if firebase_initialized:
                u = auth.get_user_by_email(user_email)
                auth.update_user(u.uid, email_verified=True)
                # Get display name for welcome email
                display_name = u.display_name or user_email.split('@')[0]
        except Exception as fe:
            print(f"[WARN] Firebase emailVerified update failed for {user_email}: {fe}")
            display_name = user_email.split('@')[0]
        
        # Send welcome email to newly verified user
        try:
            dashboard_url = url_for('landing', _external=True)
            send_welcome_email(user_email, dashboard_url)
            print(f"[OK] Welcome email sent to verified user: {user_email}")
        except Exception as email_error:
            print(f"[WARN] Failed to send welcome email to {user_email}: {email_error}")
            # Don't fail verification if welcome email fails

        return render_template('message.html', icon='✅', title='Email Verified', message='Your email has been successfully verified. You can now sign in to JustMailIt.', action_url='/', action_text='Sign In')
    except Exception as e:
        print(f"[ERROR] /verify: {e}")
        return render_template('message.html', icon='❌', title='Error', message='An unexpected error occurred.', action_url='/', action_text='Go Home'), 500


# ========== PASSWORD RESET ROUTES ==========
@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Generate reset token and email reset link to user."""
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        if not data:
            print("[ERROR] No data received in /forgot-password")
            return jsonify({"message": "No data provided"}), 400
            
        user_email = data.get('email', '').strip()
        print(f"[INFO] Password reset request for: {user_email}")
        
        if not user_email or '@' not in user_email:
            return jsonify({"message": "Invalid email"}), 400

        # Create token valid for 1h
        token = str(uuid.uuid4())
        from datetime import timedelta
        expires_at = datetime.now() + timedelta(hours=1)
        db.create_reset_token(user_email, token, expires_at)

        reset_link = url_for('reset_password_form', token=token, _external=True)
        
        ok = send_password_reset_email(user_email, reset_link)
        if not ok:
            print(f"[ERROR] Failed to send reset email to {user_email}")
            return jsonify({"message": "Failed to send reset email"}), 500

        print(f"[OK] Password reset email sent successfully to {user_email}")
        return jsonify({"success": True}), 200
    except Exception as e:
        print(f"[ERROR] /forgot-password exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": "Server error", "details": str(e)}), 500


@app.route('/reset-password', methods=['GET'])
def reset_password_form():
    """Render the reset form if token is valid and not expired."""
    try:
        token = request.args.get('token', '').strip()
        if not token:
            return render_template('message.html', icon='❌', title='Invalid Link', message='Password reset token missing.', action_url='/', action_text='Go Home'), 400

        rec = db.get_reset_by_token(token)
        if not rec:
            return render_template('message.html', icon='❌', title='Invalid Link', message='This password reset link is invalid or already used.', action_url='/', action_text='Go Home'), 400

        # Expiry check
        try:
            exp_str = rec['expires_at']
            exp_dt = datetime.fromisoformat(exp_str) if isinstance(exp_str, str) else exp_str
        except Exception:
            exp_dt = datetime.now() - timedelta(seconds=1)

        if exp_dt < datetime.now():
            return render_template('message.html', icon='⏰', title='Link Expired', message='Your password reset link has expired. Please request a new one from the login page.', action_url='/', action_text='Go Home'), 400

        return render_template('reset_password.html', token=token)
    except Exception as e:
        print(f"[ERROR] GET /reset-password: {e}")
        return render_template('message.html', icon='❌', title='Error', message='An unexpected error occurred.', action_url='/', action_text='Go Home'), 500


@app.route('/reset-password', methods=['POST'])
def reset_password_submit():
    """Accept JSON {token,password} and update Firebase password if token valid."""
    try:
        data = request.get_json(force=True)
        token = data.get('token', '').strip()
        new_password = data.get('password', '').strip()
        if not token or not new_password or len(new_password) < 6:
            return jsonify({"message": "Invalid token or password too short"}), 400

        rec = db.get_reset_by_token(token)
        if not rec:
            return jsonify({"message": "Invalid or used token"}), 400

        # Expiry check
        try:
            exp_str = rec['expires_at']
            exp_dt = datetime.fromisoformat(exp_str) if isinstance(exp_str, str) else exp_str
        except Exception:
            exp_dt = datetime.now() - timedelta(seconds=1)

        if exp_dt < datetime.now():
            return jsonify({"message": "Token expired"}), 400

        user_email = rec['user_email']
        if firebase_initialized:
            try:
                u = auth.get_user_by_email(user_email)
                auth.update_user(u.uid, password=new_password)
            except Exception as fe:
                print(f"[ERROR] Firebase password update failed for {user_email}: {fe}")
                return jsonify({"message": "Failed to update password"}), 500
        else:
            # If Firebase not initialized, indicate unsupported
            return jsonify({"message": "Password update unavailable"}), 500

        db.mark_reset_token_used(token)
        return jsonify({"success": True})
    except Exception as e:
        print(f"[ERROR] POST /reset-password: {e}")
        return jsonify({"message": "Server error"}), 500


@app.route("/login", methods=["GET", "POST"])
def login():
    # Handle GET request - show landing page with login modal
    if request.method == "GET":
        return redirect(url_for("landing"))
    
    # Handle Firebase authentication from modal (POST)
    data = request.get_json()
    id_token = data.get("idToken")
    display_name = data.get("displayName", "")
    
    auth_logger.info(f"Login request received - displayName: {display_name}")
    
    try:
        # Add clock skew tolerance to handle timestamp differences
        decoded_token = auth.verify_id_token(id_token, check_revoked=False, clock_skew_seconds=60)
        user_email = decoded_token["email"]
        session["user"] = user_email
        
        # Log user in immediately
        auth_logger.info(f"✅ {user_email} authenticated with Firebase")
        
        # Check if this is a new user (doesn't exist in our database yet)
        is_new_user = False
        try:
            auth_logger.info(f"Checking if user exists in DB: {user_email}")
            existing_profile = db.get_profile(user_email)
            if not existing_profile:
                is_new_user = True
                auth_logger.info(f"🆕 New user detected: {user_email}")
            else:
                auth_logger.info(f"✅ Existing user found: {user_email}")
        except Exception as check_error:
            auth_logger.warning(f"⚠️ Error checking user existence: {check_error}")
            is_new_user = True  # Assume new user if check fails
        
        # Create or update user profile in SQLite
        try:
            auth_logger.info(f"Saving profile to DB - email={user_email}, name={display_name or decoded_token.get('name', '')}")
            db.create_or_update_profile(
                email=user_email,
                display_name=display_name or decoded_token.get('name', ''),
                photo_url=decoded_token.get('picture')
            )
            auth_logger.info(f"✅ User profile saved to database: {user_email}")
            
            # Verify the save worked
            verify_profile = db.get_profile(user_email)
            if verify_profile:
                auth_logger.info(f"✅ Profile verification successful: {user_email}")
            else:
                auth_logger.error(f"❌ Profile verification FAILED - not found after save: {user_email}")
                
        except Exception as profile_error:
            auth_logger.error(f"❌ Profile creation error: {profile_error}")
            import traceback
            auth_logger.error(f"Traceback: {traceback.format_exc()}")
            # Continue login even if profile update fails
            if "429" in str(profile_error) or "Quota exceeded" in str(profile_error):
                auth_logger.warning(f"⚠️ Quota exceeded - login successful but profile not synced")
            else:
                auth_logger.warning(f"⚠️ Profile sync error (non-critical): {profile_error}")
        
        # Send welcome email to new users
        if is_new_user:
            try:
                dashboard_url = url_for('landing', _external=True)
                send_welcome_email(user_email, dashboard_url)
                email_logger.info(f"✅ Welcome email sent to new user: {user_email}")
            except Exception as email_error:
                email_logger.warning(f"⚠️ Failed to send welcome email to {user_email}: {email_error}")
                # Don't fail login if welcome email fails
        
        auth_logger.info(f"✅ Login complete for: {user_email}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        auth_logger.error(f"❌ Login failed: {e}")
        import traceback
        auth_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 401


@app.route("/sessionLogin", methods=["POST"])
def session_login():
    data = request.get_json()
    id_token = data.get("idToken")
    try:
        # Add clock skew tolerance to handle timestamp differences
        decoded_token = auth.verify_id_token(id_token, check_revoked=False, clock_skew_seconds=60)
        user_email = decoded_token["email"]
        session["user"] = user_email
        print(f"[OK] {user_email} logged in successfully!")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        return jsonify({"error": str(e)}), 401


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("landing"))


# --- MAIN PAGE ---
@app.route("/profile")
@login_required
def profile():
    """User profile page for managing default templates and resume."""
    return render_template("profile.html")

@app.route("/get_profile")
@login_required
def get_profile():
    """Get user profile data from SQLite."""
    user_email = session.get("user")
    try:
        profile = db.get_profile(user_email)
        if profile:
            # Convert to dict and remove BLOB data (can't be JSON serialized)
            profile_dict = dict(profile)
            
            # Handle resume BLOB
            if 'resume_data' in profile_dict:
                resume_blob = profile_dict['resume_data']
                if resume_blob:
                    profile_dict['resume_size'] = len(resume_blob)
                    profile_dict['has_resume'] = True
                else:
                    profile_dict['resume_size'] = 0
                    profile_dict['has_resume'] = False
                del profile_dict['resume_data']  # Remove BLOB
            
            # Convert snake_case to camelCase for frontend
            formatted_profile = {
                'email': profile_dict.get('email'),
                'displayName': profile_dict.get('display_name'),
                'photoUrl': profile_dict.get('photo_url'),
                'emailSubject': profile_dict.get('email_subject') or '',
                'emailContent': profile_dict.get('email_content') or '',
                'searchRole': profile_dict.get('search_role') or '',
                'searchTimePeriod': profile_dict.get('search_time_period') or 'past-week',
                'resumeFilename': profile_dict.get('resume_filename') or '',
                'resumeSize': profile_dict.get('resume_size', 0),
                'hasResume': profile_dict.get('has_resume', False),
                'createdAt': profile_dict.get('created_at'),
                'updatedAt': profile_dict.get('updated_at')
            }
            
            print(f"📤 Sending profile data: subject={formatted_profile['emailSubject'][:30] if formatted_profile['emailSubject'] else 'None'}..., role={formatted_profile['searchRole']}, resume={formatted_profile['resumeFilename']}")
            
            return jsonify(formatted_profile)
        return jsonify({})
    except Exception as e:
        print(f"Error getting profile: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Database collection names (for reference only)
# All data is now stored in SQLite tables:
# - user_profiles: User profile data
# - job_posts: Unique job posts
# - sent_emails: Email history  
# - automation_runs: Automation run data
# - subscriptions: User subscriptions

def get_user_preferences(user_email):
    """Get user preferences from SQLite.
    
    Returns user profile data which includes preferences.
    """
    try:
        profile = db.get_profile(user_email)
        if profile:
            # Return profile data as preferences
            return {
                'defaultSubject': profile.get('email_subject') or '',
                'defaultTemplate': profile.get('email_content') or '',
                'searchRole': profile.get('search_role') or '',
                'searchTimePeriod': profile.get('search_time_period') or 'past-week',
                'resumeFilename': profile.get('resume_filename') or '',
                'lastUpdated': profile.get('updated_at') or ''
            }
        return {}
    except Exception as e:
        print(f"Error getting user preferences: {str(e)}")
    return {}

def save_user_preferences(user_email, preferences):
    """Save user preferences to SQLite."""
    try:
        # Update user profile with preferences
        db.create_or_update_profile(
            email=user_email,
            display_name=preferences.get('displayName'),
            photo_url=preferences.get('photoUrl')
        )
        return True
    except Exception as e:
        print(f"Error saving user preferences: {str(e)}")
    return False

def save_automation_run(run_id, user_email, settings=None):
    """Save automation run data to SQLite.
    
    Args:
        run_id: Unique identifier for the automation run
        user_email: Email of the user who initiated the run
        settings: Dictionary of settings used for this run
    """
    try:
        run_data = {
            'job_title': settings.get('searchRole', '') if settings else '',
            'location': '',
            'keywords': settings.get('searchRole', '') if settings else '',
            'status': 'running',
            'total_jobs_found': 0,
            'emails_sent': 0
        }
        db.save_automation_run(user_email, run_data)
        return True
    except Exception as e:
        print(f"Error saving automation run: {str(e)}")
    return False

def update_automation_run(run_id, stats):
    """Update automation run statistics in SQLite."""
    try:
        # Note: SQLite automation runs are tracked per-email save
        # This function is kept for compatibility but doesn't need to do much
        return True
    except Exception as e:
        print(f"Error updating automation run: {str(e)}")
    return False

@app.route("/save_profile", methods=["POST"])
@login_required
def save_profile():
    """Save user profile data to SQLite."""
    user_email = session.get("user")
    activity_logger.info(f"💾 Profile update | User: {user_email}")
    
    # Get form data
    email_subject = request.form.get("emailSubject")
    email_content = request.form.get("emailContent")
    search_role = request.form.get("searchRole", "")
    search_time_period = request.form.get("searchTimePeriod", "past-week")
    user_name = request.form.get("userName", "")
    user_phone = request.form.get("userPhone", "")
    
    # Handle resume file - store as BLOB in database
    resume_data = None
    resume_filename = None
    if "resumeFile" in request.files:
        resume = request.files["resumeFile"]
        if resume.filename:
            # Read file as binary data
            resume_data = resume.read()
            resume_filename = resume.filename
            
            print(f"[INFO] Resume uploaded: {resume_filename}")
            print(f"   Size: {len(resume_data)} bytes")
            print(f"   Type: {resume.content_type}")
    
    try:
        # Update user profile in SQLite with all form data
        db.create_or_update_profile(
            email=user_email,
            display_name=None,  # Keep existing
            photo_url=None,  # Keep existing
            email_subject=email_subject,
            email_content=email_content,
            search_role=search_role,
            search_time_period=search_time_period,
            resume_data=resume_data,  # Store binary BLOB
            resume_filename=resume_filename,
            user_name=user_name,
            user_phone=user_phone
        )
        
        print(f"[OK] Profile updated for {user_email}")
        print(f"   - Email Subject: {email_subject[:50] if email_subject else 'None'}...")
        print(f"   - Search Role: {search_role}")
        print(f"   - Resume: {resume_filename if resume_filename else 'None'}")
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"[ERROR] Error saving profile: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/")
def landing():
    """Public landing page showcasing the platform."""
    # If user is already logged in, redirect to dashboard
    if "user" in session:
        return redirect(url_for("home"))
    return render_template("landing.html")

# --- STATIC PAGES ---
@app.route("/about")
def about():
    """About Us page"""
    return render_template("about.html")

@app.route("/careers")
def careers():
    """Careers page"""
    return render_template("careers.html")

@app.route("/blog")
def blog():
    """Blog page"""
    return render_template("blog.html")

@app.route("/blog/priya-success-story")
def blog_priya_success_story():
    """Priya's Success Story"""
    return render_template("blog_priya_success_story.html")

@app.route("/blog/rahul-success-story")
def blog_rahul_success_story():
    """Rahul's Success Story"""
    return render_template("blog_rahul_success_story.html")

@app.route("/blog/email-subject-lines")
def blog_email_subject_lines():
    """Email Subject Lines Guide"""
    return render_template("blog_email_subject_lines.html")

@app.route("/blog/email-personalization-guide")
def blog_email_personalization_guide():
    """Email Personalization Guide"""
    return render_template("blog_email_personalization_guide.html")

@app.route("/blog/best-time-to-send")
def blog_best_time_to_send():
    """Best Time to Send Emails"""
    return render_template("blog_best_time_to_send.html")

@app.route("/blog/avoiding-spam-filters")
def blog_avoiding_spam_filters():
    """Avoiding Spam Filters Guide"""
    return render_template("blog_avoiding_spam_filters.html")

@app.route("/blog/post")
def blog_post():
    """Generic Blog Post"""
    return render_template("blog_post.html",
        title="Sample Blog Post",
        category="Guide",
        date="Nov 29, 2025",
        read_time="5 min read",
        author="JustMailIt Team",
        author_bio="Helping job seekers land their dream jobs with smart automation."
    )

@app.route("/contact")
def contact():
    """Contact page"""
    return render_template("contact.html")

@app.route("/api/contact", methods=['POST'])
def api_contact():
    """Handle contact form submissions"""
    try:
        # Get form data (supports both JSON and form-data)
        if request.is_json:
            data = request.get_json()
            first_name = data.get('firstName', '')
            last_name = data.get('lastName', '')
            email = data.get('email', '')
            subject = data.get('subject', '')
            message = data.get('message', '')
        else:
            first_name = request.form.get('firstName', '')
            last_name = request.form.get('lastName', '')
            email = request.form.get('email', '')
            subject = request.form.get('subject', '')
            message = request.form.get('message', '')
        
        # Validate required fields
        if not all([first_name, last_name, email, subject, message]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        # Validate email format
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            return jsonify({'success': False, 'message': 'Invalid email address'}), 400
        
        # Log the contact request
        logger.info(f"Contact form submission from {first_name} {last_name} ({email}): {subject}")
        
        # Send notification email to admin
        try:
            admin_email = "mail@justmailit.in"
            email_subject = f"[Contact Form] {subject}"
            email_body = f"""
New contact form submission:

Name: {first_name} {last_name}
Email: {email}
Subject: {subject}

Message:
{message}

---
Sent from JustMailIt Contact Form
            """
            
            send_email(admin_email, email_subject, email_body)
            logger.info(f"Contact form notification sent to {admin_email}")
        except Exception as e:
            logger.error(f"Failed to send contact form notification: {str(e)}")
            # Don't fail the request if email fails
        
        return jsonify({
            'success': True,
            'message': 'Thank you for contacting us! We\'ll respond within 24 hours.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing contact form: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again or email us directly at mail@justmailit.in'
        }), 500

@app.route("/documentation")
def documentation():
    """Documentation page"""
    return render_template("documentation.html")

@app.route("/help")
def help_center():
    """Help Center page"""
    return render_template("help.html")

@app.route("/api")
def api_reference():
    """API Reference page"""
    return render_template("api.html")

@app.route("/community")
def community():
    """Community page"""
    return render_template("community.html")

@app.route("/privacy")
def privacy():
    """Privacy Policy page"""
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    """Terms of Service page"""
    return render_template("terms.html")

@app.route("/cookies")
def cookies():
    """Cookie Policy page"""
    return render_template("cookies.html")

@app.route("/gdpr")
def gdpr():
    """GDPR Compliance page"""
    return render_template("gdpr.html")

@app.route("/sitemap.xml")
def sitemap():
    """Generate dynamic XML sitemap for SEO"""
    from datetime import datetime
    from flask import make_response
    
    # Get current date in W3C format
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Define all public pages with their metadata
    pages = [
        {'loc': '/', 'priority': '1.0', 'changefreq': 'daily'},
        {'loc': '/pricing', 'priority': '0.9', 'changefreq': 'weekly'},
        {'loc': '/login', 'priority': '0.8', 'changefreq': 'monthly'},
        {'loc': '/signup', 'priority': '0.8', 'changefreq': 'monthly'},
        {'loc': '/about', 'priority': '0.7', 'changefreq': 'monthly'},
        {'loc': '/blog', 'priority': '0.7', 'changefreq': 'weekly'},
        {'loc': '/contact', 'priority': '0.6', 'changefreq': 'monthly'},
        {'loc': '/documentation', 'priority': '0.6', 'changefreq': 'weekly'},
        {'loc': '/help', 'priority': '0.6', 'changefreq': 'monthly'},
        {'loc': '/privacy', 'priority': '0.5', 'changefreq': 'yearly'},
        {'loc': '/terms', 'priority': '0.5', 'changefreq': 'yearly'},
        {'loc': '/careers', 'priority': '0.5', 'changefreq': 'monthly'},
    ]
    
    # Build XML sitemap
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for page in pages:
        xml += '  <url>\n'
        xml += f'    <loc>https://justmailit.in{page["loc"]}</loc>\n'
        xml += f'    <lastmod>{today}</lastmod>\n'
        xml += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
        xml += f'    <priority>{page["priority"]}</priority>\n'
        xml += '  </url>\n'
    
    xml += '</urlset>'
    
    # Return XML response with proper content type
    response = make_response(xml)
    response.headers['Content-Type'] = 'application/xml'
    return response

@app.route("/dashboard")
@login_required
def home():
    """Home dashboard after login with links to the main features."""
    user_email = session["user"]
    activity_logger.info(f"📊 Dashboard accessed | User: {user_email}")
    
    # Get user's email stats from SQLite
    sent_emails, stats = get_user_email_stats(user_email)
    
    if sent_emails is None:
        # Fallback to local storage if SQLite query failed
        print("[WARN] Falling back to local storage")
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
    
    # Get user profile data from SQLite
    try:
        profile_data = db.get_profile(user_email) or {}
    except Exception:
        profile_data = {}
    
    # Get recent activity
    recent_runs = []
    if sent_emails:
        # Group by run_id and get the most recent 5 runs
        runs = {}
        for email in sorted(sent_emails, key=lambda x: x.get('run_time') or '', reverse=True):
            run_id = email.get('run_id', 'unknown')
            if run_id not in runs:
                runs[run_id] = {
                    'run_id': run_id,
                    'run_time': email.get('run_time') or '',
                    'emails_sent': sum(1 for e in sent_emails if e.get('run_id') == run_id and e.get('status') == 'sent'),
                    'total_emails': sum(1 for e in sent_emails if e.get('run_id') == run_id)
                }
            if len(runs) >= 5:
                break
        recent_runs = list(runs.values())
    
    # Get job posts stats from SQLite
    total_jobs = 0
    try:
        job_stats = db.get_job_stats(user_email)
        total_jobs = job_stats.get('total_jobs', 0)
    except Exception as e:
        print(f"Error loading job stats: {e}")
    
    # Calculate remaining jobs (jobs not yet emailed)
    sent_count = stats.get('sent', 0)
    remaining = max(0, total_jobs - sent_count)
    
    # Add job stats to stats dict
    stats['total_jobs'] = total_jobs
    stats['remaining'] = remaining
    
    # Get today's email count for free users
    emails_today, _ = count_emails_sent_today(user_email)
    stats['emails_today'] = emails_today
    
    # Get subscription data from SQLite
    subscription = db.get_subscription(user_email)
    
    # Get recent job posts for carousel (limit to 12 + 1 for show more)
    job_posts = []
    try:
        job_posts = db.get_job_posts(user_email, limit=12)
        print(f"[OK] Loaded {len(job_posts)} job posts for user {user_email}")
        if job_posts:
            print(f"[PLAN] First job post: {job_posts[0].get('title', 'No title')}")
    except Exception as e:
        print(f"[ERROR] Error loading job posts: {e}")
        import traceback
        traceback.print_exc()
    
    # Get list of emails already sent by this user from SQLite
    sent_emails = set()
    try:
        emails = db.get_sent_emails(user_email)
        for email_record in emails:
            if email_record.get('status') == 'sent' and email_record.get('recipient_email'):
                sent_emails.add(email_record['recipient_email'])
        print(f"[EMAIL] User {user_email} has sent to {len(sent_emails)} unique emails")
    except Exception as e:
        print(f"[WARN] Error loading sent emails: {str(e)}")
    
    # Mark posts that were already sent and extract company from email
    for post in job_posts:
        # Map recruiter_email to email for template compatibility
        if 'recruiter_email' in post and not post.get('email'):
            post['email'] = post['recruiter_email']
        
        # Check if already sent
        email = post.get('email') or post.get('recruiter_email', '')
        if email in sent_emails:
            post['already_sent'] = True
        else:
            post['already_sent'] = False
        
        # Extract company name from email if not present
        if not post.get('company') or post.get('company') in ['Company Not Found', 'Company Not Specified', '']:
            if email and '@' in email:
                post['company'] = extract_company_from_email(email)
    
    print(f"[COUNT] Dashboard stats for {user_email}:")
    print(f"   Total Jobs: {stats.get('total_jobs', 0)}")
    print(f"   Job Posts Array Length: {len(job_posts)}")
    print(f"   Already Sent Count: {sum(1 for p in job_posts if p.get('already_sent'))}")
    
    return render_template(
        "home.html",
        user=user_email,
        stats=stats,
        profile=profile_data,
        subscription=subscription,
        recent_runs=recent_runs,
        job_posts=job_posts
    )


@app.route("/send")
@login_required
def send_page():
    """Email sending UI (previously the root index)."""
    return render_template("index_live.html", user=session["user"])

@app.route("/email_templates")
@login_required
def email_templates_page():
    """Email templates education page"""
    return render_template("email_templates.html", user=session["user"])

# --- JOB POSTS PAGE ---
@app.route("/jobs")
@login_required
def job_posts():
    user_email = session.get("user")
    posts = load_job_posts()
    
    # Get list of emails already sent by this user from SQLite
    sent_emails = set()
    try:
        emails = db.get_sent_emails(user_email)
        for email_record in emails:
            if email_record.get('status') == 'sent' and email_record.get('recipient_email'):
                sent_emails.add(email_record['recipient_email'])
        
        print(f"[EMAIL] User {user_email} has sent to {len(sent_emails)} unique emails")
    except Exception as e:
        print(f"[WARN] Error loading sent emails: {str(e)}")
    
    # Mark posts that were already sent and extract company from email
    for post in posts:
        # Map recruiter_email to email for template compatibility
        if 'recruiter_email' in post and not post.get('email'):
            post['email'] = post['recruiter_email']
        
        # Check if already sent
        email = post.get('email') or post.get('recruiter_email', '')
        if email in sent_emails:
            post['already_sent'] = True
        else:
            post['already_sent'] = False
        
        # Extract company name from email if not present - use helper function
        if not post.get('company') or post.get('company') in ['Company Not Found', 'Company Not Specified', '']:
            if email and '@' in email:
                # Use our helper function for extraction
                post['company'] = extract_company_from_email(email)
    
    # Sort posts by date, newest first
    posts.sort(key=lambda x: x["posted_date"], reverse=True)
    
    # Check if user is admin
    is_admin = (user_email == ADMIN_EMAIL)
    
    # Pass current date as formatted string to template
    from datetime import datetime
    current_date = datetime.now().strftime('%b %d, %Y')
    return render_template("job_posts.html", job_posts=posts, current_date=current_date, is_admin=is_admin)


@app.route("/send_job_email", methods=["POST"])
@login_required
def send_job_email():
    """Send email to a specific job post email."""
    try:
        user_email = session.get("user")
        job_email = request.json.get("email")
        job_description = request.json.get("description", "")
        job_company = request.json.get("company", "")
        job_url = request.json.get("url", "")
        
        print(f"🔔 /send_job_email called by user: {user_email}")
        print(f"   Target email: {job_email}")
        
        if not job_email:
            return jsonify({"success": False, "message": "No email address provided"}), 400
        
        # CHECK DAILY EMAIL LIMIT
        can_send, emails_sent, limit_message = check_email_limit(user_email)
        if not can_send:
            print(f"[STOP] Blocking send - limit reached!")
            return jsonify({
                "success": False, 
                "message": limit_message,
                "limit_reached": True,
                "upgrade_url": "/pricing"
            }), 403
        
        print(f"[OK] Email limit check passed. Sent today: {emails_sent}/10")
        
        # Get user's saved profile data from SQLite
        try:
            profile_data = db.get_profile(user_email)
            if not profile_data:
                return jsonify({"success": False, "message": "Please set up your profile first"}), 400
            
            # Get email content and subject from profile
            email_content = profile_data.get('email_content', '')
            subject = profile_data.get('email_subject', 'Job Application')
            
            # Check if resume exists - use correct field names with underscores
            resume_data_b64 = profile_data.get('resume_data')
            resume_filename = profile_data.get('resume_filename')
            
            if not resume_data_b64 or not resume_filename:
                return jsonify({"success": False, "message": "Please upload a resume first"}), 400
            
            # Decode resume from base64 and create temp file
            resume_bytes = base64.b64decode(resume_data_b64)
            
            temp_dir = tempfile.gettempdir()
            resume_path = os.path.join(temp_dir, f"{user_email}_{resume_filename}")
            
            with open(resume_path, 'wb') as f:
                f.write(resume_bytes)
            
            print(f"[EMAIL] Sending email to {job_email} for {job_company}")
            
        except Exception as e:
            print(f"[ERROR] Error getting profile data: {str(e)}")
            return jsonify({"success": False, "message": "Error loading profile data"}), 500
        
        # Check for duplicate using SQLite
        try:
            emails = db.get_sent_emails(user_email)
            for email_record in emails:
                if (email_record.get('recipient_email') == job_email and
                    email_record.get('subject') == subject):
                    last_sent = email_record.get('sent_at', 'unknown time')
                    return jsonify({
                        "success": False, 
                        "message": f"Already sent to this email on {last_sent}"
                    }), 400
        except Exception as e:
            print(f"[WARN] Error checking duplicates: {str(e)}")
        
        # Send the email - using mail@justmailit.in via Gmail SMTP
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "mail@justmailit.in"  # Custom domain email
        smtp_user = "manudrive06@gmail.com"  # Gmail account for authentication
        sender_password = "ozds nrqo gduy mnwd"  # Gmail App Password
        
        try:
            msg = MIMEMultipart()
            msg["From"] = sender_email  # mail@justmailit.in
            msg["To"] = job_email
            msg["Bcc"] = user_email  # Send copy to user (hidden from recruiter)
            msg["Reply-To"] = user_email  # Replies go to user
            msg["Subject"] = subject
            
            # Attach email content
            msg.attach(MIMEText(email_content, "plain", "utf-8"))
            
            # Attach resume
            if resume_path and os.path.exists(resume_path):
                with open(resume_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(resume_path)}"
                    )
                    msg.attach(part)
            
            # Send email - authenticate with Gmail, send as mail@justmailit.in
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_user, sender_password)  # Authenticate with Gmail
            # Send to recruiter AND user (BCC - user gets copy for tracking)
            recipients = [job_email, user_email]  # Both receive the email
            server.sendmail(sender_email, recipients, msg.as_string())
            server.quit()
            
            print(f"[OK] Email sent successfully to {job_email} from {sender_email} (copy sent to user: {user_email})")
            
            # Save to sent emails with proper record format
            run_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            save_sent_email({
                "email": job_email,
                "recipient_email": job_email,
                "subject": subject,
                "reply_to": user_email,  # User gets replies
                "sent_at": datetime.now().isoformat(),
                "status": "sent",
                "source_url": job_url,
                "company": job_company,
                "job_title": job_description[:50] + "..." if len(job_description) > 50 else job_description,
                "description": job_description[:100] + "..." if len(job_description) > 100 else job_description
            }, run_id, user_email)
            
            # Clean up temp file
            try:
                if resume_path and os.path.exists(resume_path):
                    os.remove(resume_path)
            except:
                pass
            
            return jsonify({
                "success": True, 
                "message": f"Email sent successfully to {job_email}"
            })
            
        except Exception as e:
            print(f"[ERROR] Error sending email: {str(e)}")
            
            # Save failure with proper record format
            run_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            save_sent_email({
                "email": job_email,
                "recipient_email": job_email,
                "subject": subject,
                "reply_to": user_email,
                "sent_at": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e),
                "source_url": job_url,
                "company": job_company
            }, run_id, user_email)
            
            return jsonify({
                "success": False, 
                "message": f"Failed to send email: {str(e)}"
            }), 500
            
    except Exception as e:
        print(f"[ERROR] Error in send_job_email: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/sent_emails")
@login_required
def sent_emails_page():
    """Render a page listing all sent emails grouped by automation runs for the current user."""
    user_email = session["user"]
    
    # Get records using the efficient query helper
    records, stats = get_user_email_stats(user_email)
    
    if records is None:
        records = load_sent_emails(user_email)
        print(f"[FOLDER] Loaded {len(records)} emails from local storage")
    
    # Group emails by run_id with enhanced stats
    runs = {}
    for record in records:
        run_id = record.get('run_id', 'unknown')
        run_time = record.get('run_time') or record.get('sent_at') or ''
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
    
    # Convert to list and sort by run_time (handle None values)
    runs_list = list(runs.values())
    runs_list.sort(key=lambda x: x.get('run_time') or '', reverse=True)
    
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
        print(f"[ERROR] Error in /api/sent_email_stats: {e}")
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

@app.route('/submit_2fa_code', methods=['POST'])
@login_required
def submit_2fa_code():
    """Endpoint to submit 2FA verification code."""
    global verification_code_submitted, verification_code_value, automation_driver
    
    code = request.json.get('code', '').strip()
    
    if not code:
        return jsonify({"status": "error", "message": "Code is required"}), 400
    
    if automation_driver is None:
        return jsonify({"status": "error", "message": "No active automation session"}), 400
    
    try:
        log(f"📱 Received 2FA code from user: {code}")
        verification_code_value = code
        verification_code_submitted = True
        
        return jsonify({
            "status": "success", 
            "message": "Code submitted successfully. Automation will continue..."
        })
    except Exception as e:
        log(f"[ERROR] Error submitting 2FA code: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/generate_email_template', methods=['POST'])
@login_required
def generate_email_template():
    """Generate email subject and body based on uploaded resume and role"""
    try:
        role = request.form.get('role', 'Software Developer')
        user_email = session.get('user')
        
        # Check if resume file is uploaded or use saved resume
        resume_info = None
        resume_path = None
        
        # First check for new upload
        if 'resume' in request.files and request.files['resume'].filename:
            # New resume uploaded - save it
            resume_file = request.files['resume']
            user_folder = os.path.join('uploads', user_email.replace('@', '_at_').replace('.', '_'))
            os.makedirs(user_folder, exist_ok=True)
            
            # Save the resume
            resume_filename = f"resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            resume_path = os.path.join(user_folder, resume_filename)
            resume_file.save(resume_path)
            
            # Also save to profile
            db.create_or_update_profile(user_email, resume_filename=resume_filename)
            
            print(f"[OK] Resume saved: {resume_path}")
        else:
            # Try to use saved resume
            user_folder = os.path.join('uploads', user_email.replace('@', '_at_').replace('.', '_'))
            if os.path.exists(user_folder):
                resume_files = [f for f in os.listdir(user_folder) if f.endswith('.pdf')]
                if resume_files:
                    # Use most recent resume
                    resume_files.sort(reverse=True)
                    resume_path = os.path.join(user_folder, resume_files[0])
                    print(f"[INFO] Using saved resume: {resume_path}")
        
        # If no resume found, return error
        if not resume_path or not os.path.exists(resume_path):
            return jsonify({
                'status': 'error',
                'error_type': 'no_resume',
                'message': 'Please upload your resume to generate a personalized email template.'
            }), 400
        
        # Extract resume info
        resume_info = extract_resume_info(resume_path)
        print(f"[PLAN] Resume Info Extracted: {resume_info}")
        
        # Generate templates
        templates = generate_email_templates(role, resume_info)
        print(f"[EMAIL] Templates Generated: Subjects={templates['subjects']}, Has Contact={templates['has_contact']}")
        
        return jsonify({
            'status': 'success',
            'subjects': templates['subjects'],
            'body': templates['body'],
            'name': templates['name'],
            'email': resume_info.get('email', ''),
            'phone': resume_info.get('phone', ''),
            'skills': resume_info.get('skills', []),
            'position': resume_info.get('position', '') or role,  # Use extracted position or fallback to role
            'has_contact': templates['has_contact']
        })
    
    except Exception as e:
        print(f"[ERROR] Error generating template: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/progress')
@login_required
def progress_stream():
    """Server-Sent Events endpoint that streams log messages to the client."""
    print("[CONN] Progress stream connection established")
    
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
                    # Don't print here to avoid duplication - message already logged via log()
                    yield f"data: {msg}\n\n"
                except Empty:
                    # heartbeat to keep connection alive
                    print("[BEAT] Sending heartbeat")
                    yield "data: \n\n"
        except GeneratorExit:
            # Client disconnected
            print("[CONN] Client disconnected")
            with clients_lock:
                try:
                    clients.remove(q)
                    print(f"👥 Remaining clients: {len(clients)}")
                except ValueError:
                    print("[ERROR] Client queue not found")

    return Response(event_stream(), mimetype='text/event-stream')


def linkedin_login(driver, email, password):
    """Log into LinkedIn using email and password."""
    try:
        log("[LOAD] Attempting LinkedIn login...")
        
        # Navigate to LinkedIn login page
        driver.get("https://www.linkedin.com/login")
        time.sleep(3)
        
        # Wait for login form to load
        wait = WebDriverWait(driver, 10)
        
        # Find email field
        email_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        email_field.clear()
        email_field.send_keys(email)
        log("[EMAIL] Email entered")
        
        # Find password field
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys(password)
        log("[LOGIN] Password entered")
        
        # Click sign in button
        sign_in_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        sign_in_button.click()
        log("[*] Sign in button clicked")
        
        # Wait for login to complete - check for feed or home page
        time.sleep(5)
        
        # Check if login was successful
        current_url = driver.current_url
        if "feed" in current_url or "home" in current_url or "mynetwork" in current_url:
            log("[OK] LinkedIn login successful!")
            return True
        elif "checkpoint" in current_url or "challenge" in current_url:
            log("=" * 70)
            log("[WARN] LinkedIn requires additional verification (2FA/challenge)")
            log(f"� Current URL: {current_url}")
            log("=" * 70)
            
            # Save screenshot for debugging
            try:
                screenshot_path = "/tmp/linkedin_2fa_challenge.png"
                driver.save_screenshot(screenshot_path)
                log(f"📸 Screenshot saved: {screenshot_path}")
            except Exception as ss_error:
                log(f"[WARN] Could not save screenshot: {str(ss_error)}")
            
            # Save page HTML
            try:
                html_path = "/tmp/linkedin_2fa_challenge.html"
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                log(f"[INFO] Page HTML saved: {html_path}")
            except Exception as html_error:
                log(f"[WARN] Could not save HTML: {str(html_error)}")
            
            log("�[DEBUG] Waiting for 2FA verification code...")
            
            # Wait for verification code input field
            try:
                # Try to find the verification code input field
                code_input = None
                input_selectors = [
                    "#input__email_verification_pin",
                    "#input__phone_verification_pin", 
                    "input[name='pin']",
                    "input[autocomplete='one-time-code']",
                    "input[id*='verification']",
                    "input[id*='pin']"
                ]
                
                for selector in input_selectors:
                    try:
                        code_input = driver.find_element(By.CSS_SELECTOR, selector)
                        if code_input and code_input.is_displayed():
                            log(f"[OK] Found verification input field: {selector}")
                            break
                    except:
                        continue
                
                if code_input:
                    global verification_code_submitted, verification_code_value
                    
                    log("📱 2FA code input field detected")
                    log("=" * 70)
                    log("[LOAD] ENTER YOUR 2FA CODE VIA WEB INTERFACE:")
                    log("   1. Check your email/phone for LinkedIn verification code")
                    log("   2. A modal will appear on the web page")
                    log("   3. Enter your 6-digit code in the input field")
                    log("   4. Click 'Submit Code' button")
                    log("   5. Automation will enter the code and continue")
                    log("[WAIT] Waiting for code submission (max 5 minutes)...")
                    log("=" * 70)
                    
                    # Reset verification state
                    verification_code_submitted = False
                    verification_code_value = None
                    
                    # Wait for user to submit code via web interface
                    timeout = 300  # 5 minutes
                    elapsed = 0
                    while elapsed < timeout and not verification_code_submitted:
                        time.sleep(1)
                        elapsed += 1
                        if elapsed % 15 == 0:
                            log(f"[WAIT] Still waiting for 2FA code... ({elapsed}s elapsed)")
                    
                    if verification_code_submitted and verification_code_value:
                        log(f"[OK] Received code, entering it now...")
                        
                        # Enter the code
                        code_input.clear()
                        code_input.send_keys(verification_code_value)
                        log("[OK] Code entered into LinkedIn form")
                        time.sleep(1)
                        
                        # Find and click submit button
                        from selenium.webdriver.common.keys import Keys
                        submit_button = None
                        button_selectors = [
                            "button[type='submit']",
                            "button[data-litms-control-urn*='verify']",
                            "button[aria-label*='Submit']",
                            ".primary-action-button",
                            "button.btn__primary--large"
                        ]
                        
                        for btn_selector in button_selectors:
                            try:
                                submit_button = driver.find_element(By.CSS_SELECTOR, btn_selector)
                                if submit_button and submit_button.is_displayed():
                                    submit_button.click()
                                    log(f"[OK] Submit button clicked")
                                    break
                            except:
                                continue
                        
                        if not submit_button:
                            log("[WARN] Could not find submit button, using Enter key...")
                            code_input.send_keys(Keys.RETURN)
                        
                        # Wait for redirect
                        log("[WAIT] Waiting for LinkedIn to verify...")
                        time.sleep(3)
                        wait = WebDriverWait(driver, 30)
                        try:
                            wait.until(lambda d: "feed" in d.current_url or "home" in d.current_url or "mynetwork" in d.current_url)
                            log("=" * 70)
                            log("[OK] Verification completed successfully!")
                            log(f"[OK] Redirected to: {driver.current_url}")
                            log("=" * 70)
                            return True
                        except:
                            log("[ERROR] Verification may have failed - check code")
                            return False
                    else:
                        log("⏰ Timeout waiting for 2FA code")
                        return False
                else:
                    log("[WARN] Could not find verification input field")
                    log("=" * 70)
                    log("[WAIT] WAITING FOR MANUAL VERIFICATION:")
                    log("   1. Complete the verification challenge on LinkedIn")
                    log("   2. You should be redirected to feed/home")
                    log("   3. Automation will detect completion and resume")
                    log("[WAIT] Maximum wait time: 5 minutes")
                    log("=" * 70)
                    
                    # Wait for URL to change to feed/home (verification completed)
                    wait = WebDriverWait(driver, 300)  # 5 minutes
                    wait.until(lambda d: "feed" in d.current_url or "home" in d.current_url or "mynetwork" in d.current_url)
                    
                    log("=" * 70)
                    log("[OK] Verification completed!")
                    log(f"[OK] Redirected to: {driver.current_url}")
                    log("=" * 70)
                    return True
                    
            except Exception as verification_error:
                log("=" * 70)
                log(f"⏰ Verification timeout or error: {str(verification_error)}")
                log(f"⏰ Current URL after timeout: {driver.current_url}")
                log("[WARN] Please check LinkedIn and try again")
                log("=" * 70)
                return False
        else:
            log("[ERROR] LinkedIn login failed - checking for error messages")
            try:
                error_element = driver.find_element(By.CLASS_NAME, "alert-error")
                log(f"[ERROR] Login error: {error_element.text}")
            except:
                log("[ERROR] Login failed - unknown error")
            return False
            
    except Exception as e:
        log(f"[ERROR] Error during LinkedIn login: {str(e)}")
        return False


def send_emails_from_existing_jobs(subject, email_content, attachment_path, cc_email, run_id, user_email, search_role, limit=10):
    """
    Send emails to existing job posts from database without LinkedIn scraping.
    Used when another automation is already running.
    """
    import time
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    
    global automation_sessions
    
    log("=" * 80)
    log("🔄 QUICK SEND MODE ACTIVATED")
    log("=" * 80)
    log(f"[INFO] User: {user_email}")
    log(f"[INFO] Reason: Another user is currently scraping LinkedIn")
    log(f"[INFO] Solution: Sending emails from existing job database")
    log(f"[INFO] Search Role: {search_role}")
    log(f"[INFO] This is FASTER and prevents Chrome/browser conflicts!")
    log("=" * 80)
    
    send_event("🔄 <strong>Quick Send Mode</strong> - Another user is scraping, using existing jobs")
    send_event(f"📋 Searching database for <strong>{search_role}</strong> positions...")
    
    emails_sent_count = 0
    
    try:
        # Get user's email limit
        can_send, today_count, limit_msg = check_email_limit(user_email)
        remaining = 10 - today_count
        actual_limit = min(limit, remaining)
        
        log(f"[LIMIT] Can send up to {actual_limit} emails (limit={limit}, already sent today={today_count})")
        
        if actual_limit <= 0:
            log("[LIMIT] Daily email limit reached")
            send_event(f"[LIMIT] Daily email limit reached. Please upgrade or try again tomorrow.")
            return {"status": "limit_reached", "emails_sent": 0}
        
        # Get existing job posts from database matching user's search role
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Parse search roles
        roles = parse_skills(search_role) if search_role else []
        
        if roles:
            # Build SQL query with OR conditions for each role
            role_conditions = " OR ".join(["LOWER(title) LIKE ? OR LOWER(description) LIKE ?" for _ in roles])
            role_params = []
            for role in roles:
                role_lower = f"%{role.lower()}%"
                role_params.extend([role_lower, role_lower])
            
            query = f"""
                SELECT DISTINCT email, company, title, description, source_url, location
                FROM job_posts
                WHERE email IS NOT NULL 
                AND email != ''
                AND ({role_conditions})
                AND email NOT IN (
                    SELECT DISTINCT recipient_email 
                    FROM sent_emails 
                    WHERE user_email = ? 
                    AND DATE(sent_at) = DATE('now')
                )
                ORDER BY created_at DESC
                LIMIT ?
            """
            
            cursor.execute(query, role_params + [user_email, actual_limit])
        else:
            # No specific role, get any recent jobs
            query = """
                SELECT DISTINCT email, company, title, description, source_url, location
                FROM job_posts
                WHERE email IS NOT NULL 
                AND email != ''
                AND email NOT IN (
                    SELECT DISTINCT recipient_email 
                    FROM sent_emails 
                    WHERE user_email = ? 
                    AND DATE(sent_at) = DATE('now')
                )
                ORDER BY created_at DESC
                LIMIT ?
            """
            cursor.execute(query, [user_email, actual_limit])
        
        jobs = cursor.fetchall()
        conn.close()
        
        log(f"[DB] Found {len(jobs)} matching jobs to send emails to")
        
        if not jobs:
            send_event("[INFO] No matching job posts found in database. Please try running a full automation later.")
            return {"status": "no_jobs", "emails_sent": 0}
        
        # Send emails
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "manudrive06@gmail.com"
        sender_password = "ozds nrqo gduy mnwd"
        
        for job in jobs:
            try:
                receiver_email = job['email']
                company = job['company']
                job_title = job['title']
                
                log(f"[→] Sending to {company} ({receiver_email})...")
                send_event(f"[→] Sending to {company}...")
                
                # Personalize email content
                personalized_content = email_content.replace("{company}", company).replace("{Company}", company)
                
                # Send email
                msg = MIMEMultipart()
                msg["From"] = sender_email
                msg["To"] = receiver_email
                msg["Subject"] = subject
                
                if cc_email:
                    msg["Cc"] = cc_email
                
                msg.attach(MIMEText(personalized_content, "plain"))
                
                # Attach resume if provided
                if attachment_path and os.path.exists(attachment_path):
                    with open(attachment_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_path)}")
                        msg.attach(part)
                
                # Send via SMTP
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    recipients = [receiver_email]
                    if cc_email:
                        recipients.append(cc_email)
                    server.sendmail(sender_email, recipients, msg.as_string())
                
                emails_sent_count += 1
                log(f"[✓] Email sent to {company}")
                send_event(f"[✓] Email sent to {company}")
                
                # Save to sent_emails
                save_sent_email({
                    "email": receiver_email,
                    "recipient_email": receiver_email,
                    "subject": subject,
                    "cc": cc_email,
                    "sent_at": datetime.now().isoformat(),
                    "status": "sent",
                    "company": company,
                    "title": job_title,
                    "source_url": job.get('source_url', '')
                }, run_id, user_email)
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                log(f"[ERROR] Failed to send to {job.get('company', 'Unknown')}: {str(e)}")
                send_event(f"[ERROR] Failed to send to {job.get('company', 'Unknown')}")
        
        log(f"[OK] Sent {emails_sent_count} emails from existing job posts")
        send_event(f"[OK] Completed! Sent {emails_sent_count} emails from existing job posts.")
        
        # Send summary email to user
        try:
            if user_email and emails_sent_count > 0:
                send_automation_summary_email(user_email, emails_sent_count, search_role, mode="quick_send")
        except Exception as email_err:
            log(f"[WARN] Could not send summary email: {str(email_err)}")
        
        return {"status": "completed", "emails_sent": emails_sent_count}
        
    except Exception as e:
        log(f"[ERROR] Error in send_emails_from_existing_jobs: {str(e)}")
        import traceback
        traceback.print_exc()
        send_event(f"[ERROR] Failed to send emails: {str(e)}")
        return {"status": "error", "emails_sent": emails_sent_count, "error": str(e)}
    finally:
        # Cleanup session
        if user_email in automation_sessions:
            automation_sessions[user_email]['running'] = False
            automation_sessions[user_email]['driver'] = None
            print(f"[OK] Quick send session cleaned up for {user_email}")


# --- AUTOMATION FUNCTION ---
def run_automation(subject, email_content, attachment_path, cc_email, run_id=None, user_email=None, search_role=None, search_time=None):
    import time
    global automation_stop_flag, automation_running, automation_driver
    
    # Wrap EVERYTHING in try-catch to catch silent failures
    try:
        print("=" * 80, flush=True)
        print("[*] DEBUG: run_automation FUNCTION CALLED", flush=True)
        print(f"[*] DEBUG: Thread ID: {threading.current_thread().ident}", flush=True)
        print(f"[*] DEBUG: Thread Name: {threading.current_thread().name}", flush=True)
        print(f"[*] DEBUG: Parameters received:", flush=True)
        print(f"    - subject: {subject}", flush=True)
        print(f"    - email_content length: {len(email_content) if email_content else 0}", flush=True)
        print(f"    - attachment_path: {attachment_path}", flush=True)
        print(f"    - cc_email: {cc_email}", flush=True)
        print(f"    - run_id: {run_id}", flush=True)
        print(f"    - user_email: {user_email}", flush=True)
        print(f"    - search_role: {search_role}", flush=True)
        print(f"    - search_time: {search_time}", flush=True)
        print("=" * 80, flush=True)
    except Exception as top_error:
        print(f"[ERROR] CRITICAL: Error in function entry: {str(top_error)}", flush=True)
        import traceback
        traceback.print_exc()
        return
    
    log("[*] Starting automation...")
    log(f"📝 Run ID: {run_id}")
    if user_email:
        log(f"[@] User: {user_email}")
    # Initialize resources referenced in finally/cleanup
    driver = None
    all_emails = set()
    skipped_emails = []  # Initialize early to avoid NameError in finally block
    emails_sent_count = 0  # Initialize email counter

    try:
        print("[OK] DEBUG: Entered main try block")
        log("⚙️ Initializing automation process...")
        print("[OK] DEBUG: About to set email credentials")
        # Log initial state
        log("⚙️ Initializing automation process...")

        # Fixed email credentials
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "manudrive06@gmail.com"
        sender_password = "ozds nrqo gduy mnwd"

        # Chrome setup - always use D:\Profile directory
        options = webdriver.ChromeOptions()
        
        # Set Chrome/Chromium binary location
        if os.environ.get('CHROME_BIN'):  # Docker/Cloud environment - use Chromium
            options.binary_location = os.environ.get('CHROME_BIN', '/usr/bin/chromium')
            log(f"[DOCKER] Using Chromium binary: {options.binary_location}")
        
        # Only use headless mode if HEADLESS environment variable is not set to "false"
        if os.environ.get('HEADLESS', 'true').lower() != 'false':
            options.add_argument("--headless=new")
            log("🔇 Running Chrome in headless mode")
        else:
            log("[VISIBLE] Running Chrome in visible mode (headless disabled)")
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument("--disable-features=VizDisplayCompositor")

        # Use appropriate profile directory based on environment
        if os.environ.get('CHROME_BIN'):  # Docker/Cloud environment
            profile_dir = "/tmp/chrome-profile"
            log("[WWW] Using Docker Chrome profile directory")
        else:  # Local Windows environment
            profile_dir = r"D:\Profile"
            log("🏠 Using Windows Chrome profile directory")
        
        os.makedirs(profile_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
        log(f"🗂 Using Chrome profile directory: {profile_dir}")

        options.page_load_strategy = 'normal'
        log("[OK] Chrome options configured")
    except Exception as e:
        error_msg = f"[ERROR] Error during initialization: {str(e)}"
        log(error_msg)
        print(error_msg)
        raise
    
    from selenium.webdriver.chrome.service import Service
    
    try:
        log("=" * 60)
        log("[DEBUG] DEBUG: Starting Chrome initialization")
        log(f"[DEBUG] DEBUG: CHROME_BIN env = {os.environ.get('CHROME_BIN')}")
        log(f"[DEBUG] DEBUG: CHROMEDRIVER_PATH env = {os.environ.get('CHROMEDRIVER_PATH')}")
        log("=" * 60)
        
        # Use explicit ChromeDriver path in Docker/Cloud, auto-install locally
        if os.environ.get('CHROMEDRIVER_PATH'):
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
            log(f"[INSTALL] Using ChromeDriver from: {chromedriver_path}")
            
            # Verify ChromeDriver exists
            if os.path.exists(chromedriver_path):
                log(f"[OK] ChromeDriver file exists at {chromedriver_path}")
            else:
                log(f"[ERROR] ChromeDriver file NOT FOUND at {chromedriver_path}")
                raise FileNotFoundError(f"ChromeDriver not found at {chromedriver_path}")
            
            service = Service(chromedriver_path)
            log("[OK] Service object created")
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            log("🔄 Installing ChromeDriver via webdriver_manager...")
            service = Service(ChromeDriverManager().install())
            log("[OK] ChromeDriver installed via webdriver_manager")
        
        log("[*] DEBUG: About to launch Chrome browser...")
        log(f"[*] DEBUG: Chrome binary location from options: {options.binary_location if hasattr(options, 'binary_location') and options.binary_location else 'Not set'}")
        
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set global driver for 2FA handling
        global automation_driver
        automation_driver = driver
        
        log("[OK] Chrome launched successfully!")
        log(f"[OK] Chrome version: {driver.capabilities.get('browserVersion', 'unknown')}")
        log(f"[OK] ChromeDriver version: {driver.capabilities.get('chrome', {}).get('chromedriverVersion', 'unknown')}")
        print("[OK] Chrome instance ready")

        # Login logic: check existing profile first, fallback to email/password
        login_successful = False

        # First, try to use existing profile
        log("=" * 60)
        log("[DEBUG] DEBUG: Starting LinkedIn login check...")
        log("[DEBUG] DEBUG: Navigating to LinkedIn feed...")
        
        try:
            driver.get("https://www.linkedin.com/feed/")
            log(f"[OK] DEBUG: Page loaded, current URL: {driver.current_url}")
            log(f"[OK] DEBUG: Page title: {driver.title}")
        except Exception as nav_error:
            log(f"[ERROR] DEBUG: Navigation error: {str(nav_error)}")
            raise
        
        log("[WAIT] DEBUG: Waiting 5 seconds for page to settle...")
        time.sleep(5)  # Increased wait time
        log(f"[OK] DEBUG: After wait, URL: {driver.current_url}")

        # Better login check: look for elements that only exist when logged in
        try:
            log("[DEBUG] DEBUG: Checking login indicators...")
            # Check for multiple indicators of being logged in
            login_indicators = [
                ".global-nav__me",  # User profile dropdown
                ".feed-identity-module",  # Feed identity section
                "[data-control-name='nav.settings_and_privacy']",  # Settings menu
                ".nav-item__profile-member-photo"  # Profile photo
            ]

            logged_in = False
            for indicator in login_indicators:
                try:
                    log(f"[DEBUG] DEBUG: Checking indicator: {indicator}")
                    elements = driver.find_elements(By.CSS_SELECTOR, indicator)
                    log(f"[DEBUG] DEBUG: Found {len(elements)} elements for {indicator}")
                    if elements:
                        logged_in = True
                        log(f"[OK] DEBUG: Login confirmed via indicator: {indicator}")
                        break
                except Exception as ind_error:
                    log(f"[WARN] DEBUG: Error checking {indicator}: {str(ind_error)}")
                    continue

            # Also check URL - if redirected to login page, definitely not logged in
            current_url = driver.current_url
            log(f"[DEBUG] DEBUG: Final URL check: {current_url}")
            
            if "login" in current_url or "authwall" in current_url:
                logged_in = False
                log("[WARN] Redirected to login page - not logged in")
            elif logged_in:
                log("[OK] Existing profile login successful!")
                login_successful = True
            else:
                log("[WARN] Could not find login indicators, profile may not be logged in")
                log(f"[DEBUG] DEBUG: Page source length: {len(driver.page_source)}")
                # Save page source for debugging
                try:
                    with open('/tmp/linkedin_debug.html', 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    log("[INFO] DEBUG: Page source saved to /tmp/linkedin_debug.html")
                except:
                    pass

        except Exception as e:
            log(f"[ERROR] DEBUG: Error checking login status: {str(e)}")
            log(f"[ERROR] DEBUG: Error type: {type(e).__name__}")
            import traceback
            log(f"[ERROR] DEBUG: Traceback: {traceback.format_exc()}")
            
            # Check URL as fallback
            try:
                current_url = driver.current_url
                log(f"[DEBUG] DEBUG: Fallback URL check: {current_url}")
                if "feed" in current_url or "home" in current_url or "mynetwork" in current_url:
                    log("[OK] Existing profile login successful! (URL check)")
                    login_successful = True
                else:
                    log("[WARN] Profile not logged in (URL check failed)")
            except Exception as url_error:
                log(f"[ERROR] DEBUG: Error getting URL in fallback: {str(url_error)}")

        if not login_successful:
            log("=" * 60)
            log("[DEBUG] DEBUG: Profile not logged in, checking for email/password login...")
            log(f"[DEBUG] DEBUG: LINKEDIN_EMAIL env = {'SET' if LINKEDIN_EMAIL else 'NOT SET'}")
            log(f"[DEBUG] DEBUG: LINKEDIN_PASSWORD env = {'SET' if LINKEDIN_PASSWORD else 'NOT SET'}")
            log("=" * 60)
            log("🔄 Profile not logged in, attempting email/password login")

        if not login_successful and LINKEDIN_EMAIL and LINKEDIN_PASSWORD:
            # Use email/password login - this will save session in the same profile directory
            log("[LOAD] Attempting email/password login...")
            login_result = linkedin_login(driver, LINKEDIN_EMAIL, LINKEDIN_PASSWORD)
            if login_result:
                login_successful = True
                log("[OK] Email/password login successful - session saved to profile")
            else:
                log("[ERROR] Email/password login failed")
                
                # Send admin alert for login failure
                try:
                    _send_admin_alert(
                        user_email=user_email or "Unknown",
                        error_type="LinkedIn Login Failed",
                        error_message="Email/password login failed after profile login check",
                        additional_info={
                            "Run ID": run_id,
                            "Search Role": search_role,
                            "LinkedIn Email": LINKEDIN_EMAIL,
                            "Current URL": driver.current_url
                        }
                    )
                except Exception as alert_error:
                    log(f"[WARN] Could not send admin alert: {str(alert_error)}")

        if not login_successful:
            log("[ERROR] No login method succeeded - automation may fail")
            
            # Send admin alert for complete login failure
            try:
                _send_admin_alert(
                    user_email=user_email or "Unknown",
                    error_type="LinkedIn Login Failed - All Methods",
                    error_message="Both profile-based and email/password login methods failed",
                    additional_info={
                        "Run ID": run_id,
                        "Search Role": search_role,
                        "Profile Dir": profile_dir,
                        "LinkedIn Email": LINKEDIN_EMAIL or 'Not Set'
                    }
                )
            except Exception as alert_error:
                log(f"[WARN] Could not send admin alert: {str(alert_error)}")
        else:
            log("[OK] Proceeding with job search...")
        
        # Continue with job search...
    except Exception as e:
        error_msg = f"[ERROR] Failed to launch Chrome: {str(e)}"
        log(error_msg)
        print(error_msg)
        
        # Send admin alert for Chrome launch failure
        try:
            import traceback
            _send_admin_alert(
                user_email=user_email or "Unknown",
                error_type="Chrome Browser Launch Failed",
                error_message=str(e),
                additional_info={
                    "Run ID": run_id,
                    "Search Role": search_role,
                    "Search Time": search_time,
                    "Traceback": traceback.format_exc()
                }
            )
        except Exception as alert_error:
            log(f"[WARN] Could not send admin alert: {str(alert_error)}")
        
        raise

    try:
        # Get search parameters from function args or fallback to profile preferences
        profile_data = db.get_profile(user_email) if user_email else {}

        # Use passed-in search parameters if provided, otherwise fall back to profile preferences
        if not search_role:
            search_role = profile_data.get('searchRole', '')
        if not search_time:
            search_time = profile_data.get('searchTimePeriod', 'past-week')
        
        # Convert roles to LinkedIn search format - handle both commas and spaces
        roles = parse_skills(search_role)
        search_keywords = ' OR '.join(f'{role.strip()} hiring' for role in roles)
        
        # Build LinkedIn search URL
        base_url = "https://www.linkedin.com/search/results/content/?"
        params = {
            'datePosted': f'"{search_time}"',
            'keywords': search_keywords
        }
        
        # URL encode parameters
        from urllib.parse import urlencode
        search_url = base_url + urlencode(params)
        log(f"[DEBUG] Using search URL: {search_url}")
        
        search_urls = [search_url]
        all_emails = set()

        for url in search_urls:
            # Check stop flag
            if automation_stop_flag:
                log("[STOP!] Automation stopped by user")
                return
            
            log(f"[WWW] Opening {url}")
            driver.get(url)
            time.sleep(5)
            # Scroll with dynamic wait
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_attempts = 18
            
            while scroll_attempts < max_attempts:
                # Check stop flag
                if automation_stop_flag:
                    log("[STOP!] Automation stopped by user")
                    return
                
                # Scroll down with error handling
                try:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)  # Wait for content to load
                    
                    # Calculate new scroll height and compare with last scroll height
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        # If heights are the same, content might be fully loaded
                        break

                    last_height = new_height
                    scroll_attempts += 1
                    log(f"[SCROLL] Scrolling... ({scroll_attempts}/{max_attempts})")
                except (urllib3.exceptions.ProtocolError, http.client.RemoteDisconnected):
                    log(f"[WARN] Scroll connection error at attempt {scroll_attempts}, checking browser...")
                    try:
                        driver.current_url  # Test if browser is alive
                        log("[OK] Browser still responsive, continuing...")
                    except:
                        log("[ERROR] Browser crashed during scroll, stopping...")
                        break
                except Exception as e:
                    log(f"[WARN] Scroll error: {e}")
                    break
            
            # Add wait for job posts
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            log("[WAIT] Waiting for posts to load...")
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
                        log(f"[OK] Found posts using selector: {selector}")
                        job_posts = elements
                        break
                except Exception as e:
                    log(f"[WARN] Selector {selector} failed: {str(e)}")
                    continue
            
            if not job_posts:
                log("[ERROR] No job posts found with any selector")
                
                # Send admin alert for scraping failure
                try:
                    _send_admin_alert(
                        user_email=user_email or "Unknown",
                        error_type="LinkedIn Scraping Failed - No Posts Found",
                        error_message="Could not find any job posts with any CSS selector",
                        additional_info={
                            "Run ID": run_id,
                            "Search URL": url,
                            "Search Role": search_role,
                            "Selectors Tried": ', '.join(selectors)
                        }
                    )
                except Exception as alert_error:
                    log(f"[WARN] Could not send admin alert: {str(alert_error)}")
                
                return
                
            for post in job_posts:
                # Check stop flag
                if automation_stop_flag:
                    log("[STOP!] Automation stopped by user")
                    return
                
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
                    
                    # Save full text and create a truncated description
                    full_text = title_elem.text if title_elem else ""
                    description = full_text[:200] + "..." if len(full_text) > 200 else full_text
                    
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
                            "full_text": full_text,  # Save complete post text
                            "email": email,
                            "location": "Remote/On-site",  # You can enhance this with actual location parsing
                            "job_type": "Full-time",      # You can enhance this with actual job type parsing
                            "posted_date": datetime.now().strftime("%Y-%m-%d"),
                            "url": url,
                            "job_url": url,
                            "skills": []
                        }
                        save_job_post(job_post, user_email)
                        
                except Exception as e:
                    log(f"Error extracting job post: {e}")
                    continue

        log(f"[EMAIL] Found {len(all_emails)} email(s).")

        # CHECK EMAIL LIMIT FOR FREE USERS BEFORE SENDING
        skipped_emails = []
        if user_email:
            try:
                subscription = db.get_subscription(user_email)
                user_plan = subscription.get('plan', 'free')
                
                if user_plan == 'free':
                    # Count emails sent today
                    from datetime import date
                    today = date.today()
                    
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT COUNT(*) as count
                        FROM sent_emails
                        WHERE user_email = ? AND DATE(sent_at) = DATE('now')
                    ''', (user_email,))
                    
                    result = cursor.fetchone()
                    conn.close()
                    
                    emails_today = result['count'] if result else 0
                    
                    if emails_today >= 10:
                        print(f"[ERROR] Daily limit reached! Free users can send 10 emails per day. Already sent: {emails_today}")
                        print("[WARN] Stopping automation. Upgrade to Pro for unlimited emails.")
                        send_event(f"<div class='upgrade-prompt'><h4>[*] Daily Limit Reached!</h4><p>You've sent all 10 emails available on the Free plan today.</p><p><strong>Missing opportunities for {len(all_emails)} potential jobs!</strong></p><a href='/pricing' class='btn-upgrade'>Upgrade to Pro for Unlimited Emails</a></div>")
                        return  # Stop the automation
                    
                    # Check if we're about to exceed the limit
                    emails_to_send = len(all_emails)
                    if emails_today + emails_to_send > 10:
                        max_can_send = 10 - emails_today
                        print(f"[WARN] Can only send {max_can_send} more emails today (already sent {emails_today}/10)")
                        # Store skipped emails for upgrade prompt
                        all_emails_list = list(all_emails)
                        skipped_emails = all_emails_list[max_can_send:]
                        all_emails = set(all_emails_list[:max_can_send])  # Limit to remaining quota
                        print(f"[COUNT] Will send {len(all_emails)} emails, {len(skipped_emails)} will be skipped due to free plan limit")
                    
                    print(f"[OK] Email limit check passed. Plan: {user_plan}, Sent today: {emails_today}/10")
            except Exception as e:
                print(f"[WARN] Could not check email limit: {str(e)}")

        # Function to check if email was already sent (using SQLite)
        def is_duplicate_email(email, subject):
            try:
                # Query SQLite directly for this email+subject combination
                conn = db.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT sent_at FROM sent_emails
                    WHERE recipient_email = ? AND subject = ? AND status IN ('sent', 'skipped')
                    LIMIT 1
                ''', (email, subject))
                
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    return True, result['sent_at']
                
                return False, None
                
            except Exception as e:
                print(f"[ERROR] Error checking for duplicate email: {str(e)}")
                # If we can't check reliably, assume it might be a duplicate
                return True, None

        # Send emails with enhanced duplicate checking
        emails_sent_count = 0
        
        for receiver_email in all_emails:
            # Check stop flag
            if automation_stop_flag:
                log("[STOP!] Automation stopped by user")
                break
            
            try:
                # Check if this exact email+subject was already sent
                is_duplicate, last_sent = is_duplicate_email(receiver_email, subject)
                
                if is_duplicate:
                    when = f" (last sent: {last_sent})" if last_sent else ""
                    print(f"[WARN] Already sent to {receiver_email} with subject '{subject}'{when} — skipping.")
                    
                    # Record skip with detailed reason
                    save_sent_email({
                        "email": receiver_email,
                        "recipient_email": receiver_email,
                        "subject": subject if subject else "",
                        "cc": cc_email,
                        "sent_at": datetime.now().isoformat(),
                        "status": "skipped",
                        "reason": "duplicate",
                        "last_sent": last_sent,
                        "source_url": ",".join(search_urls)
                    }, run_id, user_email)
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

                # Extract company name from email for better UX
                company_name = extract_company_from_email(receiver_email)
                send_event(f"[EMAIL] Sending email to {company_name}...")
                send_event(f"EMAIL_PENDING:{receiver_email}")
                
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(sender_email, sender_password)
                # Send to both receiver and CC recipient
                recipients = [receiver_email]
                if cc_email:
                    recipients.append(cc_email)
                server.sendmail(sender_email, recipients, msg.as_string())
                server.quit()

                emails_sent_count += 1
                send_event(f"[OK] Email sent to {company_name} successfully!")
                send_event(f"EMAIL_SENT:{receiver_email}")
                print(f"[OK] Sent to {receiver_email} (CC: {cc_email})")
                # Persist sent email record
                save_sent_email({
                    "email": receiver_email,
                    "recipient_email": receiver_email,
                    "subject": subject if subject else "",
                    "cc": cc_email,
                    "sent_at": datetime.now().isoformat(),
                    "status": "sent",
                    "source_url": ",".join(search_urls)
                }, run_id, user_email)
            except Exception as e:
                log(f"[ERROR] Failed to send email to {receiver_email}: {e}")
                
                # Send admin alert for email failure
                try:
                    import traceback
                    company_name = extract_company_from_email(receiver_email)
                    _send_admin_alert(
                        user_email=user_email or "Unknown",
                        error_type="Email Sending Failed",
                        error_message=str(e),
                        additional_info={
                            "Run ID": run_id,
                            "Recipient": receiver_email,
                            "Company": company_name,
                            "CC": cc_email,
                            "Subject": subject,
                            "Traceback": traceback.format_exc()[:500]
                        }
                    )
                except Exception as alert_error:
                    log(f"[WARN] Could not send admin alert: {str(alert_error)}")
                
                # Persist failure
                try:
                    save_sent_email({
                        "email": receiver_email,
                        "recipient_email": receiver_email,
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
        automation_running = False
        
        try:
            # Force close any remaining Chrome instances
            if driver:
                try:
                    driver.quit()
                    print("[OK] Driver quit successfully")
                except Exception as quit_error:
                    print(f"[WARN] Driver quit failed: {str(quit_error)}")
                    
                    # Send admin alert for browser crash during cleanup
                    try:
                        _send_admin_alert(
                            user_email=user_email or "Unknown",
                            error_type="Browser Crash During Cleanup",
                            error_message=str(quit_error),
                            additional_info={
                                "Run ID": run_id,
                                "Search Role": search_role,
                                "Emails Sent": emails_sent_count,
                                "Note": "Driver quit() failed during cleanup"
                            }
                        )
                    except Exception as alert_error:
                        log(f"[WARN] Could not send admin alert: {str(alert_error)}")
            
            # Always cleanup Chrome processes (even if driver.quit() fails)
            cleanup_chrome_processes()
            print("[DONE] Browser and Chrome instances closed.")
            
            print(f"[COUNT] Summary:")
            print(f"   - Emails found: {len(all_emails)}")
            print(f"   - Emails sent: {emails_sent_count}")
            
            # Show upgrade prompt FIRST if emails were skipped (before completion message)
            if len(skipped_emails) > 0:
                skipped_companies = [extract_company_from_email(email) for email in skipped_emails[:5]]
                companies_list = '<br>'.join([f"• {company}" for company in skipped_companies])
                more_text = f"<br>• ...and {len(skipped_emails) - 5} more companies" if len(skipped_emails) > 5 else ""
                
                print(f"[PLAN] Sending upgrade prompt for {len(skipped_emails)} skipped emails")
                send_event(f"""<div class='upgrade-prompt-modal'>
                    <h3>🌟 You're Missing Great Opportunities!</h3>
                    <p><strong>{len(skipped_emails)} emails couldn't be sent</strong> due to your Free plan limit (10 emails/day).</p>
                    <div class='missed-companies'>
                        <p><strong>Companies you missed:</strong></p>
                        {companies_list}{more_text}
                    </div>
                    <p class='upgrade-cta'>💎 Upgrade to Pro for unlimited emails and never miss an opportunity!</p>
                    <a href='/pricing' class='btn-upgrade-big'>Upgrade to Pro Now</a>
                </div>""")
                
                # Give frontend time to receive and process the upgrade prompt
                time.sleep(0.5)
                print(f"[PLAN] Upgrade prompt sent for {len(skipped_emails)} skipped emails")
                
                # Send email notification to user about skipped emails
                if user_email:
                    try:
                        print(f"[EMAIL] Sending missed opportunity email to {user_email}")
                        
                        send_missed_opportunity_email(
                            recipient_email=user_email,
                            emails_sent=emails_sent_count,
                            skipped_count=len(skipped_emails),
                            total_found=len(all_emails) + len(skipped_emails),
                            skipped_emails=skipped_emails,
                            extract_company_func=extract_company_from_email
                        )
                        
                        print(f"[OK] Missed opportunity email sent to {user_email}")
                        
                    except Exception as email_error:
                        print(f"[ERROR] Failed to send automation summary email: {str(email_error)}")
                        log(f"[ERROR] Failed to send summary email to user: {str(email_error)}")
                        
                        # Send admin alert for email failure
                        try:
                            import traceback
                            _send_admin_alert(
                                user_email=user_email or "Unknown",
                                error_type="Failed to Send User Summary Email",
                                error_message=str(email_error),
                                additional_info={
                                    "Run ID": run_id,
                                    "Emails Sent": emails_sent_count,
                                    "Skipped": len(skipped_emails),
                                    "Traceback": traceback.format_exc()
                                }
                            )
                        except Exception as alert_error:
                            log(f"[WARN] Could not send admin alert: {str(alert_error)}")
            
            # Also send a success email if all emails were sent (no skips)
            elif user_email and emails_sent_count > 0:
                try:
                    print(f"[EMAIL] Sending success summary email to {user_email}")
                    
                    send_success_summary_email(
                        recipient_email=user_email,
                        emails_sent=emails_sent_count,
                        total_found=len(all_emails)
                    )
                    
                    print(f"[OK] Success summary email sent to {user_email}")
                    
                except Exception as email_error:
                    print(f"[ERROR] Failed to send success summary email: {str(email_error)}")
                    log(f"[ERROR] Failed to send summary email to user: {str(email_error)}")
                    
                    # Send admin alert for email failure
                    try:
                        import traceback
                        _send_admin_alert(
                            user_email=user_email or "Unknown",
                            error_type="Failed to Send Success Summary Email",
                            error_message=str(email_error),
                            additional_info={
                                "Run ID": run_id,
                                "Emails Sent": emails_sent_count,
                                "Total Found": len(all_emails),
                                "Traceback": traceback.format_exc()
                            }
                        )
                    except Exception as alert_error:
                        log(f"[WARN] Could not send admin alert: {str(alert_error)}")

            # Send completion status back to the frontend (AFTER upgrade prompt)
            if automation_stop_flag:
                send_event(f"[STOP] Automation stopped by user. Sent {emails_sent_count} emails before stopping.")
                print("[STOP!] Automation stopped by user")
                # Mark automation as not running in finally block
            else:
                send_event(f"[OK] Automation completed successfully! Sent {emails_sent_count} emails.")
                print("[OK] Automation completed successfully!")
                # Mark automation as not running in finally block
            
            # Return status if this was called from a route
            return {
                "status": "completed",
                "emails_found": len(all_emails),
                "message": "Automation completed successfully!"
            }
            
        except Exception as e:
            log(f"[ERROR] Error during cleanup: {str(e)}")
            # Still try to kill Chrome processes even if everything else fails
            try:
                cleanup_chrome_processes()
            except:
                pass


# --- START AUTOMATION ---
@app.route("/stop_automation", methods=["POST"])
@login_required
def stop_automation():
    """Stop the running automation for this user"""
    global automation_sessions
    
    user_email = session.get("user")
    print(f"[STOP!] Stop automation requested by: {user_email}")
    
    # Check if user has an active session
    if user_email not in automation_sessions:
        return jsonify({"success": False, "message": "No automation running"}), 404
    
    # Set stop flag for this user
    automation_sessions[user_email]['stop_flag'] = True
    log("[STOP!] Stop requested - automation will terminate soon...")
    
    # Try to close the browser immediately for this user
    if automation_sessions[user_email].get('driver'):
        try:
            automation_sessions[user_email]['driver'].quit()
            print("[OK] Browser closed for user")
        except Exception as e:
            print(f"[WARN] Error closing browser: {e}")
    
    return jsonify({"success": True, "message": "Automation stop requested", "status": "stopped"}), 200

@app.route("/check_automation_status", methods=["GET"])
@login_required
def check_automation_status():
    """Check if automation is actually running and reset if stale"""
    global automation_running, automation_driver
    
    # If automation_running is True but no driver exists, it's a stale session
    if automation_running and (automation_driver is None or not hasattr(automation_driver, 'session_id')):
        print("[CLEANUP] Detected stale automation session - resetting")
        automation_running = False
        return jsonify({
            "is_running": False,
            "was_stale": True,
            "message": "Stale session cleaned up"
        })
    
    return jsonify({
        "is_running": automation_running,
        "was_stale": False
    })

@app.route("/run_automation", methods=["POST"])
@login_required
def send_email():
    global automation_sessions
    
    print("[REQ] Received automation request")
    
    # Get the logged-in user's email
    user_email = session.get("user")
    print(f"[@] User email: {user_email}")
    activity_logger.info(f"🚀 Automation started | User: {user_email}")
    
    # Check if this user already has an automation running
    if user_email in automation_sessions and automation_sessions[user_email].get('running'):
        print(f"[WARN] User {user_email} already has automation running")
        return jsonify({
            "success": False,
            "error": "You already have an automation running. Please wait for it to complete or stop it first.",
            "already_running": True
        }), 409  # Conflict status code
    
    # Check if ANY other user has automation running (LinkedIn scraping conflict)
    other_automations_running = any(
        session_data.get('running') and session_data.get('driver') is not None
        for email, session_data in automation_sessions.items()
        if email != user_email
    )
    
    if other_automations_running:
        print(f"[🔄 QUEUE] Another user's automation is active - {user_email} will use QUICK SEND mode")
        print(f"[INFO] Active sessions: {list(automation_sessions.keys())}")
    else:
        print(f"[🚀 NEW] {user_email} will SCRAPE LinkedIn and send emails (no conflicts)")
    
    # Initialize user session
    automation_sessions[user_email] = {
        'running': True,
        'stop_flag': False,
        'driver': None,
        'thread': None
    }
    
    print(f"[OK] Started new automation session for {user_email}")
    
    # CHECK EMAIL LIMIT BEFORE STARTING AUTOMATION
    can_send, emails_sent, limit_message = check_email_limit(user_email)
    if not can_send:
        print(f"[STOP] Blocking automation - limit reached!")
        automation_sessions[user_email]['running'] = False
        return jsonify({
            "success": False,
            "error": limit_message,
            "limit_reached": True,
            "upgrade_url": "/pricing"
        }), 403
    
    print(f"[OK] Email limit check passed. Sent today: {emails_sent}/10")
    
    # Get form data
    subject = request.form.get("subject", "Application")
    email_content = request.form.get("content", "").strip()
    search_role = request.form.get("searchRole", "").strip()
    search_time_period = request.form.get("searchTimePeriod", "past-week")
    use_saved_resume = request.form.get("useSavedResume") == "true"
    
    # Save search preferences to user profile
    try:
        # Note: This requires extending the user_profiles table or using JSON storage
        # For now, we'll just log it
        print(f"Search preferences: role={search_role}, time={search_time_period}")
    except Exception as e:
        print(f"[WARN] Could not save search preferences: {e}")
    print(f"[EMAIL] Subject: {subject}")
    print(f"📝 Content length: {len(email_content)} characters")
    print(f"📎 Using saved resume: {use_saved_resume}")
    
    resume_path = None
    
    if use_saved_resume:
        # Get saved resume BLOB from database
        try:
            profile_data = db.get_profile(user_email)
            if profile_data:
                resume_blob = profile_data.get('resume_data')
                resume_filename = profile_data.get('resume_filename')
                
                if resume_blob and resume_filename:
                    print(f"[INFO] Retrieving saved resume: {resume_filename}")
                    
                    try:
                        # Write BLOB to temporary file
                        temp_dir = tempfile.gettempdir()
                        resume_path = os.path.join(temp_dir, f"{user_email}_{resume_filename}")
                        
                        with open(resume_path, 'wb') as f:
                            f.write(resume_blob)
                        
                        print(f"[OK] Resume restored to temporary file: {resume_path}")
                        print(f"[OK] Resume size: {len(resume_blob)} bytes")
                        
                    except Exception as write_error:
                        print(f"[ERROR] Error writing resume: {str(write_error)}")
                        flash("Error loading saved resume. Please upload a new resume.", "error")
                        return redirect(url_for("send_page"))
                else:
                    flash("No resume found in your profile. Please upload a resume.", "error")
                    return redirect(url_for("send_page"))
            else:
                flash("Profile not found. Please upload a resume.", "error")
                return redirect(url_for("send_page"))
        except Exception as e:
            print(f"[ERROR] Error accessing profile: {str(e)}")
            import traceback
            traceback.print_exc()
            flash("Error accessing profile. Please upload a resume.", "error")
            return redirect(url_for("send_page"))
    else:
        # Handle new file upload - save to temporary location
        if "resume" not in request.files:
            print("[ERROR] No resume file in request")
            flash("Please upload a resume or use your saved resume.", "error")
            return redirect(url_for("send_page"))
            
        resume = request.files["resume"]
        if resume.filename == "":
            print("[ERROR] Empty resume filename")
            flash("No resume file selected. Please choose a file or use your saved resume.", "error")
            return redirect(url_for("send_page"))

        # Save the uploaded resume to temporary location (works in Docker)
        temp_dir = tempfile.gettempdir()
        resume_path = os.path.join(temp_dir, f"{user_email}_{resume.filename}")
        resume.save(resume_path)
        print(f"[INFO] Resume saved to temporary file: {resume_path}")

    # Clean up any existing Chrome instances before starting
    print("[DONE] DEBUG: Cleaning up Chrome processes...")
    cleanup_chrome_processes()
    print("[OK] DEBUG: Chrome cleanup complete")

    # Generate a unique run ID
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"[#] DEBUG: Generated run_id: {run_id}")

    # Initialize automation run in SQLite
    try:
        print("[SAVE] DEBUG: Saving automation run to SQLite...")
        save_automation_run(run_id, user_email, {
            'subject': subject,
            'usesSavedResume': use_saved_resume,
            'resumePath': resume_path,
            'searchRole': search_role,
            'searchTimePeriod': search_time_period
        })
        print("[OK] DEBUG: Automation run saved to SQLite")
    except Exception as e:
        print(f"[WARN] Could not save automation run: {e}")

    # Start automation in background thread
    print("=" * 60)
    print("[THREAD] DEBUG: Starting automation thread...")
    print(f"[THREAD] DEBUG: Other automations running: {other_automations_running}")
    print(f"[THREAD] DEBUG: Thread args: subject={subject}, content_len={len(email_content)}, resume={resume_path}")
    print(f"[THREAD] DEBUG: Thread args: run_id={run_id}, user={user_email}, role={search_role}, time={search_time_period}")
    print("=" * 60)
    
    # If another automation is running, use quick send from existing jobs
    if other_automations_running:
        print("=" * 80)
        print("[🔄 QUICK SEND MODE] Another user is scraping LinkedIn")
        print(f"[INFO] User: {user_email}")
        print(f"[INFO] Mode: Send from existing database (no scraping)")
        print(f"[INFO] This prevents Chrome/LinkedIn conflicts between users")
        print("=" * 80)
        thread = threading.Thread(
            target=send_emails_from_existing_jobs,
            args=(subject, email_content, resume_path, user_email, run_id, user_email, search_role, 10),
            daemon=True
        )
    else:
        print("=" * 80)
        print("[🚀 FULL AUTOMATION MODE] No conflicts - full scraping enabled")
        print(f"[INFO] User: {user_email}")
        print(f"[INFO] Mode: Scrape LinkedIn + Send emails")
        print(f"[INFO] Search: {search_role} ({search_time_period})")
        print("=" * 80)
        # Fixed argument order to match function signature:
        # run_automation(subject, email_content, attachment_path, cc_email, run_id, user_email, search_role, search_time)
        thread = threading.Thread(
            target=run_automation,
            args=(subject, email_content, resume_path, user_email, run_id, user_email, search_role, search_time_period),
            daemon=True
        )
    
    thread.start()
    automation_sessions[user_email]['thread'] = thread
    print(f"[OK] DEBUG: Thread started, thread is alive: {thread.is_alive()}")
    print(f"[OK] DEBUG: Thread name: {thread.name}")

    # Don't use flash() for automation since we have real-time SSE updates
    # flash("[*] Automation started in background. Check console logs for updates.", "success")
    return redirect(url_for("send_page"))


# --- PRICING & PAYMENT ---
@app.route("/pricing")
@login_required
def pricing_page():
    """Display pricing plans"""
    user_email = session.get("user")
    subscription = db.get_subscription(user_email)
    
    return render_template("pricing.html", subscription=subscription)


@app.route("/create_payment", methods=["POST"])
@login_required
def create_payment():
    """Create Razorpay payment order"""
    try:
        if not razorpay_client:
            return jsonify({'success': False, 'error': 'Payment gateway not configured'})
        
        data = request.get_json()
        plan = data.get('plan')
        price = data.get('price')
        user_email = session.get("user")
        
        if not plan or not price:
            return jsonify({'success': False, 'error': 'Invalid payment data'})
        
        # Get user profile for phone number
        user_name = user_email.split('@')[0]  # Default name from email
        user_contact = ''
        
        try:
            profile = db.get_profile(user_email)
            if profile:
                user_contact = profile.get('phone', profile.get('contact', ''))
                if profile.get('display_name'):
                    user_name = profile.get('display_name')
        except Exception as e:
            print(f"[WARN] Could not fetch user profile: {e}")
        
        # Generate unique order ID
        order_id = f"JMI_{int(time.time())}_{plan}"
        
        # Create Razorpay order
        razorpay_order = razorpay_client.order.create({
            'amount': int(float(price) * 100),  # Razorpay expects amount in paise (1 INR = 100 paise)
            'currency': 'INR',
            'receipt': order_id,
            'notes': {
                'plan': plan,
                'user_email': user_email
            }
        })
        
        # Store pending payment in SQLite
        # Note: This requires a pending_payments table which exists in database.py
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO pending_payments (order_id, user_email, plan, amount, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (order_id, user_email, plan, price))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[WARN] Could not store pending payment: {e}")
        
        # Prepare prefill data
        prefill_data = {
            'email': user_email,
            'name': user_name
        }
        
        # Add contact only if available
        if user_contact:
            prefill_data['contact'] = user_contact
        
        return jsonify({
            'success': True,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': RAZORPAY_KEY_ID,
            'order_id': order_id,
            'amount': int(float(price) * 100),  # Amount in paise for frontend
            'currency': 'INR',
            'name': 'JustMailIt',
            'description': f'{plan} Plan Subscription',
            'prefill': prefill_data
        })
        
    except Exception as e:
        print(f"[ERROR] Payment creation error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to create payment: {str(e)}'
        })


@app.route("/payment/webhook", methods=["POST"])
def payment_webhook():
    """Razorpay webhook for automatic payment verification"""
    try:
        # Get webhook data
        webhook_data = request.get_json()
        
        # Verify webhook signature (important for security)
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        webhook_secret = os.getenv('RAZORPAY_WEBHOOK_SECRET', '')
        
        # Verify signature if webhook secret is configured
        if webhook_secret and razorpay_client:
            try:
                razorpay_client.utility.verify_webhook_signature(
                    json.dumps(webhook_data, separators=(',', ':')),
                    webhook_signature,
                    webhook_secret
                )
            except Exception as e:
                print(f"[WARN] Webhook signature verification failed: {e}")
                return jsonify({'success': False, 'error': 'Invalid signature'}), 400
        
        # Handle payment.captured event
        event = webhook_data.get('event')
        
        if event == 'payment.captured':
            payment = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
            razorpay_order_id = payment.get('order_id')  # Razorpay's order ID
            razorpay_payment_id = payment.get('id')
            amount = payment.get('amount') / 100  # Convert from paise to INR
            
            # Update payment and activate subscription
            if razorpay_order_id:
                try:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    
                    # Get pending payment by Razorpay order ID
                    cursor.execute('''
                        SELECT * FROM pending_payments WHERE order_id = ?
                    ''', (razorpay_order_id,))
                    
                    payment_data = cursor.fetchone()
                    conn.close()
                    
                    if payment_data:
                        user_email = payment_data['user_email']
                        plan = payment_data['plan']
                        doc_order_id = payment_data['order_id']
                        amount = payment_data['amount']
                        
                        # Activate subscription
                        activate_subscription(user_email, plan, amount, doc_order_id)
                        
                        print(f"[OK] Payment webhook: {user_email} upgraded to {plan} (Payment ID: {razorpay_payment_id})")
                except Exception as e:
                    print(f"[WARN] Could not process webhook: {e}")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        print(f"[ERROR] Webhook error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/payment/callback")
def payment_callback():
    """Handle return URL after payment"""
    order_id = request.args.get('order_id')
    
    # Redirect to pricing page with status
    return redirect(url_for('pricing_page', order_id=order_id, status='success'))


@app.route("/payment/success", methods=["POST"])
@login_required
def payment_success():
    """Handle immediate payment success from Razorpay frontend"""
    try:
        data = request.get_json()
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        our_order_id = data.get('order_id')
        
        # Verify payment signature
        if razorpay_client:
            try:
                params_dict = {
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature
                }
                razorpay_client.utility.verify_payment_signature(params_dict)
                print(f"[OK] Payment signature verified: {razorpay_payment_id}")
            except Exception as e:
                print(f"[ERROR] Payment signature verification failed: {e}")
                return jsonify({'success': False, 'error': 'Invalid payment signature'})
        
        # Get payment details from SQLite
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM pending_payments WHERE order_id = ?', (our_order_id,))
            payment_data = cursor.fetchone()
            conn.close()
            
            if payment_data:
                user_email = payment_data['user_email']
                plan = payment_data['plan']
                amount = payment_data['amount']
                
                # Activate subscription
                activate_subscription(user_email, plan, amount, our_order_id)
                
                print(f"[OK] Payment success: {user_email} upgraded to {plan} (Payment ID: {razorpay_payment_id})")
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully upgraded to {plan} plan!',
                    'status': 'completed'
                })
            else:
                return jsonify({'success': False, 'error': 'Payment record not found'})
        except Exception as e:
            print(f"[ERROR] Error processing payment: {e}")
            return jsonify({'success': False, 'error': 'Payment processing failed'})
        
    except Exception as e:
        print(f"[ERROR] Payment success handler error: {e}")
        return jsonify({'success': False, 'error': str(e)})


def activate_subscription(user_email, plan, price, order_id):
    """Activate user subscription after successful payment"""
    try:
        from datetime import timedelta
        next_billing = datetime.now() + timedelta(days=30)
        
        subscription_data = {
            'plan': plan,
            'status': 'active',
            'amount': price,
            'razorpay_order_id': order_id,
            'expires_at': next_billing.isoformat()
        }
        
        db.create_or_update_subscription(user_email, subscription_data)
        print(f"[OK] Subscription activated: {user_email} - {plan} plan")
        
        # Get user name
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT display_name FROM user_profiles WHERE email = ?", (user_email,))
        user_data = cursor.fetchone()
        conn.close()
        
        user_name = user_data['display_name'] if user_data and user_data['display_name'] else user_email.split('@')[0]
        
        # Send upgrade notification email
        send_upgrade_notification_email(user_email, user_name, plan, duration_days=30, upgraded_by='self')
        
    except Exception as e:
        print(f"[ERROR] Activate subscription error: {e}")


@app.route("/check_payment_status/<order_id>", methods=["GET"])
@login_required
def check_payment_status(order_id):
    """Check if payment has been completed"""
    try:
        user_email = session.get("user")
        
        # Check if user has active subscription
        subscription = db.get_subscription(user_email)
        
        if subscription and subscription.get('status') == 'active':
            # Check if subscription is recent (within last 5 minutes)
            started_at = subscription.get('started_at')
            if started_at:
                # Parse timestamp if it's a string
                if isinstance(started_at, str):
                    try:
                        # Try to parse ISO format timestamp
                        start_date = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    except:
                        start_date = None
                else:
                    start_date = started_at
                
                if start_date and (datetime.now() - start_date).total_seconds() < 300:
                    return jsonify({
                        'success': True,
                        'status': 'completed',
                        'plan': subscription.get('plan'),
                        'message': 'Payment verified and subscription activated!'
                    })
        
        # Check pending payment status
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM pending_payments WHERE order_id = ?', (order_id,))
        payment_data = cursor.fetchone()
        conn.close()
        
        if payment_data:
            return jsonify({
                'success': True,
                'status': 'pending',
                'message': 'Waiting for payment confirmation...'
            })
        
        return jsonify({
            'success': True,
            'status': 'pending',
            'message': 'Payment pending'
        })
        
    except Exception as e:
        print(f"[ERROR] Payment status check error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to check payment status'
        })


# ========== ADMIN PANEL ROUTES ==========

# Admin decorator moved to utils/decorators.py - ADMIN_EMAIL imported from there
# Keeping original code commented for safety - DELETE AFTER TESTING
# ADMIN_EMAIL = "manuchaturvedi28mc@gmail.com"
# 
# def admin_required(f):
#     """Decorator to check if user is admin"""
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         print(f"[DEBUG] admin_required: Checking access for route {f.__name__}", flush=True)
#         if "user" not in session:
#             print("[DEBUG] admin_required: No user in session", flush=True)
#             flash("Please log in first!", "warning")
#             return redirect(url_for('landing'))
#         
#         # session['user'] is a string (email), not a dict
#         user_email = session.get('user', '')
#         print(f"[DEBUG] admin_required: User={user_email}, Admin={ADMIN_EMAIL}", flush=True)
#         if user_email != ADMIN_EMAIL:
#             print(f"[DEBUG] admin_required: Access denied - not admin", flush=True)
#             flash("Access denied. Admin only!", "danger")
#             return redirect(url_for('dashboard'))
#         
#         print(f"[DEBUG] admin_required: Access granted", flush=True)
#         return f(*args, **kwargs)
#     return decorated_function

@app.route('/admin')
@admin_required
def admin_panel():
    """Admin panel dashboard"""
    try:
        print(f"[ADMIN] Loading admin panel - DB path: {db.db_path}", flush=True)
        activity_logger.info(f"🔐 Admin panel accessed | User: {session.get('user')}")
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get total users
        cursor.execute("SELECT COUNT(*) FROM user_profiles")
        total_users = cursor.fetchone()[0]
        print(f"[ADMIN] Total users: {total_users}", flush=True)
        
        # Get new users today
        cursor.execute("""
            SELECT COUNT(*) FROM user_profiles 
            WHERE DATE(created_at) = DATE('now')
        """)
        new_users_today = cursor.fetchone()[0]
        
        # Get total emails sent
        cursor.execute("SELECT COUNT(*) FROM sent_emails")
        total_emails = cursor.fetchone()[0]
        print(f"[ADMIN] Total emails: {total_emails}", flush=True)
        
        # Get emails sent today
        cursor.execute("""
            SELECT COUNT(*) FROM sent_emails 
            WHERE DATE(sent_at) = DATE('now')
        """)
        emails_today = cursor.fetchone()[0]
        
        # Get active automation runs
        cursor.execute("""
            SELECT COUNT(*) FROM automation_runs 
            WHERE status = 'running'
        """)
        active_runs = cursor.fetchone()[0]
        
        # Get total automation runs
        cursor.execute("SELECT COUNT(*) FROM automation_runs")
        total_runs = cursor.fetchone()[0]
        
        # Get premium users count
        cursor.execute("""
            SELECT COUNT(*) FROM subscriptions 
            WHERE status = 'active' AND plan != 'free'
        """)
        premium_users = cursor.fetchone()[0]
        
        # Get recent users (last 10)
        cursor.execute("""
            SELECT email, display_name, created_at 
            FROM user_profiles 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        recent_users = [dict(row) for row in cursor.fetchall()]
        
        # Get user email statistics with subscription info
        cursor.execute("""
            SELECT 
                up.email,
                up.display_name,
                up.created_at,
                COUNT(DISTINCT se.id) as emails_sent,
                COUNT(DISTINCT ar.id) as automation_runs,
                COALESCE(s.plan, 'free') as plan,
                COALESCE(s.status, 'inactive') as subscription_status,
                s.expires_at
            FROM user_profiles up
            LEFT JOIN sent_emails se ON up.email = se.user_email
            LEFT JOIN automation_runs ar ON up.email = ar.user_email
            LEFT JOIN subscriptions s ON up.email = s.user_email
            GROUP BY up.email
            ORDER BY emails_sent DESC, up.created_at DESC
            LIMIT 50
        """)
        user_stats = [dict(row) for row in cursor.fetchall()]
        
        # Get recent email activity
        cursor.execute("""
            SELECT 
                se.user_email,
                se.recipient_email,
                se.subject,
                se.company,
                se.job_title,
                se.sent_at,
                se.status
            FROM sent_emails se
            ORDER BY se.sent_at DESC
            LIMIT 50
        """)
        recent_emails = [dict(row) for row in cursor.fetchall()]
        print(f"[ADMIN] Recent emails count: {len(recent_emails)}", flush=True)
        
        # Get daily email stats (last 7 days)
        cursor.execute("""
            SELECT 
                DATE(sent_at) as date,
                COUNT(*) as count
            FROM sent_emails
            WHERE sent_at >= DATE('now', '-7 days')
            GROUP BY DATE(sent_at)
            ORDER BY date DESC
        """)
        daily_stats = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        stats = {
            'total_users': total_users,
            'new_users_today': new_users_today,
            'total_emails': total_emails,
            'emails_today': emails_today,
            'active_runs': active_runs,
            'total_runs': total_runs,
            'premium_users': premium_users
        }
        
        return render_template('admin.html',
                             stats=stats,
                             recent_users=recent_users,
                             user_stats=user_stats,
                             recent_emails=recent_emails,
                             daily_stats=daily_stats)
    
    except Exception as e:
        print(f"Admin panel error: {e}")
        flash(f"Error loading admin panel: {str(e)}", "danger")
        return redirect(url_for('landing'))

@app.route('/admin/api/stats')
@admin_required
def admin_api_stats():
    """API endpoint for real-time admin stats"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get various statistics
        cursor.execute("SELECT COUNT(*) FROM user_profiles")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sent_emails WHERE DATE(sent_at) = DATE('now')")
        emails_today = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM automation_runs WHERE status = 'running'")
        active_runs = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_users': total_users,
            'emails_today': emails_today,
            'active_runs': active_runs
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/debug/db-check')
@admin_required
def admin_debug_db():
    """Debug endpoint to check database contents"""
    try:
        import os
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM user_profiles")
        users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sent_emails")
        emails = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM job_posts")
        jobs = cursor.fetchone()[0]
        
        cursor.execute("SELECT email, display_name, created_at FROM user_profiles ORDER BY created_at DESC LIMIT 5")
        recent = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT user_email, recipient_email, subject, sent_at FROM sent_emails ORDER BY sent_at DESC LIMIT 5")
        recent_emails = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'db_path': db.db_path,
            'db_exists': os.path.exists(db.db_path),
            'db_size': os.path.getsize(db.db_path) if os.path.exists(db.db_path) else 0,
            'counts': {
                'users': users,
                'emails': emails,
                'jobs': jobs
            },
            'recent_users': recent,
            'recent_emails': recent_emails
        })
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()})

@app.route('/admin/user/<email>')
@admin_required
def admin_user_detail(email):
    """View detailed information about a specific user"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get user profile
        cursor.execute("SELECT * FROM user_profiles WHERE email = ?", (email,))
        user = dict(cursor.fetchone())
        
        # Get user's sent emails
        cursor.execute("""
            SELECT * FROM sent_emails 
            WHERE user_email = ? 
            ORDER BY sent_at DESC
        """, (email,))
        sent_emails = [dict(row) for row in cursor.fetchall()]
        
        # Get user's automation runs
        cursor.execute("""
            SELECT * FROM automation_runs 
            WHERE user_email = ? 
            ORDER BY started_at DESC
        """, (email,))
        automation_runs = [dict(row) for row in cursor.fetchall()]
        
        # Get user's job posts
        cursor.execute("""
            SELECT * FROM job_posts 
            WHERE user_email = ? 
            ORDER BY created_at DESC
        """, (email,))
        job_posts = [dict(row) for row in cursor.fetchall()]
        
        # Get user's subscription info
        cursor.execute("""
            SELECT * FROM subscriptions 
            WHERE user_email = ?
        """, (email,))
        subscription_row = cursor.fetchone()
        subscription = dict(subscription_row) if subscription_row else None
        
        conn.close()
        
        return render_template('admin_user_detail.html',
                             user=user,
                             sent_emails=sent_emails,
                             automation_runs=automation_runs,
                             job_posts=job_posts,
                             subscription=subscription)
    
    except Exception as e:
        print(f"Admin user detail error: {e}")
        flash(f"Error loading user details: {str(e)}", "danger")
        return redirect(url_for('admin_panel'))

@app.route('/admin/upgrade_user', methods=['POST'])
@admin_required
def admin_upgrade_user():
    """Admin endpoint to upgrade user to Pro without payment"""
    try:
        data = request.get_json()
        user_email = data.get('email')
        duration_days = int(data.get('duration_days', 365))  # Default 1 year
        
        if not user_email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        # Check if user exists
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM user_profiles WHERE email = ?", (user_email,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Calculate expiration date
        from datetime import datetime, timedelta
        expires_at = (datetime.now() + timedelta(days=duration_days)).isoformat()
        
        # Create or update subscription
        subscription_data = {
            'plan': 'pro',
            'status': 'active',
            'razorpay_order_id': None,
            'razorpay_payment_id': None,
            'razorpay_subscription_id': 'ADMIN_UPGRADE',
            'amount': 0,
            'coupon_code': 'ADMIN_GRANT',
            'expires_at': expires_at
        }
        
        db.create_or_update_subscription(user_email, subscription_data)
        conn.close()
        
        print(f"[OK] Admin upgraded {user_email} to Pro until {expires_at}")
        
        # Get user name
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT display_name FROM user_profiles WHERE email = ?", (user_email,))
        user_data = cursor.fetchone()
        conn.close()
        
        user_name = user_data['display_name'] if user_data and user_data['display_name'] else user_email.split('@')[0]
        
        # Send upgrade notification email
        send_upgrade_notification_email(user_email, user_name, 'pro', duration_days, upgraded_by='admin')
        
        return jsonify({
            'success': True,
            'message': f'User upgraded to Pro for {duration_days} days',
            'expires_at': expires_at
        })
        
    except Exception as e:
        print(f"[ERROR] Admin upgrade error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/downgrade_user', methods=['POST'])
@admin_required
def admin_downgrade_user():
    """Admin endpoint to downgrade user to Free plan"""
    try:
        data = request.get_json()
        user_email = data.get('email')
        
        if not user_email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        # Update subscription to free
        subscription_data = {
            'plan': 'free',
            'status': 'inactive',
            'razorpay_order_id': None,
            'razorpay_payment_id': None,
            'razorpay_subscription_id': None,
            'amount': 0,
            'coupon_code': None,
            'expires_at': None
        }
        
        db.create_or_update_subscription(user_email, subscription_data)
        
        print(f"[OK] Admin downgraded {user_email} to Free plan")
        
        return jsonify({
            'success': True,
            'message': 'User downgraded to Free plan'
        })
        
    except Exception as e:
        print(f"[ERROR] Admin downgrade error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/sync-firebase-users', methods=['POST'])
@admin_required
def admin_sync_firebase_users():
    """Admin endpoint to sync all Firebase users to database"""
    try:
        print("[ADMIN] Starting Firebase user sync...", flush=True)
        
        # Get all Firebase users
        page = auth.list_users()
        users_synced = 0
        users_skipped = 0
        users_total = 0
        errors = []
        
        while page:
            for user in page.users:
                users_total += 1
                email = user.email
                display_name = user.display_name or ""
                photo_url = user.photo_url or ""
                
                # Check if user already exists in DB
                existing = db.get_profile(email)
                if existing:
                    users_skipped += 1
                    print(f"[ADMIN SYNC] User exists: {email}", flush=True)
                else:
                    # Create new profile
                    try:
                        db.create_or_update_profile(
                            email=email,
                            display_name=display_name,
                            photo_url=photo_url
                        )
                        users_synced += 1
                        print(f"[ADMIN SYNC] ✅ Synced: {email} ({display_name})", flush=True)
                        
                        # Verify
                        verify = db.get_profile(email)
                        if not verify:
                            errors.append(f"Verification failed for: {email}")
                            print(f"[ADMIN SYNC] ❌ Verification failed: {email}", flush=True)
                    except Exception as e:
                        errors.append(f"Error adding {email}: {str(e)}")
                        print(f"[ADMIN SYNC] ❌ Error: {email} - {e}", flush=True)
            
            # Get next batch
            page = page.get_next_page()
        
        result = {
            'success': True,
            'total_firebase_users': users_total,
            'newly_synced': users_synced,
            'already_existed': users_skipped,
            'errors': errors
        }
        
        print(f"[ADMIN SYNC] Complete: {users_synced} synced, {users_skipped} existed, {len(errors)} errors", flush=True)
        return jsonify(result)
        
    except Exception as e:
        print(f"[ERROR] Firebase sync error: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/logs')
@admin_required
def admin_logs():
    """Admin page to view application logs"""
    return render_template('admin_logs.html')

@app.route('/admin/logs/list')
@admin_required
def admin_logs_list():
    """Get list of available log files"""
    try:
        log_files = []
        for filename in os.listdir(LOGS_DIR):
            if filename.endswith('.log'):
                filepath = os.path.join(LOGS_DIR, filename)
                size = os.path.getsize(filepath)
                modified = datetime.fromtimestamp(os.path.getmtime(filepath))
                log_files.append({
                    'name': filename,
                    'size': size,
                    'size_mb': round(size / 1024 / 1024, 2),
                    'modified': modified.strftime('%Y-%m-%d %H:%M:%S')
                })
        
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'success': True, 'logs': log_files})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/logs/view/<filename>')
@admin_required
def admin_logs_view(filename):
    """View log file content (last N lines)"""
    try:
        # Security: prevent path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'success': False, 'message': 'Invalid filename'}), 400
        
        filepath = os.path.join(LOGS_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'message': 'Log file not found'}), 404
        
        lines = int(request.args.get('lines', 500))
        
        # Read last N lines
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:]
            content = ''.join(last_lines)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'content': content,
            'total_lines': len(all_lines),
            'showing_lines': len(last_lines)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/logs/download/<filename>')
@admin_required
def admin_logs_download(filename):
    """Download log file"""
    try:
        # Security: prevent path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'success': False, 'message': 'Invalid filename'}), 400
        
        filepath = os.path.join(LOGS_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'message': 'Log file not found'}), 404
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/logs/clear/<filename>', methods=['POST'])
@admin_required
def admin_logs_clear(filename):
    """Clear log file content"""
    try:
        # Security: prevent path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'success': False, 'message': 'Invalid filename'}), 400
        
        filepath = os.path.join(LOGS_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'message': 'Log file not found'}), 404
        
        # Clear file content
        with open(filepath, 'w') as f:
            f.write('')
        
        app_logger.info(f"Log file cleared by admin: {filename}")
        return jsonify({'success': True, 'message': f'{filename} cleared'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/api/user_count')
@admin_required
def admin_get_user_count():
    """Get user count based on target filter"""
    try:
        target = request.args.get('target', 'all')
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        if target == 'all':
            cursor.execute("SELECT COUNT(*) FROM user_profiles")
        elif target == 'free':
            cursor.execute("""
                SELECT COUNT(*) FROM user_profiles up
                LEFT JOIN subscriptions s ON up.email = s.user_email
                WHERE s.plan IS NULL OR s.plan = 'free' OR s.status != 'active'
            """)
        elif target == 'pro':
            cursor.execute("""
                SELECT COUNT(*) FROM user_profiles up
                INNER JOIN subscriptions s ON up.email = s.user_email
                WHERE s.plan = 'pro' AND s.status = 'active'
            """)
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({'success': True, 'count': count})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/send_promotional_email', methods=['POST'])
@admin_required
def admin_send_promotional_email():
    """Send promotional email to selected users"""
    try:
        data = request.get_json()
        subject = data.get('subject', '')
        body = data.get('body', '')
        target = data.get('target', 'all')
        
        if not subject or not body:
            return jsonify({'success': False, 'message': 'Subject and body are required'}), 400
        
        # Get target users
        conn = db.get_connection()
        cursor = conn.cursor()
        
        if target == 'all':
            cursor.execute("SELECT email, display_name FROM user_profiles")
        elif target == 'free':
            cursor.execute("""
                SELECT up.email, up.display_name 
                FROM user_profiles up
                LEFT JOIN subscriptions s ON up.email = s.user_email
                WHERE s.plan IS NULL OR s.plan = 'free' OR s.status != 'active'
            """)
        elif target == 'pro':
            cursor.execute("""
                SELECT up.email, up.display_name 
                FROM user_profiles up
                INNER JOIN subscriptions s ON up.email = s.user_email
                WHERE s.plan = 'pro' AND s.status = 'active'
            """)
        
        users = cursor.fetchall()
        conn.close()
        
        # Send emails
        sent_count = 0
        failed_count = 0
        
        # Gmail SMTP settings - using mail@justmailit.in via Gmail SMTP
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "mail@justmailit.in"  # Custom domain email
        smtp_user = "manudrive06@gmail.com"  # Gmail account for authentication
        sender_password = "ozds nrqo gduy mnwd"  # Gmail App Password
        
        for user in users:
            user_email = user[0]
            user_name = user[1] or 'User'
            
            try:
                # Get user subscription plan
                subscription = db.get_subscription(user_email)
                user_plan = subscription.get('plan', 'free')
                
                # Replace placeholders in body
                personalized_body = body.replace('{name}', user_name)
                personalized_body = personalized_body.replace('{email}', user_email)
                personalized_body = personalized_body.replace('{plan}', user_plan.upper())
                
                # Create email
                msg = MIMEMultipart()
                msg["From"] = f"JustMailIt <{sender_email}>"
                msg["To"] = user_email
                msg["Subject"] = subject
                msg["Reply-To"] = sender_email
                
                msg.attach(MIMEText(personalized_body, "plain", "utf-8"))
                
                # Send email - authenticate with Gmail, send as mail@justmailit.in
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(smtp_user, sender_password)  # Authenticate with Gmail
                server.sendmail(sender_email, user_email, msg.as_string())
                server.quit()
                
                sent_count += 1
                print(f"[OK] Promotional email sent to {user_email}")
                
            except Exception as email_error:
                failed_count += 1
                print(f"[ERROR] Failed to send promotional email to {user_email}: {str(email_error)}")
        
        return jsonify({
            'success': True,
            'sent': sent_count,
            'failed': failed_count,
            'message': f'Sent {sent_count} emails successfully'
        })
        
    except Exception as e:
        print(f"[ERROR] Promotional email error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/delete_job/<int:job_id>', methods=['DELETE'])
@admin_required
def admin_delete_job(job_id):
    """Admin endpoint to delete inappropriate job posts"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if job exists
        cursor.execute("SELECT id, title FROM job_posts WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        
        if not job:
            return jsonify({'success': False, 'message': 'Job post not found'}), 404
        
        # Delete the job post
        cursor.execute("DELETE FROM job_posts WHERE id = ?", (job_id,))
        conn.commit()
        conn.close()
        
        print(f"[ADMIN] Deleted job post ID {job_id}: {job['title'] if job else 'Unknown'}")
        return jsonify({
            'success': True,
            'message': 'Job post deleted successfully'
        })
        
    except Exception as e:
        print(f"[ERROR] Delete job error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/job_posts')
@admin_required
def admin_job_posts():
    """Admin page to view and delete all job posts"""
    try:
        print("[DEBUG] admin_job_posts: Starting...", flush=True)
        conn = db.get_connection()
        print("[DEBUG] admin_job_posts: Database connection established", flush=True)
        cursor = conn.cursor()
        
        # Get all job posts with user info
        print("[DEBUG] admin_job_posts: Executing query...", flush=True)
        cursor.execute("""
            SELECT 
                id, title, company, location, recruiter_email,
                full_text as description, created_at, job_url as source_url,
                user_email
            FROM job_posts
            ORDER BY created_at DESC
            LIMIT 500
        """)
        
        # Map recruiter_email to email for template compatibility
        print("[DEBUG] admin_job_posts: Fetching and mapping results...", flush=True)
        jobs = []
        for row in cursor.fetchall():
            job = dict(row)
            job['email'] = job.get('recruiter_email', '')  # Map for template
            jobs.append(job)
        # Map recruiter_email to email for template compatibility
        print("[DEBUG] admin_job_posts: Fetching and mapping results...", flush=True)
        jobs = []
        for row in cursor.fetchall():
            job = dict(row)
            job['email'] = job.get('recruiter_email', '')  # Map for template
            jobs.append(job)
        print(f"[DEBUG] admin_job_posts: Retrieved {len(jobs)} jobs", flush=True)
        conn.close()
        
        print("[DEBUG] admin_job_posts: Rendering template...", flush=True)
        return render_template('admin_job_posts.html', jobs=jobs)
        
    except Exception as e:
        print(f"[ERROR] Failed to load admin job posts: {str(e)}", flush=True)
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}", flush=True)
        flash(f"Error loading job posts: {str(e)}", "danger")
        return redirect(url_for('admin_panel'))

# ========== JOB SCRAPING FUNCTION (for scheduler and admin) ==========
def scrape_and_save_jobs(search_role, search_time='past-week', user_email=None, scrolls=10):
    """
    Scrape LinkedIn jobs and save to database WITHOUT sending emails.
    This function is used by scheduler and admin scraping.
    """
    import time
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from urllib.parse import urlencode
    
    driver = None
    jobs_found = 0
    jobs_saved = 0
    
    try:
        print(f"[SCRAPER] Starting job scraping for: {search_role}")
        
        # Build LinkedIn search URL
        skills = parse_skills(search_role)
        search_keywords = ' OR '.join(f'{role.strip()} hiring' for role in skills)
        base_url = "https://www.linkedin.com/search/results/content/?"
        params = {
            'datePosted': f'"{search_time}"',
            'keywords': search_keywords
        }
        url = base_url + urlencode(params)
        print(f"[SCRAPER] Search URL: {url}")
        
        # Initialize Chrome driver
        chrome_options = Options()
        
        # Set Chrome/Chromium binary location
        chrome_options.binary_location = os.environ.get('CHROME_BIN', '/usr/bin/chromium')
        print(f"[SCRAPER] Using Chromium: {chrome_options.binary_location}")
        
        # Headless mode
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--remote-debugging-port=9222")
        
        # Use SAME profile directory as run_automation to share authenticated session
        if os.environ.get('CHROME_BIN'):  # Docker/Cloud environment
            profile_dir = "/tmp/chrome-profile"
            print("[SCRAPER] Using shared Docker Chrome profile directory")
        else:  # Local Windows environment
            profile_dir = r"D:\Profile"
            print("[SCRAPER] Using shared Windows Chrome profile directory")
        
        os.makedirs(profile_dir, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={profile_dir}")
        print(f"[SCRAPER] Chrome profile directory: {profile_dir}")
        
        # Launch Chrome with explicit ChromeDriver path
        chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
        print(f"[SCRAPER] Using ChromeDriver: {chromedriver_path}")
        
        from selenium.webdriver.chrome.service import Service
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("[SCRAPER] Chrome launched successfully")
        
        # Login to LinkedIn first (check if already logged in)
        print("[SCRAPER] Checking LinkedIn login status...")
        driver.get("https://www.linkedin.com/feed")
        time.sleep(3)
        
        current_url = driver.current_url
        if "login" in current_url or "authwall" in current_url:
            print("[SCRAPER] Not logged in, performing login...")
            
            # Get LinkedIn credentials from environment
            linkedin_email = os.environ.get('LINKEDIN_EMAIL', '')
            linkedin_password = os.environ.get('LINKEDIN_PASSWORD', '')
            
            if not linkedin_email or not linkedin_password:
                print("[ERROR] LinkedIn credentials not configured in environment")
                print("[ERROR] Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables")
                return {'error': 'LinkedIn credentials not configured'}
            
            # Navigate to login page
            driver.get("https://www.linkedin.com/login")
            time.sleep(3)
            
            try:
                # Wait for login form
                wait = WebDriverWait(driver, 10)
                
                # Enter email
                email_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
                email_field.clear()
                email_field.send_keys(linkedin_email)
                print("[SCRAPER] Email entered")
                
                # Enter password
                password_field = driver.find_element(By.ID, "password")
                password_field.clear()
                password_field.send_keys(linkedin_password)
                print("[SCRAPER] Password entered")
                
                # Click sign in
                sign_in_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                sign_in_button.click()
                print("[SCRAPER] Sign in button clicked")
                
                # Wait for login to complete
                time.sleep(5)
                
                # Check if login was successful
                current_url = driver.current_url
                if "feed" in current_url or "home" in current_url:
                    print("[SCRAPER] LinkedIn login successful!")
                elif "checkpoint" in current_url or "challenge" in current_url:
                    print("[ERROR] LinkedIn requires 2FA/verification - cannot proceed in headless mode")
                    return {'error': 'LinkedIn 2FA required - please login manually in browser first'}
                else:
                    print(f"[WARN] Login status unclear, URL: {current_url}")
            
            except Exception as login_error:
                print(f"[ERROR] LinkedIn login failed: {str(login_error)}")
                return {'error': f'LinkedIn login failed: {str(login_error)}'}
        else:
            print("[SCRAPER] Already logged in to LinkedIn")
        
        # Now navigate to search URL
        print(f"[SCRAPER] Navigating to search results...")
        driver.get(url)
        time.sleep(5)
        
        # Scroll to load more posts with error handling
        for i in range(scrolls):
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                print(f"[SCRAPER] Scroll {i+1}/{scrolls}")
            except (urllib3.exceptions.ProtocolError, http.client.RemoteDisconnected) as scroll_error:
                print(f"[WARN] Scroll error on attempt {i+1}, Chrome may have crashed. Trying to recover...")
                try:
                    # Try to check if browser is still alive
                    driver.current_url
                    print(f"[SCRAPER] Browser still responsive, continuing...")
                except:
                    print(f"[ERROR] Browser crashed, stopping scroll at {i+1}/{scrolls}")
                    break
            except Exception as e:
                print(f"[WARN] Unexpected scroll error: {e}")
                break
        
        # Extract job posts
        posts = driver.find_elements(By.CSS_SELECTOR, ".feed-shared-update-v2")
        print(f"[SCRAPER] Found {len(posts)} posts")
        
        for post in posts:
            try:
                # Extract job information
                text_content = post.text
                
                # Look for email addresses
                import re
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text_content)
                
                if emails:
                    jobs_found += 1
                    recruiter_email = emails[0]
                    
                    # Extract company and title
                    company = extract_company_from_email(recruiter_email)
                    
                    # Try to find job title in text
                    title_match = re.search(r'(hiring|looking for|seeking)\s+([^\.]+)', text_content, re.IGNORECASE)
                    title = title_match.group(2).strip() if title_match else f"{search_role} Position"
                    
                    # Create job post object
                    job_post = {
                        'title': title[:100],
                        'company': company,
                        'location': 'Remote',
                        'job_url': url,
                        'recruiter_email': recruiter_email,
                        'email': recruiter_email,
                        'skills': skills,
                        'full_text': text_content[:500],
                        'posted_date': datetime.now().strftime("%Y-%m-%d")
                    }
                    
                    # Save to database (for ALL users, not just scheduler)
                    if save_job_post(job_post, user_email='all_users'):
                        jobs_saved += 1
                        print(f"[SCRAPER] Saved: {company} - {title}")
            
            except Exception as post_error:
                print(f"[SCRAPER] Error processing post: {str(post_error)}")
                continue
        
        print(f"[SCRAPER] Completed: {jobs_found} jobs found, {jobs_saved} saved to database")
        return {'jobs_found': jobs_found, 'jobs_saved': jobs_saved}
        
    except Exception as e:
        print(f"[SCRAPER] Error during scraping: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}
        
    finally:
        if driver:
            try:
                driver.quit()
                print("[SCRAPER] Chrome closed")
            except:
                pass

@app.route('/admin/scrape_jobs')
@admin_required
def admin_scrape_jobs():
    """Admin endpoint to scrape jobs without sending emails - SSE stream"""
    from flask import Response, stream_with_context
    import queue
    import threading
    
    def generate():
        # Create a queue for messages
        message_queue = queue.Queue()
        
        def send_event(msg):
            """Send SSE event"""
            message_queue.put(msg)
        
        def log(msg):
            """Log and send message"""
            print(msg)
            send_event(msg)
        
        # Get parameters
        custom_url = request.args.get('url', '').strip()
        skills = request.args.get('skills', '').strip()
        scrolls = int(request.args.get('scrolls', 10))
        
        # Use admin's session email instead of requiring user input
        user_email = session.get('user', 'admin@justmailit.in')
        
        # Build LinkedIn search URL based on skills (if custom URL not provided)
        if custom_url:
            url = custom_url
            log(f"📍 Using custom URL: {url}")
        elif skills:
            # Build search URL using skills like the main automation
            from urllib.parse import urlencode
            skill_list = parse_skills(skills)
            search_keywords = ' OR '.join(f'{skill.strip()} hiring' for skill in skill_list)
            
            base_url = "https://www.linkedin.com/search/results/content/?"
            params = {
                'datePosted': '"past-week"',
                'keywords': search_keywords
            }
            url = base_url + urlencode(params)
            log(f"[DEBUG] Built search URL for skills: {skills}")
            log(f"📍 Search URL: {url}")
        else:
            # Default to feed if no URL or skills provided
            url = 'https://www.linkedin.com/feed/'
            log(f"📍 Using default feed URL: {url}")
        
        def scrape_jobs_thread():
            """Background thread for scraping"""
            import time
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            driver = None
            try:
                log("[*] Starting admin job scraping...")
                log(f"[@] Admin user: {user_email}")
                log(f"📍 URL: {url}")
                log(f"🔢 Scrolls: {scrolls}")
                if skills:
                    log(f"🎯 Skills filter: {skills}")
                
                log("⚙️ Initializing Chrome driver...")
                
                # Initialize Chrome driver
                chrome_options = Options()
                
                # Set Chrome/Chromium binary location
                if os.environ.get('CHROME_BIN'):  # Docker/Cloud environment - use Chromium
                    chrome_options.binary_location = os.environ.get('CHROME_BIN', '/usr/bin/chromium')
                    log(f"[DOCKER] Using Chromium binary: {chrome_options.binary_location}")
                
                # Only use headless mode if HEADLESS environment variable is not set to "false"
                if os.environ.get('HEADLESS', 'true').lower() != 'false':
                    chrome_options.add_argument("--headless=new")
                    log("🔇 Running Chrome in headless mode")
                else:
                    log("[VISIBLE] Running Chrome in visible mode")
                
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--dns-prefetch-disable")
                chrome_options.add_argument("--disable-features=VizDisplayCompositor")
                
                # Use appropriate profile directory based on environment
                if os.environ.get('CHROME_BIN'):  # Docker/Cloud environment
                    profile_dir = "/tmp/chrome-profile"
                    log("[WWW] Using Docker Chrome profile directory")
                else:  # Local Windows environment
                    profile_dir = r"D:\Profile"
                    log("🏠 Using Windows Chrome profile directory")
                
                os.makedirs(profile_dir, exist_ok=True)
                chrome_options.add_argument(f"--user-data-dir={profile_dir}")
                log(f"🗂 Using Chrome profile directory: {profile_dir}")
                
                chrome_options.page_load_strategy = 'normal'
                
                log("[WWW] Launching Chrome...")
                
                # Use explicit ChromeDriver path in Docker/Cloud, auto-install locally
                if os.environ.get('CHROMEDRIVER_PATH'):
                    chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
                    log(f"[INSTALL] Using ChromeDriver from: {chromedriver_path}")
                    from selenium.webdriver.chrome.service import Service
                    service = Service(chromedriver_path)
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    from webdriver_manager.chrome import ChromeDriverManager
                    from selenium.webdriver.chrome.service import Service
                    log("🔄 Installing ChromeDriver via webdriver_manager...")
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                
                log("[OK] Chrome launched successfully!")
                
                # Login check: Try existing profile first
                log("[AUTH] Checking LinkedIn login status...")
                log("[DEBUG] Navigating to LinkedIn feed...")
                
                driver.get("https://www.linkedin.com/feed/")
                log(f"[OK] Page loaded, current URL: {driver.current_url}")
                time.sleep(5)  # Wait for page to settle
                
                # Check for multiple indicators of being logged in
                login_indicators = [
                    ".global-nav__me",
                    ".feed-identity-module",
                    "[data-control-name='nav.settings_and_privacy']",
                    ".nav-item__profile-member-photo"
                ]
                
                logged_in = False
                for indicator in login_indicators:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, indicator)
                        if elements:
                            logged_in = True
                            log(f"[OK] Login confirmed via indicator: {indicator}")
                            break
                    except:
                        continue
                
                # Check URL for redirect to login
                current_url = driver.current_url
                if "login" in current_url or "authwall" in current_url:
                    logged_in = False
                    log("[WARN] Redirected to login page")
                
                if logged_in:
                    log("[OK] ✓ Already logged in via existing profile!")
                else:
                    log("[LOGIN] Profile not logged in, attempting credential login...")
                    
                    # Get LinkedIn credentials from environment or database
                    linkedin_email = os.environ.get('LINKEDIN_EMAIL')
                    linkedin_password = os.environ.get('LINKEDIN_PASSWORD')
                    
                    if not linkedin_email or not linkedin_password:
                        # Try database
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute('SELECT linkedin_email, linkedin_password FROM user_profiles WHERE email = ?', (user_email,))
                        creds = cursor.fetchone()
                        conn.close()
                        
                        if creds and creds['linkedin_email'] and creds['linkedin_password']:
                            linkedin_email = creds['linkedin_email']
                            linkedin_password = creds['linkedin_password']
                    
                    if linkedin_email and linkedin_password:
                        try:
                            log("[LOGIN] Navigating to login page...")
                            driver.get("https://www.linkedin.com/login")
                            time.sleep(2)
                            
                            log("[LOGIN] Entering credentials...")
                            email_field = driver.find_element(By.ID, "username")
                            email_field.send_keys(linkedin_email)
                            
                            password_field = driver.find_element(By.ID, "password")
                            password_field.send_keys(linkedin_password)
                            
                            login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                            login_btn.click()
                            
                            log("[LOGIN] Waiting for login...")
                            time.sleep(8)  # Wait longer for login
                            
                            # Verify login success
                            current_url = driver.current_url
                            if "feed" in current_url or "checkpoint" in current_url:
                                log("[OK] ✓ Login successful!")
                                
                                # Handle 2FA if needed
                                if "checkpoint" in current_url:
                                    log("[2FA] Two-factor authentication required")
                                    log("[2FA] Please complete 2FA in the browser...")
                                    log("[2FA] Waiting 60 seconds for manual verification...")
                                    time.sleep(60)
                            else:
                                log(f"[WARN] Login unclear, current URL: {current_url}")
                        
                        except Exception as login_error:
                            log(f"[ERROR] Login error: {str(login_error)}")
                            log("[INFO] Continuing with current session...")
                    else:
                        log("[WARN] No LinkedIn credentials found")
                        log("[INFO] Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD env vars")
                        log("[INFO] Or add credentials in user profile")
                
                # Now navigate to target URL
                log(f"🔗 Navigating to: {url}")
                driver.get(url)
                time.sleep(5)
                
                # Scroll and collect posts
                log(f"[SCROLL] Starting to scroll ({scrolls} times)...")
                last_height = driver.execute_script("return document.body.scrollHeight")
                no_change_count = 0
                
                for i in range(scrolls):
                    try:
                        # Scroll up a bit first to trigger lazy loading
                        current_scroll = driver.execute_script("return window.pageYOffset")
                        driver.execute_script(f"window.scrollTo(0, {current_scroll - 100});")
                        time.sleep(0.5)
                        
                        # Now scroll to bottom
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(4)  # Increased wait time for content to load
                        
                        new_height = driver.execute_script("return document.body.scrollHeight")
                        log(f"[SCROLL] Scrolling... ({i+1}/{scrolls}) - Height: {new_height}")
                        
                        if new_height == last_height:
                            no_change_count += 1
                            log(f"[SCROLL] No new content loaded (attempt {no_change_count}/3)")
                            if no_change_count >= 3:
                                log("[OK] Reached end of feed after 3 attempts")
                                break
                            # Try waiting longer and scroll again
                            time.sleep(2)
                        else:
                            no_change_count = 0  # Reset counter when new content loads
                            last_height = new_height
                    except (urllib3.exceptions.ProtocolError, http.client.RemoteDisconnected):
                        log(f"[WARN] Connection lost during scroll {i+1}, checking browser...")
                        try:
                            driver.current_url
                            log("[OK] Browser recovered, continuing...")
                        except:
                            log("[ERROR] Browser crashed, stopping scroll")
                            break
                    except Exception as e:
                        log(f"[ERROR] Scroll error: {e}")
                        break
                
                log("[WAIT] Waiting for posts to load...")
                wait = WebDriverWait(driver, 20)
                
                # Try multiple selectors for job posts
                selectors = [
                    ".feed-shared-update-v2",
                    "article.ember-view",
                    ".update-components-actor",
                    ".social-details-social-activity"
                ]
                
                job_posts = []
                for selector in selectors:
                    try:
                        elements = wait.until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                        )
                        if elements:
                            log(f"[OK] Found {len(elements)} posts using selector: {selector}")
                            job_posts = elements
                            break
                    except Exception as e:
                        log(f"[WARN] Selector {selector} failed")
                        continue
                
                if not job_posts:
                    log("[ERROR] No job posts found")
                    send_event("completed")
                    return
                
                all_emails = set()
                jobs_saved = 0
                
                log(f"[DEBUG] Scanning {len(job_posts)} posts for job opportunities...")
                
                for idx, post in enumerate(job_posts):
                    try:
                        # Extract post content
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
                        
                        if not title_elem:
                            continue
                        
                        title = title_elem.text
                        full_text = title
                        
                        # Filter by skills if provided (additional filtering on top of search)
                        if skills and not custom_url:
                            # If we built the search URL, jobs should already be filtered
                            # This is just an additional check
                            skill_list = [s.strip().lower() for s in parse_skills(skills)]
                            if not any(skill in full_text.lower() for skill in skill_list):
                                continue
                        
                        # Extract company
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
                        description = full_text[:200] + "..." if len(full_text) > 200 else full_text
                        
                        # Find mailto links
                        mailtos = post.find_elements(By.XPATH, ".//a[contains(@href, 'mailto:')]")
                        
                        for m in mailtos:
                            email = m.get_attribute("href").replace("mailto:", "")
                            all_emails.add(email)
                            
                            # Save job post for ALL USERS (visible to everyone)
                            job_post = {
                                "title": title,
                                "company": company,
                                "description": description,
                                "full_text": full_text,
                                "email": email,
                                "location": "Remote/On-site",
                                "job_type": "Full-time",
                                "posted_date": datetime.now().strftime("%Y-%m-%d"),
                                "url": url,
                                "job_url": url,
                                "skills": parse_skills(skills) if skills else []
                            }
                            
                            # Save for the specified user AND make it visible to all users
                            save_job_post(job_post, user_email)
                            # Also save without user_email so it appears for everyone
                            save_job_post(job_post, None)
                            jobs_saved += 1
                            log(f"[SAVE] Saved job from {company} - {email} (visible to all users)")
                    
                    except Exception as e:
                        continue
                
                log(f"[EMAIL] Found {len(all_emails)} unique email(s)")
                log(f"[SAVE] Saved {jobs_saved} job post(s) to database (visible to all users)")
                log("[OK] Automation completed!")
                send_event("completed")
                
            except Exception as e:
                error_msg = f"[ERROR] Error: {str(e)}"
                log(error_msg)
                print(f"ADMIN SCRAPING ERROR: {str(e)}")
                import traceback
                traceback.print_exc()
                send_event("error")
            
            finally:
                if driver:
                    try:
                        driver.quit()
                        log("[DONE] Browser closed")
                    except:
                        pass
        
        # Start scraping in background thread
        thread = threading.Thread(target=scrape_jobs_thread)
        thread.daemon = True
        thread.start()
        
        # Stream messages from queue
        while True:
            try:
                msg = message_queue.get(timeout=1)
                yield f"data: {msg}\n\n"
                
                if msg in ['completed', 'error']:
                    break
            except queue.Empty:
                # Check if thread is still alive
                if not thread.is_alive():
                    break
                continue
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


# ========== ADMIN SCHEDULED JOBS ROUTES ==========

@app.route('/admin/scheduled_jobs')
@admin_required
def admin_scheduled_jobs():
    """Admin page to manage scheduled jobs"""
    try:
        jobs = db.get_all_scheduled_jobs()
        return render_template('admin_scheduled_jobs.html', jobs=jobs)
    except Exception as e:
        print(f"[ERROR] Failed to load scheduled jobs: {str(e)}")
        flash(f"Error loading scheduled jobs: {str(e)}", "danger")
        return redirect(url_for('admin_panel'))

@app.route('/admin/scheduled_jobs/create', methods=['POST'])
@admin_required
def create_scheduled_job():
    """Create a new scheduled job"""
    try:
        job_name = request.form.get('job_name', '').strip()
        search_role = request.form.get('search_role', '').strip()
        position = request.form.get('position', '').strip()
        cron_expression = request.form.get('cron_expression', '').strip()
        
        if not all([job_name, search_role, cron_expression]):
            return jsonify({'success': False, 'message': 'Job name, search role, and cron expression are required'}), 400
        
        # Validate cron expression format (basic validation)
        cron_parts = cron_expression.split()
        if len(cron_parts) != 5:
            return jsonify({'success': False, 'message': 'Invalid cron expression. Format: minute hour day month weekday'}), 400
        
        admin_email = session.get('user')
        job_id = db.create_scheduled_job(job_name, search_role, position, cron_expression, admin_email)
        
        print(f"[OK] Created scheduled job #{job_id}: {job_name}")
        return jsonify({'success': True, 'message': f'Scheduled job created successfully', 'job_id': job_id})
        
    except Exception as e:
        print(f"[ERROR] Failed to create scheduled job: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/scheduled_jobs/<int:job_id>/toggle', methods=['POST'])
@admin_required
def toggle_scheduled_job(job_id):
    """Toggle scheduled job active status"""
    try:
        is_active = request.json.get('is_active', True)
        db.update_scheduled_job(job_id, is_active=is_active)
        
        status = 'activated' if is_active else 'deactivated'
        print(f"[OK] Scheduled job #{job_id} {status}")
        return jsonify({'success': True, 'message': f'Job {status} successfully'})
        
    except Exception as e:
        print(f"[ERROR] Failed to toggle scheduled job: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/scheduled_jobs/<int:job_id>/update', methods=['POST'])
@admin_required
def update_scheduled_job_route(job_id):
    """Update a scheduled job"""
    try:
        job_name = request.form.get('job_name')
        search_role = request.form.get('search_role')
        position = request.form.get('position')
        cron_expression = request.form.get('cron_expression')
        
        # Validate cron expression if provided
        if cron_expression:
            cron_parts = cron_expression.split()
            if len(cron_parts) != 5:
                return jsonify({'success': False, 'message': 'Invalid cron expression'}), 400
        
        db.update_scheduled_job(job_id, job_name=job_name, search_role=search_role, 
                               position=position, cron_expression=cron_expression)
        
        print(f"[OK] Updated scheduled job #{job_id}")
        return jsonify({'success': True, 'message': 'Job updated successfully'})
        
    except Exception as e:
        print(f"[ERROR] Failed to update scheduled job: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/scheduled_jobs/<int:job_id>/delete', methods=['DELETE'])
@admin_required
def delete_scheduled_job(job_id):
    """Delete a scheduled job"""
    try:
        db.delete_scheduled_job(job_id)
        print(f"[OK] Deleted scheduled job #{job_id}")
        return jsonify({'success': True, 'message': 'Job deleted successfully'})
        
    except Exception as e:
        print(f"[ERROR] Failed to delete scheduled job: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/scheduled_jobs/<int:job_id>/run_now', methods=['POST'])
@admin_required
def run_scheduled_job_now(job_id):
    """Manually trigger a scheduled job to run immediately"""
    try:
        jobs = db.get_all_scheduled_jobs()
        job = next((j for j in jobs if j['id'] == job_id), None)
        
        if not job:
            return jsonify({'success': False, 'message': 'Job not found'}), 404
        
        # Run job in background thread
        def run_job():
            try:
                from app import scrape_jobs_thread
                print(f"[CRON] Manually running scheduled job #{job_id}: {job['job_name']}")
                
                # Run scraping for this job's search criteria
                scrape_jobs_thread(
                    search_role=job['search_role'],
                    search_time='past-week',
                    user_email='admin@justmailit.in'
                )
                
                # Update last run time
                from datetime import datetime, timedelta
                from croniter import croniter
                now = datetime.now()
                cron = croniter(job['cron_expression'], now)
                next_run = cron.get_next(datetime)
                
                db.update_job_run_info(job_id, now, next_run)
                print(f"[OK] Scheduled job #{job_id} completed")
                
            except Exception as e:
                print(f"[ERROR] Failed to run scheduled job #{job_id}: {str(e)}")
        
        thread = threading.Thread(target=run_job, daemon=True)
        thread.start()
        
        return jsonify({'success': True, 'message': 'Job started in background'})
        
    except Exception as e:
        print(f"[ERROR] Failed to run scheduled job: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == "__main__":
    import sys
    # Force unbuffered output
    sys.stdout.flush()
    sys.stderr.flush()
    
    # Start the cron scheduler
    start_scheduler()
    
    # Get port from environment variable (Render provides this)
    port = int(os.environ.get("PORT", 5000))
    print(f"\n{'='*60}")
    print(f"[*] SERVER STARTING ON PORT {port}")
    print(f"{'='*60}\n")
    # Use 0.0.0.0 to accept connections from all interfaces
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
