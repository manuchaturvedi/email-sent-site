"""
LinkedIn Job Scraper - Standalone Script
=========================================
Scrapes LinkedIn job posts and saves them to a local SQLite database.
You can then transfer the database file to Raspberry Pi.

Requirements:
- Python 3.8+
- selenium
- python-dotenv (optional)

Setup:
1. pip install selenium python-dotenv
2. Download ChromeDriver: https://chromedriver.chromium.org/
3. Set environment variables or edit config below
4. Run: python linkedin_job_scraper.py

Usage:
    python linkedin_job_scraper.py --role "Python Developer" --scrolls 10
"""

import os
import sys
import time
import sqlite3
import re
import argparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlencode

# ==================== CONFIGURATION ====================

# Database configuration
DB_PATH = "linkedin_jobs.db"  # Local database file

# Chrome/ChromeDriver paths (edit these if needed)
CHROME_BINARY = None  # Leave None for auto-detect, or set path like: r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROMEDRIVER_PATH = None  # Leave None for auto-detect, or set path like: r"C:\chromedriver.exe"

# Chrome profile directory (to persist LinkedIn login session)
CHROME_PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome-profile")

# LinkedIn credentials (optional - can set via environment variables)
LINKEDIN_EMAIL = os.environ.get('LINKEDIN_EMAIL', 'manudrive04@gmail.com')
LINKEDIN_PASSWORD = os.environ.get('LINKEDIN_PASSWORD', 'Jpking@232')

# ==================== DATABASE FUNCTIONS ====================

def init_database():
    """Initialize SQLite database with job_posts table"""
    print(f"📂 Initializing database: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create job_posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT DEFAULT 'scraper',
            title TEXT,
            company TEXT,
            location TEXT,
            job_url TEXT,
            recruiter_email TEXT,
            skills TEXT,
            full_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create index for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_recruiter_email 
        ON job_posts(recruiter_email)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_created_at 
        ON job_posts(created_at DESC)
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def is_duplicate_job(recruiter_email, job_text):
    """Check if job post already exists in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check by recruiter email
    if recruiter_email:
        cursor.execute('''
            SELECT id FROM job_posts 
            WHERE recruiter_email = ? 
            AND datetime(created_at) > datetime('now', '-7 days')
        ''', (recruiter_email,))
        
        if cursor.fetchone():
            conn.close()
            return True
    
    # Check by similar text (first 100 chars)
    if job_text and len(job_text) > 100:
        text_snippet = job_text[:100]
        cursor.execute('''
            SELECT id FROM job_posts 
            WHERE substr(full_text, 1, 100) = ?
            AND datetime(created_at) > datetime('now', '-7 days')
        ''', (text_snippet,))
        
        if cursor.fetchone():
            conn.close()
            return True
    
    conn.close()
    return False

def save_job_to_db(job_data):
    """Save job post to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO job_posts 
            (user_email, title, company, location, job_url, recruiter_email, skills, full_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job_data.get('user_email', 'manuchaturvedi28mc@gmail.com'),
            job_data.get('title', ''),
            job_data.get('company', ''),
            job_data.get('location', ''),
            job_data.get('job_url', ''),
            job_data.get('recruiter_email', ''),
            job_data.get('skills', ''),
            job_data.get('full_text', '')
        ))
        
        conn.commit()
        job_id = cursor.lastrowid
        conn.close()
        return job_id
        
    except Exception as e:
        print(f"❌ Error saving job to database: {e}")
        conn.close()
        return None

def get_job_stats():
    """Get statistics about scraped jobs"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total jobs
    cursor.execute("SELECT COUNT(*) FROM job_posts")
    total = cursor.fetchone()[0]
    
    # Jobs today
    cursor.execute('''
        SELECT COUNT(*) FROM job_posts 
        WHERE date(created_at) = date('now')
    ''')
    today = cursor.fetchone()[0]
    
    # Jobs this week
    cursor.execute('''
        SELECT COUNT(*) FROM job_posts 
        WHERE datetime(created_at) > datetime('now', '-7 days')
    ''')
    this_week = cursor.fetchone()[0]
    
    # Jobs with email
    cursor.execute('''
        SELECT COUNT(*) FROM job_posts 
        WHERE recruiter_email IS NOT NULL AND recruiter_email != ''
    ''')
    with_email = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total,
        'today': today,
        'this_week': this_week,
        'with_email': with_email
    }

# ==================== SCRAPING FUNCTIONS ====================

def extract_company_from_email(email):
    """Extract company name from email address"""
    if not email:
        return None
    
    # Get domain part
    domain = email.split('@')[1] if '@' in email else email
    
    # Remove common TLDs
    company = domain.split('.')[0]
    
    # Capitalize
    return company.capitalize()

def parse_skills(search_role):
    """Parse search role into list of skills/keywords"""
    if not search_role:
        return []
    
    # Split by common separators
    skills = re.split(r'[,|/]', search_role)
    return [s.strip() for s in skills if s.strip()]

def setup_chrome_driver(headless=True):
    """Setup and return Chrome WebDriver"""
    print("🔧 Setting up Chrome WebDriver...")
    
    chrome_options = Options()
    
    # Set Chrome binary location if specified
    if CHROME_BINARY:
        chrome_options.binary_location = CHROME_BINARY
        print(f"   Using Chrome: {CHROME_BINARY}")
    
    # Headless mode
    if headless:
        chrome_options.add_argument("--headless=new")
        print("   Mode: Headless")
    else:
        print("   Mode: Visible browser")
    
    # Common Chrome arguments
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    
    # User agent to avoid detection
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Use persistent profile directory to keep login session
    os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)
    chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
    print(f"   Profile: {CHROME_PROFILE_DIR}")
    
    # Launch Chrome
    try:
        if CHROMEDRIVER_PATH:
            from selenium.webdriver.chrome.service import Service
            service = Service(CHROMEDRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print(f"   ChromeDriver: {CHROMEDRIVER_PATH}")
        else:
            driver = webdriver.Chrome(options=chrome_options)
            print("   ChromeDriver: Auto-detected")
        
        print("✅ Chrome WebDriver ready")
        return driver
        
    except Exception as e:
        print(f"❌ Failed to setup Chrome WebDriver: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Install ChromeDriver: https://chromedriver.chromium.org/")
        print("   2. Make sure Chrome browser is installed")
        print("   3. Set CHROMEDRIVER_PATH variable in this script")
        print("   4. Or use: pip install webdriver-manager")
        sys.exit(1)

def login_to_linkedin(driver):
    """Login to LinkedIn if not already logged in"""
    print("🔑 Checking LinkedIn login status...")
    
    driver.get("https://www.linkedin.com/feed")
    time.sleep(3)
    
    current_url = driver.current_url
    
    if "login" in current_url or "authwall" in current_url:
        print("   Not logged in, attempting login...")
        
        if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
            print("\n❌ LinkedIn credentials not configured!")
            print("   Option 1: Set environment variables:")
            print("      export LINKEDIN_EMAIL='your@email.com'")
            print("      export LINKEDIN_PASSWORD='yourpassword'")
            print("\n   Option 2: Edit script and set LINKEDIN_EMAIL and LINKEDIN_PASSWORD")
            print("\n   Option 3: Login manually in browser with profile directory:")
            print(f"      chrome --user-data-dir={CHROME_PROFILE_DIR}")
            return False
        
        try:
            driver.get("https://www.linkedin.com/login")
            time.sleep(3)
            
            # Wait for login form
            wait = WebDriverWait(driver, 10)
            
            # Enter email
            email_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
            email_field.clear()
            email_field.send_keys(LINKEDIN_EMAIL)
            print("   ✓ Email entered")
            
            # Enter password
            password_field = driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(LINKEDIN_PASSWORD)
            print("   ✓ Password entered")
            
            # Click sign in
            sign_in_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            sign_in_button.click()
            print("   ✓ Sign in clicked")
            
            # Wait for login to complete
            time.sleep(5)
            
            # Check if login was successful
            current_url = driver.current_url
            if "feed" in current_url or "home" in current_url:
                print("✅ LinkedIn login successful!")
                return True
            elif "checkpoint" in current_url or "challenge" in current_url:
                print("⚠️  LinkedIn requires 2FA/verification")
                print("   Please login manually in browser first:")
                print(f"   chrome --user-data-dir={CHROME_PROFILE_DIR}")
                return False
            else:
                print(f"⚠️  Login status unclear, URL: {current_url}")
                return False
                
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False
    else:
        print("✅ Already logged in to LinkedIn")
        return True

def scrape_linkedin_jobs(search_role, search_time='past-week', scrolls=10, headless=True):
    """
    Main scraping function
    
    Args:
        search_role: Job role/keywords to search for (e.g. "Python Developer, Django, Flask")
        search_time: Time period - 'past-24-hours', 'past-week', 'past-month'
        scrolls: Number of times to scroll down (more scrolls = more posts)
        headless: Run Chrome in headless mode (True) or visible (False)
    
    Returns:
        dict with results
    """
    driver = None
    jobs_found = 0
    jobs_saved = 0
    errors = []
    
    try:
        print("\n" + "="*60)
        print(f"🚀 STARTING JOB SCRAPING")
        print("="*60)
        print(f"Search Role: {search_role}")
        print(f"Time Period: {search_time}")
        print(f"Scrolls: {scrolls}")
        print(f"Database: {os.path.abspath(DB_PATH)}")
        print("="*60 + "\n")
        
        # Initialize database
        init_database()
        
        # Build LinkedIn search URL
        skills = parse_skills(search_role)
        search_keywords = ' OR '.join(f'{role.strip()} hiring' for role in skills)
        base_url = "https://www.linkedin.com/search/results/content/?"
        params = {
            'datePosted': f'"{search_time}"',
            'keywords': search_keywords
        }
        url = base_url + urlencode(params)
        print(f"🔍 Search URL: {url}\n")
        
        # Setup Chrome driver
        driver = setup_chrome_driver(headless=headless)
        
        # Login to LinkedIn
        if not login_to_linkedin(driver):
            print("\n❌ Cannot proceed without LinkedIn login")
            return {
                'success': False,
                'error': 'LinkedIn login required',
                'jobs_found': 0,
                'jobs_saved': 0
            }
        
        # Navigate to search results
        print(f"\n🔍 Navigating to search results...")
        driver.get(url)
        time.sleep(5)
        
        # Scroll to load more posts with dynamic wait
        print(f"\n📜 Scrolling to load posts...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        
        for i in range(scrolls):
            try:
                # Check stop flag
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)  # Wait for content to load
                
                # Calculate new scroll height
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    # If heights are the same, content might be fully loaded
                    break
                
                last_height = new_height
                scroll_attempts += 1
                print(f"   Scroll {i+1}/{scrolls}")
            except Exception as e:
                print(f"   ⚠️  Scroll error: {e}")
                break
        
        print(f"\n📊 Extracting job posts...")
        
        # Wait for posts to load
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        print("   🔍 Waiting for posts to load...")
        time.sleep(5)  # Extra wait for content
        
        # Try multiple possible selectors for job posts (same as real scraper)
        selectors = [
            ".feed-shared-update-v2",
            "article.ember-view",
            ".update-components-actor",
            ".social-details-social-activity"
        ]
        
        posts = []
        for selector in selectors:
            try:
                print(f"   🔍 Trying selector: {selector}")
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"   📊 Found {len(elements)} elements with {selector}")
                if elements and len(elements) > posts.__len__():
                    posts = elements
                    print(f"   ✅ Using {len(posts)} posts from selector: {selector}")
            except Exception as e:
                print(f"   ⚠️  Selector {selector} error: {e}")
                continue
        
        # If still no posts, try getting all visible text elements
        if not posts or len(posts) < 10:
            print("   ⚠️  Not enough posts found with selectors, trying alternative method...")
            try:
                # Get all divs that might be posts
                all_divs = driver.find_elements(By.XPATH, "//div[contains(@class, 'feed') or contains(@class, 'update') or contains(@class, 'post')]")
                print(f"   📊 Found {len(all_divs)} potential post divs")
                if len(all_divs) > len(posts):
                    posts = all_divs
                    print(f"   ✅ Using {len(posts)} posts from alternative method")
            except Exception as e:
                print(f"   ❌ Alternative method failed: {e}")
        
        if not posts:
            print("   ❌ No job posts found with any selector")
            return {
                'success': False,
                'error': 'No posts found',
                'jobs_found': 0,
                'jobs_saved': 0
            }
        
        print(f"   Found {len(posts)} posts total\n")
        
        # Process each post
        for idx, post in enumerate(posts, 1):
            try:
                # Get post text content and HTML
                text_content = post.text
                html_content = ""
                try:
                    html_content = post.get_attribute('innerHTML')
                except:
                    pass
                
                # Extract emails from text (method 1)
                text_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text_content)
                
                # Extract emails from HTML (method 2)
                html_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html_content) if html_content else []
                
                # Find mailto links in the post (method 3 - most reliable)
                mailto_emails = []
                try:
                    mailtos = post.find_elements(By.XPATH, ".//a[contains(@href, 'mailto:')]")
                    for m in mailtos:
                        email = m.get_attribute("href").replace("mailto:", "").split('?')[0]  # Remove query params
                        mailto_emails.append(email)
                except:
                    pass
                
                # Combine all methods and deduplicate
                all_emails_in_post = list(set(text_emails + html_emails + mailto_emails))
                
                if all_emails_in_post:
                    jobs_found += 1
                    recruiter_email = all_emails_in_post[0]  # Take first email
                    
                    # Check for duplicates
                    if is_duplicate_job(recruiter_email, text_content):
                        print(f"   [{idx}] ⏭️  Skipped (duplicate): {recruiter_email}")
                        continue
                    
                    # Extract company from email
                    company = extract_company_from_email(recruiter_email)
                    
                    # Try to get post URL
                    try:
                        post_link = post.find_element(By.CSS_SELECTOR, "a[href*='/posts/']")
                        job_url = post_link.get_attribute('href')
                    except:
                        job_url = url
                    
                    # Extract title (first line or truncate)
                    title_parts = text_content.split('\n')
                    title = title_parts[0][:100] if title_parts else "Job Post"
                    
                    # Prepare job data
                    job_data = {
                        'user_email': 'manuchaturvedi28mc@gmail.com',
                        'title': title,
                        'company': company,
                        'location': '',  # Could extract from text
                        'job_url': job_url,
                        'recruiter_email': recruiter_email,
                        'skills': search_role,
                        'full_text': text_content
                    }
                    
                    # Save to database
                    job_id = save_job_to_db(job_data)
                    
                    if job_id:
                        jobs_saved += 1
                        print(f"   [{idx}] ✅ Saved: {recruiter_email} @ {company}")
                    else:
                        print(f"   [{idx}] ❌ Failed to save: {recruiter_email}")
                        
            except Exception as e:
                error_msg = f"Error processing post {idx}: {e}"
                errors.append(error_msg)
                print(f"   [{idx}] ⚠️  {error_msg}")
        
        # Final stats
        print("\n" + "="*60)
        print("📊 SCRAPING COMPLETED")
        print("="*60)
        print(f"Posts Processed: {len(posts)}")
        print(f"Jobs Found (with email): {jobs_found}")
        print(f"Jobs Saved (new): {jobs_saved}")
        print(f"Errors: {len(errors)}")
        
        # Database stats
        db_stats = get_job_stats()
        print("\n📈 Database Statistics:")
        print(f"   Total Jobs: {db_stats['total']}")
        print(f"   Today: {db_stats['today']}")
        print(f"   This Week: {db_stats['this_week']}")
        print(f"   With Email: {db_stats['with_email']}")
        print("="*60 + "\n")
        
        return {
            'success': True,
            'jobs_found': jobs_found,
            'jobs_saved': jobs_saved,
            'errors': errors,
            'db_stats': db_stats
        }
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        
        return {
            'success': False,
            'error': str(e),
            'jobs_found': jobs_found,
            'jobs_saved': jobs_saved,
            'errors': errors
        }
        
    finally:
        # Close browser
        if driver:
            print("\n🔒 Closing browser...")
            try:
                driver.quit()
                print("✅ Browser closed")
            except:
                pass

# ==================== MAIN ====================

def main():
    """Main function with CLI arguments"""
    parser = argparse.ArgumentParser(
        description='LinkedIn Job Scraper - Scrape job posts to local database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python linkedin_job_scraper.py --role "Python Developer"
  python linkedin_job_scraper.py --role "Django, Flask, FastAPI" --scrolls 15
  python linkedin_job_scraper.py --role "DevOps Engineer" --time past-24-hours --visible
  
After scraping:
  - Database file: linkedin_jobs.db
  - Transfer to Pi: scp linkedin_jobs.db pi@192.168.1.x:/path/to/justmailit.db
  - Or merge databases using SQL commands
        """
    )
    
    parser.add_argument('--role', type=str, default='Python Developer',
                        help='Job role/keywords to search (e.g. "Python Developer, Django")')
    parser.add_argument('--time', type=str, default='past-week',
                        choices=['past-24-hours', 'past-week', 'past-month'],
                        help='Time period for job posts')
    parser.add_argument('--scrolls', type=int, default=10,
                        help='Number of scrolls to load more posts (default: 10)')
    parser.add_argument('--visible', action='store_true',
                        help='Run Chrome in visible mode (not headless)')
    parser.add_argument('--stats', action='store_true',
                        help='Show database statistics only (no scraping)')
    
    args = parser.parse_args()
    
    # Show stats only
    if args.stats:
        if not os.path.exists(DB_PATH):
            print(f"❌ Database not found: {DB_PATH}")
            print("   Run scraper first to create database")
            return
        
        print("\n" + "="*60)
        print("📊 DATABASE STATISTICS")
        print("="*60)
        print(f"Database: {os.path.abspath(DB_PATH)}")
        
        db_stats = get_job_stats()
        print(f"\nTotal Jobs: {db_stats['total']}")
        print(f"Today: {db_stats['today']}")
        print(f"This Week: {db_stats['this_week']}")
        print(f"With Email: {db_stats['with_email']}")
        print("="*60 + "\n")
        return
    
    # Run scraper
    result = scrape_linkedin_jobs(
        search_role=args.role,
        search_time=args.time,
        scrolls=args.scrolls,
        headless=not args.visible
    )
    
    # Exit code based on success
    sys.exit(0 if result['success'] else 1)

if __name__ == "__main__":
    main()
