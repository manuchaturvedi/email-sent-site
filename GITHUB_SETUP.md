# 🚀 GitHub Repository Setup Commands

## Step 1: Create Repository on GitHub
1. Go to: https://github.com/new
2. Repository name: `justmailit-app`
3. Description: `AI-powered email automation for job applications with LinkedIn integration`
4. Make it **Public** (required for free Render)
5. **Don't** initialize with README
6. Click "Create repository"

## Step 2: Push Your Code
After creating the repository, copy the repository URL and run:

```bash
# Replace YOUR_USERNAME with your actual GitHub username
git remote add origin https://github.com/YOUR_USERNAME/justmailit-app.git
git push -u origin cloud-deployment
```

## Step 3: Render.com Deployment
1. Go to: https://render.com
2. Sign up with GitHub
3. Click "New +" → "Web Service"
4. Connect your `justmailit-app` repository
5. Use branch: `cloud-deployment`
6. Configure:
   - **Name**: justmailit-app
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python sendmail/app.py`

## Step 4: Environment Variables
Add these in Render's Environment Variables:
- `FLASK_ENV=production`
- `CHROME_BIN=/usr/bin/google-chrome-stable`
- `CHROMEDRIVER_PATH=/usr/bin/chromedriver`
- `CHROME_NO_SANDBOX=true`

## Step 5: Firebase Credentials
Copy content from: `sendmail/linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json`
Encode to base64 and add as: `GOOGLE_APPLICATION_CREDENTIALS_JSON`

Your app will be live at: https://justmailit-app.onrender.com