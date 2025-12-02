# LinkedIn Job Scraper - Standalone

A pure Python script to scrape LinkedIn job posts and save them to a local SQLite database. Perfect for running on your Windows PC and then transferring to Raspberry Pi.

## 🎯 Features

- ✅ Standalone Python script - no Flask/web server needed
- ✅ Scrapes LinkedIn job posts with recruiter emails
- ✅ Saves to local SQLite database
- ✅ Duplicate detection (skips already saved jobs)
- ✅ Persistent Chrome profile (stays logged in)
- ✅ Headless or visible browser mode
- ✅ CLI arguments for easy automation
- ✅ Database statistics and reporting

## 📋 Requirements

```bash
pip install selenium python-dotenv
```

**ChromeDriver**: Download from https://chromedriver.chromium.org/
- Must match your Chrome browser version
- Add to PATH or set path in script

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd "c:\Users\windows 10\Desktop\AI_support"
pip install selenium python-dotenv
```

### 2. Download ChromeDriver

1. Check your Chrome version: `chrome://version`
2. Download matching ChromeDriver: https://chromedriver.chromium.org/downloads
3. Extract to a folder (e.g., `C:\chromedriver\chromedriver.exe`)
4. Either:
   - Add to PATH, OR
   - Edit `linkedin_job_scraper.py` line 27: `CHROMEDRIVER_PATH = r"C:\chromedriver\chromedriver.exe"`

### 3. Configure LinkedIn Credentials

**Option A: Environment Variables (Recommended)**
```bash
# PowerShell
$env:LINKEDIN_EMAIL = "your@email.com"
$env:LINKEDIN_PASSWORD = "yourpassword"
```

**Option B: Edit Script**
Edit `linkedin_job_scraper.py` lines 30-31:
```python
LINKEDIN_EMAIL = "your@email.com"
LINKEDIN_PASSWORD = "yourpassword"
```

**Option C: Manual Login (Most Secure)**
1. Run once in visible mode: `python linkedin_job_scraper.py --visible`
2. Login manually when browser opens
3. Chrome profile will save your session
4. Future runs will stay logged in

### 4. Run Scraper

```bash
# Basic scraping
python linkedin_job_scraper.py --role "Python Developer"

# Advanced options
python linkedin_job_scraper.py --role "Django, Flask, FastAPI" --scrolls 15 --time past-24-hours

# Visible browser (see what's happening)
python linkedin_job_scraper.py --role "DevOps Engineer" --visible

# Check database stats
python linkedin_job_scraper.py --stats
```

## 📖 Usage Examples

### Scrape Multiple Roles

```bash
# Python roles
python linkedin_job_scraper.py --role "Python Developer, Django, Flask"

# DevOps roles
python linkedin_job_scraper.py --role "DevOps Engineer, Kubernetes, Docker"

# Full Stack roles
python linkedin_job_scraper.py --role "Full Stack Developer, React, Node.js"
```

### Time Periods

```bash
# Last 24 hours (freshest jobs)
python linkedin_job_scraper.py --role "Python" --time past-24-hours

# Last week (default)
python linkedin_job_scraper.py --role "Python" --time past-week

# Last month (more results)
python linkedin_job_scraper.py --role "Python" --time past-month
```

### More Scrolling = More Jobs

```bash
# Default: 10 scrolls (~50-100 jobs)
python linkedin_job_scraper.py --role "Python"

# More scrolls = more jobs
python linkedin_job_scraper.py --role "Python" --scrolls 20

# Light scraping
python linkedin_job_scraper.py --role "Python" --scrolls 5
```

## 📊 Output

### Console Output
```
============================================================
🚀 STARTING JOB SCRAPING
============================================================
Search Role: Python Developer
Time Period: past-week
Scrolls: 10
Database: C:\Users\...\linkedin_jobs.db
============================================================

📂 Initializing database: linkedin_jobs.db
✅ Database initialized
🔧 Setting up Chrome WebDriver...
   Using Chrome: Auto-detected
   Mode: Headless
   Profile: C:\Users\...\chrome-profile
   ChromeDriver: Auto-detected
✅ Chrome WebDriver ready
🔑 Checking LinkedIn login status...
✅ Already logged in to LinkedIn

🔍 Navigating to search results...

📜 Scrolling to load posts...
   Scroll 1/10
   Scroll 2/10
   ...
   Scroll 10/10

📊 Extracting job posts...
   Found 87 posts total

   [1] ✅ Saved: recruiter@company.com @ Company
   [2] ⏭️  Skipped (duplicate): hr@example.com
   [3] ✅ Saved: jobs@startup.com @ Startup
   ...

============================================================
📊 SCRAPING COMPLETED
============================================================
Posts Processed: 87
Jobs Found (with email): 45
Jobs Saved (new): 38
Errors: 0

📈 Database Statistics:
   Total Jobs: 156
   Today: 38
   This Week: 98
   With Email: 145
============================================================
```

### Database File

**File**: `linkedin_jobs.db`  
**Location**: Same folder as script  
**Schema**:
```sql
CREATE TABLE job_posts (
    id INTEGER PRIMARY KEY,
    user_email TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    job_url TEXT,
    recruiter_email TEXT,
    skills TEXT,
    full_text TEXT,
    created_at TIMESTAMP,
    scraped_at TIMESTAMP
);
```

## 🔄 Transfer to Raspberry Pi

### Method 1: Replace Database (Simple)

```bash
# Stop your app on Pi first
ssh pi@192.168.1.x "docker stop justmailit-app"

# Transfer database
scp linkedin_jobs.db pi@192.168.1.x:/home/pi/justmailit.db

# Restart app
ssh pi@192.168.1.x "docker start justmailit-app"
```

### Method 2: Merge Databases (Keep Existing Data)

Use the provided merge script:

```bash
# Copy both databases to same location
scp linkedin_jobs.db pi@192.168.1.x:/tmp/

# Run merge script on Pi
ssh pi@192.168.1.x
cd /tmp
python3 merge_databases.py justmailit.db linkedin_jobs.db
```

See `merge_databases.py` in this folder.

### Method 3: SSH Transfer (Windows)

```powershell
# Using PowerShell
scp -P 8888 linkedin_jobs.db manu@localhost:/home/manu/justmailit/justmailit.db

# If you have your SSH setup
ssh -p 8888 manu@localhost "cd /home/manu/justmailit && docker restart justmailit-app"
```

## 🤖 Automation

### Windows Task Scheduler

1. Create batch file `scrape_jobs.bat`:
```batch
@echo off
cd "c:\Users\windows 10\Desktop\AI_support"
python linkedin_job_scraper.py --role "Python Developer" --scrolls 15
```

2. Open Task Scheduler
3. Create Basic Task
4. Schedule: Daily at 9 AM
5. Action: Start a program
6. Program: `c:\Users\windows 10\Desktop\AI_support\scrape_jobs.bat`

### Cron Job (if running on Linux/Pi)

```bash
# Run daily at 9 AM
0 9 * * * cd /home/user/scraper && python3 linkedin_job_scraper.py --role "Python" >> scraper.log 2>&1
```

### Python Script (Schedule)

```python
import schedule
import time
from linkedin_job_scraper import scrape_linkedin_jobs

def job():
    scrape_linkedin_jobs("Python Developer", scrolls=15)

schedule.every().day.at("09:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## 🛠️ Configuration

Edit the script directly for custom settings:

```python
# Line 24: Database file name
DB_PATH = "linkedin_jobs.db"

# Line 27: Chrome binary path (auto-detect if None)
CHROME_BINARY = None

# Line 28: ChromeDriver path (auto-detect if None)
CHROMEDRIVER_PATH = r"C:\chromedriver\chromedriver.exe"

# Line 31: Chrome profile directory
CHROME_PROFILE_DIR = os.path.join(os.path.dirname(__file__), "chrome-profile")

# Line 34-35: LinkedIn credentials
LINKEDIN_EMAIL = os.environ.get('LINKEDIN_EMAIL', '')
LINKEDIN_PASSWORD = os.environ.get('LINKEDIN_PASSWORD', '')
```

## 📈 Database Statistics

View stats anytime without scraping:

```bash
python linkedin_job_scraper.py --stats
```

Output:
```
============================================================
📊 DATABASE STATISTICS
============================================================
Database: C:\Users\...\linkedin_jobs.db

Total Jobs: 256
Today: 45
This Week: 178
With Email: 234
============================================================
```

## 🔍 Troubleshooting

### ChromeDriver Not Found

```
❌ Failed to setup Chrome WebDriver: 'chromedriver' executable needs to be in PATH
```

**Solution**: 
1. Download ChromeDriver: https://chromedriver.chromium.org/
2. Extract to folder
3. Edit script line 28: `CHROMEDRIVER_PATH = r"C:\path\to\chromedriver.exe"`

### Chrome Version Mismatch

```
SessionNotCreatedException: session not created: This version of ChromeDriver only supports Chrome version XX
```

**Solution**: Download ChromeDriver matching your Chrome version

### LinkedIn Login Failed

```
❌ LinkedIn credentials not configured!
```

**Solution**: Set environment variables or use manual login (--visible)

### No Jobs Found

```
Posts Processed: 43
Jobs Found (with email): 0
```

**Reason**: LinkedIn posts don't always have recruiter emails in text

**Solution**: 
- Try different search terms
- Increase scrolls: `--scrolls 20`
- Try different time period: `--time past-24-hours`

## 📁 Files Created

```
AI_support/
├── linkedin_job_scraper.py      # Main scraper script
├── linkedin_jobs.db              # SQLite database (created after first run)
├── chrome-profile/               # Chrome profile directory (login session)
│   └── [Chrome profile files]
├── merge_databases.py            # Database merge utility
└── SCRAPER_README.md            # This file
```

## 🎓 Advanced Usage

### Extract Specific Data

```python
import sqlite3

conn = sqlite3.connect('linkedin_jobs.db')
cursor = conn.cursor()

# Get all jobs from last week
cursor.execute('''
    SELECT title, company, recruiter_email, created_at 
    FROM job_posts 
    WHERE datetime(created_at) > datetime('now', '-7 days')
    ORDER BY created_at DESC
''')

for row in cursor.fetchall():
    print(row)

conn.close()
```

### Export to CSV

```python
import sqlite3
import csv

conn = sqlite3.connect('linkedin_jobs.db')
cursor = conn.cursor()

cursor.execute('SELECT * FROM job_posts')
rows = cursor.fetchall()
columns = [description[0] for description in cursor.description]

with open('jobs_export.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(columns)
    writer.writerows(rows)

conn.close()
print("✅ Exported to jobs_export.csv")
```

## 🆘 Support

If you encounter issues:

1. Check Chrome and ChromeDriver versions match
2. Try visible mode: `--visible` to see what's happening
3. Check LinkedIn login status
4. Verify database file permissions
5. Look at error messages in console

## 📝 License

Free to use and modify for personal projects.
