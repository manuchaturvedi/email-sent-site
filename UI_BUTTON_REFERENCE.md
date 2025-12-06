# 🎨 JustMailIt UI Button Reference Guide

**Complete overview of every button, form, and interactive element in the application**

**Last Updated:** December 6, 2025

---

## 📑 Table of Contents

1. [Landing Page](#landing-page)
2. [Authentication Modal](#authentication-modal)
3. [Dashboard](#dashboard)
4. [Profile Page](#profile-page)
5. [Jobs Page](#jobs-page)
6. [Automation Page](#automation-page)
7. [Sent Emails Page](#sent-emails-page)
8. [Subscription Page](#subscription-page)
9. [Settings Page](#settings-page)
10. [Navigation Menu](#navigation-menu)

---

## 🏠 Landing Page
**File:** `sendmail/templates/landing.html`  
**Route:** `GET /`

### Header/Navigation Buttons

| Button | Location | Visual | Action | Route/Function | Result |
|--------|----------|--------|--------|----------------|--------|
| **JustMailIt Logo** | Top left | <img> Logo image | Click → Reload homepage | `window.location.href='/'` | Refreshes landing page |
| **Get Started** | Top right navigation | Green gradient button | Opens login modal | `openLoginModal()` | Shows authentication modal |
| **Login** | Top right navigation | Text link | Opens login modal | `openLoginModal('signin')` | Shows sign-in form |

---

### Hero Section Buttons

| Button | Location | Visual | Action | Route/Function | Result |
|--------|----------|--------|--------|----------------|--------|
| **Get Started Free** | Hero center | Large gradient button with rocket icon | Opens signup modal | `openLoginModal()` | Shows authentication form (signup tab) |
| **Watch How It Works** | Hero center | Secondary outlined button | Scrolls to demo section | `href="#how-it-works"` | Smooth scroll to tutorial video |

---

### Feature Showcase Buttons

| Button | Location | Visual | Action | Route/Function | Result |
|--------|----------|--------|--------|----------------|--------|
| **Try It Free** | Bottom of features | Call-to-action button | Opens signup modal | `openLoginModal()` | Shows registration form |
| **View Pricing** | Pricing section | Link button | Scrolls to pricing | `href="#pricing"` | Jumps to pricing cards |

---

### Footer Buttons

| Button | Location | Visual | Action | Route/Function | Result |
|--------|----------|--------|--------|----------------|--------|
| **Twitter** | Footer social | <i class="bi-twitter"> icon | Opens Twitter | `href="https://twitter.com/..."` | New tab to Twitter |
| **LinkedIn** | Footer social | <i class="bi-linkedin"> icon | Opens LinkedIn | `href="https://linkedin.com/..."` | New tab to LinkedIn |
| **Facebook** | Footer social | <i class="bi-facebook"> icon | Opens Facebook | `href="https://facebook.com/..."` | New tab to Facebook |
| **Terms of Service** | Footer links | Text link | Opens terms page | `href="/terms"` | Navigate to terms |
| **Privacy Policy** | Footer links | Text link | Opens privacy page | `href="/privacy"` | Navigate to privacy |

---

## 🔐 Authentication Modal
**File:** `sendmail/templates/landing.html` (modal section)  
**Trigger:** Click "Get Started" or "Login" buttons

### Modal Controls

| Button | Location | Visual | Action | Function | Result |
|--------|----------|--------|--------|----------|--------|
| **Close (X)** | Top right corner | X icon in circle | Close modal | `closeLoginModal()` | Hides modal, returns to landing |
| **Sign In Tab** | Top of form | Tab button | Switch to sign-in | `switchAuthTab('signin')` | Shows sign-in form |
| **Sign Up Tab** | Top of form | Tab button | Switch to sign-up | `switchAuthTab('signup')` | Shows sign-up form |

---

### Sign In Form Buttons

| Button | Location | Visual | Action | Function | Result |
|--------|----------|--------|--------|----------|--------|
| **Sign In** | Below password field | Primary blue button | Submit login form | `handleSignIn(event)` → `POST /login` | Authenticates user, redirects to dashboard |
| **Forgot Password?** | Below password | Small text link | Open password reset | `handleForgotPassword()` | Sends Firebase password reset email |
| **Continue with Google** | Below divider | White button with Google icon | Google OAuth | `handleGoogleAuth()` | Firebase Google sign-in |
| **Continue with Facebook** | Below Google | Blue button with Facebook icon | Facebook OAuth | `handleFacebookAuth()` | Firebase Facebook sign-in |
| **Create Account** | Bottom text link | Inline link | Switch to signup | `switchAuthTab('signup')` | Shows sign-up form |

**Form Fields:**
- Email input: `<input id="signinEmail">`
- Password input: `<input id="signinPassword">`

**Submit Process:**
1. User enters email + password
2. Click "Sign In" → `handleSignIn()` called
3. Firebase authenticates: `auth.signInWithEmailAndPassword()`
4. Get Firebase token: `user.getIdToken()`
5. Send to backend: `POST /login` with `{idToken, displayName}`
6. Backend verifies token, creates session
7. Redirect to: `window.location.href = '/dashboard'`

---

### Sign Up Form Buttons

| Button | Location | Visual | Action | Function | Result |
|--------|----------|--------|--------|----------|--------|
| **Sign Up** | Below confirm password | Primary blue button | Submit registration | `handleSignUp(event)` → `POST /login` | Creates account, redirects to dashboard |
| **Continue with Google** | Below divider | White button with Google icon | Google OAuth | `handleGoogleAuth()` | Firebase Google sign-in |
| **Continue with Facebook** | Below Google | Blue button with Facebook icon | Facebook OAuth | `handleFacebookAuth()` | Firebase Facebook sign-in |
| **Sign In** | Bottom text link | Inline link | Switch to sign-in | `switchAuthTab('signin')` | Shows sign-in form |

**Form Fields:**
- Full Name: `<input id="signupName">`
- Email: `<input id="signupEmail">`
- Password: `<input id="signupPassword">`
- Confirm Password: `<input id="signupConfirmPassword">`

**Submit Process:**
1. User fills all 4 fields
2. Validates: password match, length ≥6
3. Click "Sign Up" → `handleSignUp()` called
4. Firebase creates account: `auth.createUserWithEmailAndPassword()`
5. Update profile: `user.updateProfile({displayName: name})`
6. Get token: `user.getIdToken()`
7. Send to backend: `POST /login` with `{idToken, displayName}`
8. Backend creates `user_profiles` and `subscriptions` entries
9. Redirect to: `window.location.href = '/dashboard'`

---

## 📊 Dashboard
**File:** `sendmail/templates/dashboard.html`  
**Route:** `GET /dashboard`  
**Requires:** User authentication (session)

### Top Navigation Bar

| Button | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **JustMailIt Logo** | Top left | Logo image | Return to dashboard | `href="/dashboard"` | Refresh dashboard |
| **Dashboard** | Nav menu | Nav link with icon | Current page | `href="/dashboard"` | Active page (no action) |
| **Profile** | Nav menu | Nav link with icon | Open profile page | `href="/profile"` | Navigate to profile |
| **Jobs** | Nav menu | Nav link with icon | Open jobs list | `href="/jobs"` | Navigate to jobs page |
| **Automation** | Nav menu | Nav link with icon | Open automation | `href="/automation"` | Navigate to automation page |
| **Sent Emails** | Nav menu | Nav link with icon | Open email history | `href="/sent_emails"` | Navigate to sent emails |
| **Settings** | Nav menu | Nav link with icon | Open settings | `href="/settings"` | Navigate to settings |
| **User Avatar** | Top right | Circle with initials | Dropdown menu | Toggles dropdown | Shows logout option |
| **Logout** | User dropdown | Text link with icon | End session | `href="/logout"` | Clears session, redirects to `/` |

---

### Quick Stats Cards

| Card | Location | Visual | Action | Function | Result |
|------|----------|--------|--------|----------|--------|
| **Jobs Found** | Top row, card 1 | Number with icon | Display only | None | Shows total scraped jobs |
| **Emails Sent** | Top row, card 2 | Number with icon | Display only | None | Shows emails sent today |
| **Applications** | Top row, card 3 | Number with icon | Click → View history | `href="/sent_emails"` | Navigate to sent emails page |
| **Success Rate** | Top row, card 4 | Percentage | Display only | None | Shows application success % |

---

### Quick Action Buttons

| Button | Location | Visual | Action | Route/Function | Result |
|--------|----------|--------|--------|----------------|--------|
| **🚀 Run Automation** | Center card | Large gradient button | Start automation | `onclick` → Modal or `href="/automation"` | Opens automation config page |
| **📋 View Jobs** | Center card | Secondary button | Browse jobs | `href="/jobs"` | Navigate to jobs list |
| **⚙️ Settings** | Center card | Secondary button | Open settings | `href="/settings"` | Navigate to settings |

**Run Automation Button Process:**
1. Click "Run Automation"
2. If no resume: Alert "Please upload resume first"
3. Else: Navigate to `/automation` page
4. User configures search (keywords, location)
5. Clicks "Start" on automation page
6. Executes `POST /run_automation`

---

### Subscription Banner (Free Users Only)

| Button | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **Upgrade to Pro** | Sidebar banner | Gradient button | Open subscription page | `href="/subscription"` | Navigate to pricing |
| **Close Banner** | Banner top-right | X icon | Hide banner | JavaScript | Removes banner from view |

**Banner Text:**
- "You're on the Free Plan"
- "10 emails per day"
- "Upgrade to Pro for unlimited emails"

---

### Recent Activity Feed

| Element | Location | Visual | Action | Route | Result |
|---------|----------|--------|--------|-------|--------|
| **Activity Item** | Activity feed | List item with timestamp | Click → View details | `href="/sent_emails?id={email_id}"` | Opens email detail view |
| **View All** | Bottom of feed | Link button | See all activity | `href="/sent_emails"` | Navigate to full history |

**Activity Shows:**
- Last 5 actions
- Format: "Sent email to [Company] - [Time ago]"
- Click any item to see email details

---

## 👤 Profile Page
**File:** `sendmail/templates/profile.html`  
**Route:** `GET /profile`  
**Requires:** Authentication

### Profile Form Buttons

| Button | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **Save Changes** | Bottom of form | Primary gradient button | Update profile | `POST /profile` | Saves all form data to `user_profiles` table |
| **Cancel** | Bottom of form | Secondary button | Discard changes | `window.location.reload()` | Reloads page (resets form) |

**Form Fields Updated:**
- Name: `<input name="name">`
- Email: `<input name="email">` (read-only)
- Skills: `<input name="skills">` (comma-separated)
- Experience Years: `<input name="experience_years" type="number">`
- Cover Letter: `<textarea name="cover_letter">`

**Save Process:**
```python
# Backend: POST /profile
1. Validate session
2. Get form data: request.form.get('name', 'skills', etc.)
3. Update database:
   UPDATE user_profiles 
   SET name=?, skills=?, experience_years=?, cover_letter=?
   WHERE user_id=?
4. Flash success message
5. Redirect back to /profile
```

---

### Resume Section Buttons

| Button | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **Upload Resume** | Resume card | Blue upload button with icon | Open file picker | `<input type="file" accept=".pdf">` → `POST /upload_resume` | Uploads PDF, saves to `/uploads/resumes/` |
| **Preview Resume** | Resume card (if exists) | Eye icon button | Open PDF viewer | `window.open('/uploads/resumes/{filename}')` | Opens PDF in new tab |
| **Delete Resume** | Resume card (if exists) | Red trash icon | Remove resume | Confirm dialog → `POST /delete_resume` | Deletes file, clears `resume_path` |
| **Download Resume** | Resume card (if exists) | Download icon | Download file | `<a download href="/uploads/resumes/{filename}">` | Downloads PDF to computer |

**Upload Resume Process:**
1. Click "Upload Resume" → File picker opens
2. Select PDF file (max 5MB)
3. JavaScript validates:
   - File type is PDF
   - Size ≤ 5MB
4. Submit form: `POST /upload_resume`
5. Backend process:
   ```python
   file = request.files['resume']
   filename = f"resume_{user_id}_{timestamp}.pdf"
   file.save(f"/uploads/resumes/{filename}")
   db.execute("UPDATE user_profiles SET resume_path=? WHERE user_id=?", 
              (filename, user_id))
   ```
6. Success message shown
7. Preview/Delete buttons now appear

**Delete Resume Process:**
1. Click trash icon → Confirmation dialog:
   "Are you sure you want to delete your resume?"
2. Click "Yes" → `POST /delete_resume`
3. Backend:
   ```python
   db.execute("UPDATE user_profiles SET resume_path=NULL WHERE user_id=?")
   os.remove(f"/uploads/resumes/{old_filename}")
   ```
4. Upload button reappears

---

### Skills Section

| Button | Location | Visual | Action | Function | Result |
|--------|----------|--------|--------|----------|--------|
| **Add Skill** | Skills input | Plus icon button | Add skill tag | JavaScript | Adds skill to comma-separated list |
| **Remove Skill (X)** | On skill badge | Small X icon | Remove skill | JavaScript | Removes from skills string |

**Skills Input:**
- Type skill name + press Enter or click "+"
- Skills stored as: `"Python,JavaScript,React,Node.js,SQL"`
- Displayed as individual badge tags
- Max 500 characters total

---

## 💼 Jobs Page
**File:** `sendmail/templates/job_posts.html`  
**Route:** `GET /jobs`  
**Requires:** Authentication

### Filter Controls

| Button | Location | Visual | Action | Function | Result |
|--------|----------|--------|--------|----------|--------|
| **Search** | Top toolbar | Search input + button | Filter jobs | `GET /jobs?search={query}` | Filters by title/company |
| **Location Filter** | Sidebar | Dropdown select | Filter by location | `GET /jobs?location={city}` | Shows only matching location |
| **Job Type Filter** | Sidebar | Checkbox group | Filter by type | `GET /jobs?type={full-time,contract}` | Filters by job type |
| **Experience Filter** | Sidebar | Range slider | Filter by experience | `GET /jobs?exp_min={n}&exp_max={m}` | Filters by years required |
| **Clear Filters** | Sidebar bottom | Secondary button | Reset all filters | `window.location.href='/jobs'` | Reloads without query params |
| **Apply Filters** | Sidebar bottom | Primary button | Execute filter | Form submit | Reloads page with filters |

---

### Job List Actions

| Button | Location | Visual | Action | Function | Result |
|--------|----------|--------|--------|----------|--------|
| **Sort: Date** | Table header | Clickable header | Sort by posted date | `GET /jobs?sort=date&order=desc` | Sorts newest first |
| **Sort: Company** | Table header | Clickable header | Sort alphabetically | `GET /jobs?sort=company&order=asc` | Sorts A-Z |
| **Sort: Title** | Table header | Clickable header | Sort by job title | `GET /jobs?sort=title&order=asc` | Sorts A-Z |

**Sorting Logic (Backend):**
```python
# app.py - job_posts() route (line 2123-2180)
sort = request.args.get('sort', 'date')
order = request.args.get('order', 'desc')

jobs = load_job_posts()  # From database

if sort == 'date':
    jobs.sort(key=lambda x: x.get('posted_date', '1970-01-01'), 
              reverse=(order == 'desc'))
elif sort == 'company':
    jobs.sort(key=lambda x: x.get('company', '').lower())
```

---

### Job Card Actions

| Button | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **View Details** | On each job card | Blue text button | Open job modal | JavaScript modal | Shows full job description |
| **Apply Now** | On each job card | Gradient button | Send application | `POST /apply_to_job?job_id={id}` | Sends single email |
| **View on LinkedIn** | Job modal | External link icon | Open LinkedIn | `window.open(job.job_url)` | Opens LinkedIn job page |

**Apply Now Process:**
1. Click "Apply Now" on job card
2. Backend checks:
   ```python
   # Check if already applied
   applied = db.execute(
       "SELECT COUNT(*) FROM sent_emails WHERE user_id=? AND job_id=?",
       (user_id, job_id)
   )
   if applied > 0:
       return "Already applied to this job"
   
   # Check daily limit (free users)
   if user_plan == 'free':
       today_count = count_emails_sent_today(user_id)
       if today_count >= 10:
           return "Daily limit reached. Upgrade to Pro."
   ```
3. If checks pass:
   - Generate personalized email
   - Attach resume
   - Send via SMTP
   - Save to `sent_emails` table
4. Success message: "Application sent to {company}!"
5. Button changes to: "✓ Applied" (disabled)

---

### Job Detail Modal

| Button | Location | Visual | Action | Function | Result |
|--------|----------|--------|--------|----------|--------|
| **Close (X)** | Modal top-right | X icon | Close modal | JavaScript | Hides modal overlay |
| **Apply Now** | Modal bottom | Primary button | Send application | `POST /apply_to_job` | Same as card button |
| **Copy Job URL** | Modal top | Copy icon | Copy LinkedIn URL | `navigator.clipboard.writeText()` | Copies URL to clipboard |
| **Share** | Modal top | Share icon | Open share menu | Native share API | Opens system share dialog |

**Modal Content Shows:**
- Full job description (HTML formatted)
- Skills required (badge tags)
- Experience requirement
- Salary range (if available)
- Posted date
- Company info
- Recruiter email

---

### Pagination Controls

| Button | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **Previous** | Bottom of list | Arrow left button | Previous page | `GET /jobs?page={n-1}` | Shows previous 50 jobs |
| **Next** | Bottom of list | Arrow right button | Next page | `GET /jobs?page={n+1}` | Shows next 50 jobs |
| **Page Number** | Center | Number buttons | Jump to page | `GET /jobs?page={n}` | Loads specific page |

**Pagination Logic:**
- Default: 50 jobs per page
- Total pages: `ceil(767 / 50) = 16 pages`
- Current page highlighted in blue

---

## 🤖 Automation Page
**File:** `sendmail/templates/automation.html`  
**Route:** `GET /automation`  
**Requires:** Authentication + Resume uploaded

### Configuration Form Buttons

| Button | Location | Visual | Action | Function | Result |
|--------|----------|--------|--------|----------|--------|
| **Start Automation** | Bottom of config | Large gradient button | Execute automation | `POST /run_automation` | Starts full automation flow |
| **Save Settings** | Below start button | Secondary button | Save preferences | `POST /automation/settings` | Saves config to user profile |
| **Reset to Default** | Config header | Link button | Clear all fields | JavaScript | Resets form to defaults |

**Configuration Fields:**
- **Job Title Keywords:** `<input name="keywords" placeholder="Python Developer, Data Scientist">`
- **Location:** `<input name="location" placeholder="Mumbai, Bangalore">`
- **Job Type:** `<select name="job_type">` (Full-time, Part-time, Contract, Internship)
- **Minimum Salary:** `<input name="min_salary" type="number">`
- **Maximum Applications:** `<input name="max_applications">` (Free: max 10, Pro: unlimited)

---

### Automation Execution Flow

**Start Button Click Process:**

```javascript
// Frontend: automation.html
document.getElementById('startAutomation').onclick = async function() {
    // 1. Validate form
    if (!keywords || !location) {
        alert('Please fill required fields');
        return;
    }
    
    // 2. Disable button
    this.disabled = true;
    this.innerHTML = '<i class="spinner"></i> Running...';
    
    // 3. Show progress bar
    document.getElementById('progressContainer').style.display = 'block';
    
    // 4. Start automation
    const response = await fetch('/run_automation', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            keywords: keywords,
            location: location,
            job_type: job_type,
            min_salary: min_salary,
            max_applications: max_applications
        })
    });
    
    // 5. Handle response
    const result = await response.json();
    if (result.success) {
        showSuccessModal(result);
    } else {
        showError(result.error);
    }
};
```

**Backend Execution (app.py):**

```python
@app.route('/run_automation', methods=['POST'])
def run_automation():
    # 1. Validate (lines 3520-3545)
    user_id = session.get('user_id')
    user = get_user_profile(user_id)
    if not user['resume_path']:
        return {'success': False, 'error': 'No resume uploaded'}
    
    # 2. Get config
    config = request.get_json()
    keywords = config['keywords']
    location = config['location']
    
    try:
        # 3. SCRAPING PHASE
        emit_progress('Scraping LinkedIn jobs...', 10)
        jobs = scrape_linkedin_jobs(keywords, location)
        all_emails = set(jobs)
        emit_progress(f'Found {len(jobs)} jobs', 30)
        
        # 4. ANALYSIS PHASE
        emit_progress('Analyzing job matches...', 50)
        scored_jobs = analyze_and_score(jobs, user['skills'])
        emit_progress('Jobs ranked by relevance', 60)
        
        # 5. LIMIT CHECK (Free users only)
        if user_plan == 'free':
            today_count = count_emails_sent_today(user_id)
            remaining = 10 - today_count
            if remaining <= 0:
                skipped_emails = all_emails
                sendable = []
            else:
                sendable = scored_jobs[:remaining]
                skipped_emails = scored_jobs[remaining:]
        else:  # Pro user
            sendable = scored_jobs
            skipped_emails = []
        
        # 6. EMAIL SENDING PHASE
        emails_sent_count = 0
        for job in sendable:
            emit_progress(f'Sending to {job["company"]}...', 70 + (emails_sent_count * 2))
            success = send_job_application_email(
                to=job['recruiter_email'],
                job=job,
                user=user,
                resume_path=user['resume_path']
            )
            if success:
                emails_sent_count += 1
                save_sent_email(user_id, job)
        
        emit_progress('Automation complete!', 100)
        
        # 7. NOTIFICATION PHASE (finally block - lines 3785-3920)
        # Sends appropriate notification emails
        
        return {
            'success': True,
            'jobs_found': len(all_emails),
            'emails_sent': emails_sent_count,
            'skipped': len(skipped_emails)
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

---

### Progress Monitoring

| Element | Location | Visual | Action | Function | Result |
|---------|----------|--------|--------|----------|--------|
| **Progress Bar** | Center of page | Animated bar | Display only | Updates via WebSocket | Shows % complete |
| **Status Text** | Below progress bar | Text updates | Display only | Updates via WebSocket | Shows current step |
| **Stop Button** | Right of progress | Red button | Cancel automation | `POST /api/stop_automation` | Interrupts execution |

**Progress Updates:**
- 10%: "Scraping LinkedIn jobs..."
- 30%: "Found 87 jobs"
- 50%: "Analyzing job matches..."
- 60%: "Jobs ranked by relevance"
- 70-90%: "Sending to {Company}..." (incremental)
- 100%: "Automation complete!"

**Stop Button:**
```javascript
document.getElementById('stopAutomation').onclick = async function() {
    const confirmed = confirm('Stop automation? Emails already sent will not be recalled.');
    if (confirmed) {
        await fetch('/api/stop_automation', {method: 'POST'});
        window.location.reload();
    }
};
```

---

### Results Summary (After Completion)

| Button | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **View Applications** | Results modal | Primary button | Open sent emails | `href="/sent_emails"` | Navigate to email history |
| **Run Again** | Results modal | Secondary button | Restart automation | `window.location.reload()` | Resets automation page |
| **Upgrade to Pro** | Results modal (if limited) | Gradient button | Open pricing | `href="/subscription"` | Navigate to subscription |

**Results Modal Shows:**
```
✅ Automation Complete!

📊 Summary:
- Jobs Found: 87
- Emails Sent: 10
- Skipped: 77 (Free plan limit)

💡 Upgrade to Pro to apply to all 87 jobs!

[View Applications] [Run Again] [Upgrade to Pro]
```

---

## 📧 Sent Emails Page
**File:** `sendmail/templates/sent_emails.html`  
**Route:** `GET /sent_emails`  
**Requires:** Authentication

### Filter Controls

| Button | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **Date Range** | Top toolbar | Date picker | Filter by date | `GET /sent_emails?from={date}&to={date}` | Shows emails in range |
| **Search Company** | Top toolbar | Search input | Filter by company | `GET /sent_emails?company={name}` | Shows matching companies |
| **Export CSV** | Top right | Download button | Export data | `GET /api/export_emails?format=csv` | Downloads CSV file |
| **Refresh** | Top right | Refresh icon | Reload data | `window.location.reload()` | Reloads page |

---

### Email List Actions

| Button | Location | Visual | Action | Function | Result |
|--------|----------|--------|--------|----------|--------|
| **View Email** | On each row | Eye icon | Open email details | JavaScript modal | Shows full email content |
| **View Job** | On each row | Link icon | Open job details | Opens job modal | Shows original job post |
| **Copy Email** | On each row | Copy icon | Copy email content | `navigator.clipboard.writeText()` | Copies to clipboard |
| **Delete** | On each row | Trash icon | Delete record | Confirm → `POST /delete_email` | Removes from history |

**Email List Columns:**
- Date Sent
- Company Name
- Job Title
- Recipient Email
- Status (Sent/Failed)
- Actions (buttons)

---

### Email Detail Modal

| Button | Location | Visual | Action | Function | Result |
|--------|----------|--------|--------|----------|--------|
| **Close (X)** | Modal top-right | X icon | Close modal | JavaScript | Hides modal |
| **Forward** | Modal bottom | Forward button | Forward email | Opens email client | `mailto:?body={content}` |
| **Download PDF** | Modal bottom | PDF icon | Save as PDF | Generates PDF | Downloads email as PDF |

**Modal Shows:**
```
To: hr@company.com
Subject: Application for Senior Developer - John Doe
Sent: Dec 6, 2025 at 2:30 PM
Status: ✓ Sent

---

[Full email body with formatting]

[Resume attachment: resume_john_doe.pdf]

[Forward] [Download PDF] [Close]
```

---

## 💳 Subscription Page
**File:** `sendmail/templates/subscription.html`  
**Route:** `GET /subscription`  
**Requires:** Authentication

### Plan Cards

#### Free Plan Card

| Button | Location | Visual | Action | Function | Result |
|--------|----------|--------|--------|----------|--------|
| **Current Plan** | Free card | Badge indicator | Display only | None | Shows active status |

**Free Plan Features:**
- ✓ 10 emails per day
- ✓ Job scraping
- ✓ Resume upload
- ✓ Email history
- ✗ Unlimited emails
- ✗ Priority support

---

#### Pro Plan Card

| Button | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **Upgrade to Pro** | Pro card | Large gradient button | Start checkout | `POST /create_order` → Razorpay | Opens payment modal |
| **See Features** | Pro card | Link | Expand features | JavaScript | Shows full feature list |

**Pro Plan Features:**
- ✓ Unlimited emails per day
- ✓ Job scraping
- ✓ Resume upload
- ✓ Email history
- ✓ Priority support
- ✓ Advanced analytics
- ✓ Custom templates
- ✓ API access

**Pricing:**
- Monthly: ₹199/month
- Yearly: ₹1,999/year (Save 17%)

---

### Upgrade Process

**Upgrade Button Click:**

```javascript
document.getElementById('upgradeToPro').onclick = async function() {
    // 1. Create Razorpay order
    const response = await fetch('/create_order', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            plan: 'pro',
            billing: 'monthly'  // or 'yearly'
        })
    });
    
    const order = await response.json();
    
    // 2. Open Razorpay checkout
    const options = {
        key: 'rzp_live_xxxxxxxxx',
        amount: order.amount,
        currency: 'INR',
        name: 'JustMailIt Pro',
        description: 'Monthly Subscription',
        order_id: order.id,
        handler: function(response) {
            // 3. Verify payment
            verifyPayment(response);
        }
    };
    
    const rzp = new Razorpay(options);
    rzp.open();
};

async function verifyPayment(response) {
    // 4. Backend verifies signature
    const result = await fetch('/verify_payment', {
        method: 'POST',
        body: JSON.stringify(response)
    });
    
    if (result.success) {
        // 5. Update subscription in database
        // UPDATE subscriptions SET plan='pro', end_date=DATE('+1 year')
        
        // 6. Show success
        alert('✅ Upgraded to Pro! Enjoy unlimited emails.');
        window.location.reload();
    }
}
```

---

### Current Subscription Management (Pro Users)

| Button | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **Manage Subscription** | Pro card | Secondary button | Open management | `href="/manage_subscription"` | Shows billing details |
| **Cancel Subscription** | Management page | Danger button | Cancel Pro plan | Confirm → `POST /cancel_subscription` | Downgrades to Free |
| **Update Payment** | Management page | Link button | Change card | Opens Razorpay | Updates payment method |
| **View Invoices** | Management page | Link button | Download invoices | `GET /invoices` | Shows invoice list |

**Cancel Process:**
1. Click "Cancel Subscription"
2. Confirmation dialog:
   ```
   Are you sure you want to cancel Pro?
   
   You'll lose:
   - Unlimited emails (back to 10/day)
   - Priority support
   - Advanced features
   
   Active until: Dec 31, 2025
   ```
3. Click "Yes, Cancel" → `POST /cancel_subscription`
4. Backend:
   ```python
   db.execute("""
       UPDATE subscriptions 
       SET is_active=0 
       WHERE user_id=? AND plan='pro'
   """)
   ```
5. Remains active until end date
6. Then auto-downgrades to Free

---

## ⚙️ Settings Page
**File:** `sendmail/templates/settings.html`  
**Route:** `GET /settings`  
**Requires:** Authentication

### Account Settings

| Button | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **Change Password** | Account section | Primary button | Update password | `POST /change_password` | Updates Firebase password |
| **Change Email** | Account section | Link button | Update email | Opens modal | Requires re-authentication |
| **Delete Account** | Account section | Danger button | Delete account | Confirm → `POST /delete_account` | Removes all user data |

**Change Password Form:**
- Current Password: `<input type="password" name="current">`
- New Password: `<input type="password" name="new">`
- Confirm Password: `<input type="password" name="confirm">`

**Process:**
1. Enter current + new passwords
2. Click "Change Password" → `POST /change_password`
3. Backend verifies current password with Firebase
4. Updates: `auth.update_password(new_password)`
5. Success: "Password updated successfully"

---

### Notification Settings

| Toggle | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **Email Notifications** | Notifications section | Toggle switch | Enable/disable emails | `POST /settings/notifications` | Updates preference |
| **Success Emails** | Notifications section | Toggle switch | Enable success emails | `POST /settings/notifications` | Toggles success notifications |
| **Missed Opportunity Emails** | Notifications section | Toggle switch | Enable missed emails | `POST /settings/notifications` | Toggles missed notifications |
| **No Results Emails** | Notifications section | Toggle switch | Enable no-results emails | `POST /settings/notifications` | Toggles no-results notifications |
| **Weekly Summary** | Notifications section | Toggle switch | Enable weekly digest | `POST /settings/notifications` | Toggles weekly summary |

**Stored in database:**
```python
# Add to user_profiles table
ALTER TABLE user_profiles ADD COLUMN notification_settings TEXT;

# JSON format:
{
    "email_enabled": true,
    "success_emails": true,
    "missed_opportunity_emails": true,
    "no_results_emails": true,
    "weekly_summary": false
}
```

---

### Privacy Settings

| Button | Location | Visual | Action | Route | Result |
|--------|----------|--------|--------|-------|--------|
| **Download My Data** | Privacy section | Download button | Export user data | `GET /api/export_data` | Downloads JSON with all user data |
| **Delete All History** | Privacy section | Danger button | Clear email history | Confirm → `POST /delete_history` | Removes all sent_emails records |

**Download My Data:**
- Exports JSON file containing:
  - User profile
  - All sent emails
  - Job application history
  - Subscription info
- GDPR compliance
- Filename: `justmailit_data_{user_id}_{date}.json`

---

### Automation Defaults

| Input | Location | Visual | Action | Route | Result |
|-------|----------|--------|--------|-------|--------|
| **Default Keywords** | Automation section | Text input | Save default | `POST /settings` | Pre-fills automation form |
| **Default Location** | Automation section | Text input | Save default | `POST /settings` | Pre-fills automation form |
| **Default Job Type** | Automation section | Dropdown | Save default | `POST /settings` | Pre-fills automation form |
| **Save Defaults** | Automation section | Primary button | Save all settings | `POST /settings` | Updates user_profiles |

---

## 🗂️ Navigation Menu
**Present on:** All authenticated pages  
**Location:** Left sidebar or top navigation

### Main Navigation Links

| Link | Icon | Action | Route | Page Loaded |
|------|------|--------|-------|-------------|
| **Dashboard** | 📊 bi-speedometer2 | Navigate to dashboard | `GET /dashboard` | Dashboard overview |
| **Profile** | 👤 bi-person | Open profile page | `GET /profile` | Profile editing |
| **Jobs** | 💼 bi-briefcase | Open jobs list | `GET /jobs` | Job listings |
| **Automation** | 🤖 bi-robot | Open automation | `GET /automation` | Automation config |
| **Sent Emails** | 📧 bi-envelope-check | Open email history | `GET /sent_emails` | Sent emails list |
| **Subscription** | 💳 bi-star | Open subscription | `GET /subscription` | Subscription plans |
| **Settings** | ⚙️ bi-gear | Open settings | `GET /settings` | Settings page |

---

### User Menu (Top Right)

| Item | Icon | Action | Route | Result |
|------|------|--------|-------|--------|
| **User Avatar** | Circle with initials | Toggle dropdown | JavaScript | Shows dropdown menu |
| **Profile** | 👤 | Navigate to profile | `GET /profile` | Opens profile page |
| **Settings** | ⚙️ | Navigate to settings | `GET /settings` | Opens settings page |
| **Help & Support** | ❓ | Open help modal | JavaScript | Shows help resources |
| **Logout** | 🚪 bi-box-arrow-right | End session | `GET /logout` | Clears session, redirects to landing |

**Logout Process:**
```python
@app.route('/logout')
def logout():
    # 1. Clear session
    session.clear()
    
    # 2. Clear cookies
    response = make_response(redirect('/'))
    response.set_cookie('session', '', expires=0)
    
    # 3. Redirect to landing
    return response
```

---

## 🔔 Notification Toasts
**Present on:** All pages  
**Location:** Top-right corner (floating)

### Toast Types

| Type | Icon | Color | Trigger | Example |
|------|------|-------|---------|---------|
| **Success** | ✓ | Green | Action succeeded | "Profile updated successfully!" |
| **Error** | ✗ | Red | Action failed | "Failed to send email. Please try again." |
| **Warning** | ⚠️ | Yellow | Validation issue | "Resume must be less than 5MB" |
| **Info** | ℹ️ | Blue | Information | "Automation will take 5-10 minutes" |

**Toast Auto-Dismiss:**
- Success: 3 seconds
- Error: 5 seconds
- Warning: 4 seconds
- Info: 3 seconds

**Close Button:**
- All toasts have X button
- Click to dismiss immediately

---

## 🎯 Modal Dialogs

### Confirmation Dialogs

**Used for destructive actions:**
- Delete resume
- Cancel subscription
- Delete account
- Clear history

**Buttons:**
- **Cancel** (Secondary, gray): Closes dialog, no action
- **Confirm** (Primary, red for danger): Executes action

---

### Success Modals

**Shown after:**
- Automation complete
- Payment successful
- Profile updated

**Buttons:**
- **Close** (X icon): Dismisses modal
- **View Results** (Primary): Navigate to relevant page

---

## 📱 Mobile Responsive Buttons

**On mobile screens (<768px):**

| Desktop Button | Mobile Version | Action |
|----------------|----------------|--------|
| Text buttons | Icon-only buttons | Same action, compact layout |
| Multi-line forms | Stacked inputs | Full-width inputs |
| Sidebar navigation | Hamburger menu | Collapsible menu |
| Table actions | Swipe actions | Swipe left to reveal |

**Hamburger Menu Button:**
- Location: Top-left corner (mobile only)
- Icon: ☰ (three lines)
- Action: Toggles slide-out navigation
- Navigation slides from left

---

## 🎨 Button Style Guide

### Button Types

#### Primary Button
```css
background: linear-gradient(135deg, #a8e6cf, #8b9fff);
color: white;
padding: 0.875rem 2rem;
border-radius: 50px;
font-weight: 700;
```
**Used for:** Main actions (Start Automation, Save, Submit)

#### Secondary Button
```css
background: white;
color: #8b9fff;
border: 2px solid #a8e6cf;
padding: 0.875rem 2rem;
border-radius: 50px;
font-weight: 600;
```
**Used for:** Alternative actions (Cancel, Back, View)

#### Danger Button
```css
background: linear-gradient(135deg, #ff6b6b, #ee5a6f);
color: white;
padding: 0.875rem 2rem;
border-radius: 50px;
font-weight: 700;
```
**Used for:** Destructive actions (Delete, Cancel Subscription)

#### Icon Button
```css
background: transparent;
color: #718096;
padding: 0.5rem;
border-radius: 50%;
```
**Used for:** Small actions (Edit, Delete, Copy)

---

## 🔢 Button States

### Disabled State
```css
opacity: 0.6;
cursor: not-allowed;
pointer-events: none;
```
**Shown when:** Action not available or form invalid

### Loading State
```html
<button disabled>
  <i class="spinner-border spinner-border-sm"></i>
  Processing...
</button>
```
**Shown when:** Waiting for server response

### Active State
```css
background: darker shade;
transform: scale(0.98);
```
**Shown when:** Button is pressed

---

## 📊 Summary Statistics

### Total Interactive Elements

| Category | Count | Examples |
|----------|-------|----------|
| **Navigation Links** | 15+ | Dashboard, Profile, Jobs, etc. |
| **Form Buttons** | 30+ | Save, Cancel, Upload, etc. |
| **Action Buttons** | 50+ | Apply, View, Delete, etc. |
| **Toggle Switches** | 10+ | Notification settings |
| **Modal Buttons** | 20+ | Close, Confirm, Cancel |
| **Icon Buttons** | 40+ | Edit, Delete, Copy, Share |

**Total:** 165+ interactive elements across the entire application

---

## 🔍 Quick Reference Table

### Most Common Buttons by Page

| Page | Primary Action | Secondary Action | Danger Action |
|------|----------------|------------------|---------------|
| **Landing** | Get Started | Watch Demo | - |
| **Dashboard** | Run Automation | View Jobs | - |
| **Profile** | Save Changes | Cancel | Delete Resume |
| **Jobs** | Apply Now | View Details | - |
| **Automation** | Start Automation | Save Settings | Stop |
| **Sent Emails** | View Email | Export CSV | Delete |
| **Subscription** | Upgrade to Pro | - | Cancel Plan |
| **Settings** | Save Settings | - | Delete Account |

---

## 🎓 Button Usage Guidelines

### When to Use Each Button Type

**Primary Button:**
- ✅ Main call-to-action
- ✅ Form submissions
- ✅ Starting processes
- ❌ Destructive actions

**Secondary Button:**
- ✅ Alternative actions
- ✅ Navigation
- ✅ Cancellation
- ❌ Main actions

**Danger Button:**
- ✅ Destructive actions only
- ✅ Requires confirmation
- ❌ Regular actions

**Icon Button:**
- ✅ Quick actions
- ✅ Space-constrained areas
- ✅ Repeated actions
- ❌ Primary actions

---

**End of UI Button Reference**

*This document covers every interactive element in the JustMailIt application. For implementation details, see SYSTEM_DOCUMENTATION.md.*
