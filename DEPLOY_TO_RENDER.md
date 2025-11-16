# 🚀 Deploy JustMailIt to Render - Complete Guide

## ✅ What's Ready:

- ✅ Razorpay Payment Gateway (₹1 Pro Plan)
- ✅ Docker configuration with Chrome/ChromeDriver
- ✅ Firebase authentication & Firestore
- ✅ Email automation with Gmail SMTP
- ✅ Job post tracking & analysis
- ✅ Subscription management system

---

## 📋 Prerequisites

1. **GitHub Repository**: `manuchaturvedi/email-sent-site` (branch: `cloud-deployment`)
2. **Render Account**: https://dashboard.render.com (sign up free)
3. **Razorpay Account**: Already registered with live keys
4. **Firebase Project**: linkedin-7c251 (already configured)

---

## 🎯 Step-by-Step Deployment

### Step 1: Push Latest Changes to GitHub

```powershell
cd "c:\Users\windows 10\Desktop\AI_support"
git add .
git commit -m "Add Razorpay payment integration with ₹1 subscription"
git push origin cloud-deployment
```

### Step 2: Create Web Service on Render

1. **Go to**: https://dashboard.render.com
2. **Click**: "New +" → "Web Service"
3. **Connect Repository**: 
   - Select "Connect account" if needed
   - Choose: `manuchaturvedi/email-sent-site`
   - Branch: `cloud-deployment`

### Step 3: Configure Service

**Basic Settings:**
- **Name**: `justmailit-app` (or your preferred name)
- **Region**: Choose closest to your location (e.g., Singapore, Oregon)
- **Branch**: `cloud-deployment`
- **Runtime**: **Docker** ⚠️ CRITICAL!
- **Dockerfile Path**: `Dockerfile.render`
- **Docker Command**: Leave empty (uses CMD from Dockerfile)

**Instance Type:**
- **Free Tier** for testing ($0/month)
- **Starter** ($7/month) for production - recommended for better performance

### Step 4: Set Environment Variables

Click on "Environment" tab and add these variables:

#### Required Variables:

```env
# Razorpay Payment Gateway
RAZORPAY_KEY_ID=rzp_live_RgNB6M60lUvK2l
RAZORPAY_KEY_SECRET=i4GM8FcOw34g438OMecg2z78
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_from_razorpay

# Firebase Configuration
GOOGLE_APPLICATION_CREDENTIALS_JSON=<paste_base64_encoded_json>

# Chrome Configuration (Auto-set by Dockerfile)
CHROME_BIN=/usr/bin/google-chrome
CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
PYTHONPATH=/app
DISPLAY=:99

# Flask Configuration
PORT=5000
SECRET_KEY=<generate_random_secret_key>
```

#### Get Firebase Credentials (Base64):

**Option 1 - PowerShell:**
```powershell
$json = Get-Content "c:\Users\windows 10\Desktop\AI_support\sendmail\linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json" -Raw
$bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
[System.Convert]::ToBase64String($bytes) | Set-Clipboard
Write-Host "✅ Firebase credentials copied to clipboard!"
```

**Option 2 - Online Tool:**
1. Go to: https://www.base64encode.org/
2. Upload your Firebase JSON file
3. Copy the base64 output
4. Paste into `GOOGLE_APPLICATION_CREDENTIALS_JSON`

#### Generate Secret Key:

**PowerShell:**
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

### Step 5: Configure Razorpay Webhook

1. **Go to**: https://dashboard.razorpay.com/app/webhooks
2. **Click**: "Create New Webhook"
3. **Webhook URL**: `https://your-app-name.onrender.com/payment/webhook`
   - Replace `your-app-name` with your actual Render service name
4. **Active Events**: Select `payment.captured`
5. **Secret**: Copy the generated webhook secret
6. **Save** and add the secret to Render environment variables as `RAZORPAY_WEBHOOK_SECRET`

### Step 6: Deploy!

1. **Click**: "Create Web Service"
2. **Wait**: 5-10 minutes for build and deployment
3. **Monitor**: Check build logs for any errors

**Expected Build Logs:**
```
🚀 Starting Render build with Chrome installation...
📦 Installing Python packages...
✅ Razorpay Payment Gateway initialized
✅ Firebase initialized from environment variable
✅ Firestore client initialized
* Running on all addresses (0.0.0.0)
* Running on http://0.0.0.0:5000
```

### Step 7: Test Your Deployment

1. **Visit**: `https://your-app-name.onrender.com`
2. **Test Login**: Click "Sign in with Google"
3. **Test Pricing**: Go to `/pricing` page
4. **Test Payment**: Click "Upgrade to Pro" (₹1)
5. **Complete Payment**: Use test card if in test mode
6. **Verify Upgrade**: Check if plan upgraded successfully

---

## 🧪 Testing Razorpay Payment

### Test Mode (For Development):

**Update Environment Variables:**
```env
RAZORPAY_KEY_ID=rzp_test_XXXXXXXXXXXXX
RAZORPAY_KEY_SECRET=your_test_secret
```

**Test Cards:**
- **Success**: `4111 1111 1111 1111`
- **CVV**: Any 3 digits
- **Expiry**: Any future date
- **OTP**: 1234

### Live Mode (For Production):

**Use Your Live Keys:**
```env
RAZORPAY_KEY_ID=rzp_live_RgNB6M60lUvK2l
RAZORPAY_KEY_SECRET=i4GM8FcOw34g438OMecg2z78
```

**Real payments** will be charged to user's card/UPI.

---

## 🔧 Common Issues & Solutions

### Issue 1: Build Fails

**Error**: `Cannot find Dockerfile.render`
**Solution**: Ensure `Dockerfile.render` is in root directory and pushed to GitHub

**Error**: `pip install failed`
**Solution**: Check `requirements.txt` is valid and all packages available

### Issue 2: Firebase Error

**Error**: `Firebase credentials not found`
**Solution**: 
- Verify `GOOGLE_APPLICATION_CREDENTIALS_JSON` is set
- Ensure base64 encoding is correct
- Check no extra spaces/newlines

### Issue 3: Payment Not Working

**Error**: Payment completes but user not upgraded
**Solution**:
- Check Razorpay webhook is configured correctly
- Verify webhook URL is publicly accessible
- Check `RAZORPAY_WEBHOOK_SECRET` matches dashboard
- Monitor Render logs for webhook events

### Issue 4: Chrome Crashes

**Error**: Chrome fails to start
**Solution**: 
- This is usually fine on Render's infrastructure
- If persists, upgrade to Starter plan for more resources
- Check logs for specific Chrome errors

---

## 📊 Post-Deployment Checklist

- [ ] App loads successfully at Render URL
- [ ] Google login works
- [ ] Dashboard displays correctly
- [ ] Pricing page loads
- [ ] Payment flow completes
- [ ] User gets upgraded to Pro plan
- [ ] Success message shows
- [ ] Redirect works after payment
- [ ] Email sending works (test with your email)
- [ ] Job posts tracking works

---

## 🔒 Security Best Practices

### 1. Environment Variables
- ✅ Never commit secrets to GitHub
- ✅ Use Render's environment variables
- ✅ Keep webhook secret private
- ✅ Rotate keys periodically

### 2. Razorpay Security
- ✅ Webhook signature verification enabled
- ✅ HTTPS only (Render provides free SSL)
- ✅ Payment signature verification on frontend
- ✅ Test mode for development, live for production

### 3. Firebase Security
- ✅ Firestore rules configured
- ✅ Only authenticated users can write
- ✅ Service account JSON secured
- ✅ Admin SDK on backend only

---

## 📈 Monitoring & Logs

### View Logs:
1. Go to Render Dashboard
2. Select your service
3. Click "Logs" tab
4. Monitor real-time logs

### Key Log Messages:
```
✅ Razorpay Payment Gateway initialized
✅ Firebase initialized
✅ Payment success: user@email.com upgraded to pro
✅ Payment webhook: user@email.com upgraded to pro
```

### Payment Monitoring:
- **Razorpay Dashboard**: https://dashboard.razorpay.com/app/payments
- View all transactions, refunds, disputes
- Download reports for accounting

---

## 🚀 Performance Optimization

### For Better Performance:

1. **Upgrade to Starter Plan** ($7/month)
   - More CPU and RAM
   - Faster cold starts
   - Better for Chrome automation

2. **Enable Auto-Deploy**
   - Automatically deploys when you push to GitHub
   - Already configured in `render.yaml`

3. **Add Redis** (Optional)
   - Cache job posts
   - Store session data
   - Faster responses

---

## 🎉 You're Live!

Your app is now deployed with:
- ✅ Razorpay payment integration (₹1/month Pro plan)
- ✅ Automatic payment detection and subscription upgrade
- ✅ Chrome-based LinkedIn automation
- ✅ Firebase authentication and Firestore database
- ✅ Email automation with Gmail SMTP
- ✅ Professional UI with pricing plans

**Your Live URL**: `https://your-app-name.onrender.com`

---

## 📞 Support

**Render Support**:
- Docs: https://render.com/docs
- Community: https://community.render.com

**Razorpay Support**:
- Dashboard: https://dashboard.razorpay.com
- Docs: https://razorpay.com/docs
- Support: https://razorpay.com/support

**Your Application**:
- Repository: https://github.com/manuchaturvedi/email-sent-site
- Branch: cloud-deployment

---

## 🔄 Updating Your Deployment

To deploy updates:

```powershell
# Make changes to your code
git add .
git commit -m "Your update message"
git push origin cloud-deployment

# Render will auto-deploy (if enabled)
# Or manually deploy from Render dashboard
```

---

**Ready to go live? Follow the steps above and your app will be running on Render in 10 minutes!** 🚀
