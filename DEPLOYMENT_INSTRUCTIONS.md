# 🚀 Cloud Deployment Guide for AI Support Email Automation

## Step 1: GitHub Repository Setup

### Create GitHub Repository
1. Go to [GitHub](https://github.com) and log in
2. Click the "+" icon → "New repository"
3. Repository name: `ai-email-automation` or `justmailit-app`
4. Description: `AI-powered email automation for job applications with LinkedIn integration`
5. Make it **Public** (required for free Render deployment)
6. **DON'T** initialize with README (we have one)
7. Click "Create repository"

### Push Local Code to GitHub
After creating the repository, run these commands in your terminal:

```bash
# Set the remote origin to your new GitHub repository
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push the cleaned code
git push -u origin cloud-deployment
```

## Step 2: Render.com Deployment

### Create Render Account
1. Go to [Render.com](https://render.com)
2. Sign up with your GitHub account
3. Authorize Render to access your repositories

### Deploy Web Service
1. On Render Dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure the service:
   - **Name**: `justmailit-app`
   - **Branch**: `cloud-deployment`
   - **Root Directory**: leave blank
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python sendmail/app.py`

### Environment Variables
Add these in Render's Environment Variables section:

1. **Required Variables:**
   ```
   FLASK_ENV=production
   CHROME_BIN=/usr/bin/google-chrome-stable  
   CHROMEDRIVER_PATH=/usr/bin/chromedriver
   PYTHONPATH=/opt/render/project/src
   CHROME_NO_SANDBOX=true
   ```

2. **Firebase Credentials (Critical):**
   - Copy content of `sendmail/linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json`
   - Encode it as base64: Use online tool or command `base64 -w 0 file.json`
   - Add as: `GOOGLE_APPLICATION_CREDENTIALS_JSON=<your-base64-string>`

### Deploy
1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Build and deploy your app
3. Monitor the build logs for any issues

## Step 3: Domain Configuration

### Get Your Render URL
- After successful deployment: `https://justmailit-app.onrender.com`
- Test the app to ensure it works

### Point Custom Domain (justmailit.in)
1. In Render Dashboard → Your Service → Settings
2. Add Custom Domain: `justmailit.in`
3. Add DNS records at your domain provider:
   ```
   Type: CNAME
   Name: @
   Value: justmailit-app.onrender.com
   
   Type: CNAME  
   Name: www
   Value: justmailit-app.onrender.com
   ```

## Step 4: Environment Setup

### Chrome and ChromeDriver
Render automatically provides Chrome in production. Your app configuration already handles this with:
```python
# Chrome setup for cloud deployment
options.add_argument("--headless=new")
options.add_argument("--no-sandbox") 
options.add_argument("--disable-dev-shm-usage")
```

### Firebase Configuration
- Your app will read Firebase credentials from the `GOOGLE_APPLICATION_CREDENTIALS_JSON` environment variable
- The base64-encoded JSON is automatically decoded in production

## Step 5: Testing & Monitoring

### Test Deployment
1. Visit your Render URL
2. Test login functionality
3. Test email automation
4. Check logs for any issues

### Monitor Logs
- Render Dashboard → Your Service → Logs
- Watch for startup issues or runtime errors
- Chrome/LinkedIn automation logs will appear here

## Troubleshooting

### Common Issues:

**Build Failures:**
- Check `requirements.txt` for correct package versions
- Ensure `Procfile` specifies correct start command

**Chrome Issues:**
- Verify environment variables are set
- Check that `--no-sandbox` flag is enabled

**Firebase Connection:**
- Verify base64 encoding of credentials is correct
- Check environment variable name matches code

**Domain Not Working:**
- DNS propagation takes 24-48 hours
- Verify CNAME records point to correct Render URL

### Support
- Render Docs: https://render.com/docs
- GitHub Issues: Create issues in your repository
- Monitor deployment status in Render dashboard

## Success! 🎉
Your AI email automation app is now running in the cloud at:
- Render URL: `https://justmailit-app.onrender.com`
- Custom domain: `https://justmailit.in` (after DNS setup)

The app now has:
- ✅ Professional cloud hosting
- ✅ Automatic scaling
- ✅ HTTPS security
- ✅ Persistent storage with Firebase
- ✅ LinkedIn automation with headless Chrome
- ✅ Email automation capabilities
- ✅ User authentication and profiles