# 🚀 Quick Deploy Checklist

## 📋 Information You'll Need:

### 1. Razorpay Keys (Already Have):
```
Key ID: rzp_live_RgNB6M60lUvK2l
Key Secret: i4GM8FcOw34g438OMecg2z78
Webhook Secret: (Get from Razorpay after setting webhook)
```

### 2. Firebase Credentials (Base64):
**✅ Already copied to your clipboard!**
```
Variable name: GOOGLE_APPLICATION_CREDENTIALS_JSON
Value: [Already in your clipboard - just paste in Render]
```

### 3. Flask Secret Key:
**✅ Already generated!**
```
Variable name: SECRET_KEY
Value: tHeuznMsSOk20GDNATd6JlYFZx9QyUah
```

---

## 🎯 Deployment Steps:

### [ ] Step 1: Push to GitHub
```powershell
cd "c:\Users\windows 10\Desktop\AI_support"
git add .
git commit -m "Add Razorpay payment integration"
git push origin cloud-deployment
```

### [ ] Step 2: Create Render Service
1. Go to: https://dashboard.render.com
2. New + → Web Service
3. Connect: `manuchaturvedi/email-sent-site`
4. Branch: `cloud-deployment`
5. Runtime: **Docker**
6. Dockerfile: `Dockerfile.render`

### [ ] Step 3: Add Environment Variables in Render

Copy and paste these into Render's Environment tab:

```env
# Razorpay
RAZORPAY_KEY_ID=rzp_live_RgNB6M60lUvK2l
RAZORPAY_KEY_SECRET=i4GM8FcOw34g438OMecg2z78

# Firebase (paste the base64 string from clipboard)
GOOGLE_APPLICATION_CREDENTIALS_JSON=<PASTE_FROM_CLIPBOARD>

# Flask
SECRET_KEY=tHeuznMsSOk20GDNATd6JlYFZx9QyUah

# Chrome (Auto-configured)
CHROME_BIN=/usr/bin/google-chrome
CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
PYTHONPATH=/app
DISPLAY=:99
PORT=5000
```

### [ ] Step 4: Deploy
Click "Create Web Service" - wait 5-10 minutes

### [ ] Step 5: Configure Razorpay Webhook
1. After deploy, note your URL: `https://your-app.onrender.com`
2. Go to: https://dashboard.razorpay.com/app/webhooks
3. Create webhook:
   - URL: `https://your-app.onrender.com/payment/webhook`
   - Event: `payment.captured`
4. Copy webhook secret and add to Render:
   - Variable: `RAZORPAY_WEBHOOK_SECRET`
   - Value: [paste secret]

### [ ] Step 6: Test Your App
1. Visit: `https://your-app.onrender.com`
2. Login with Google
3. Go to Pricing page
4. Test ₹1 payment
5. Verify upgrade works

---

## ✅ All Environment Variables for Render:

| Variable | Value | Note |
|----------|-------|------|
| RAZORPAY_KEY_ID | `rzp_live_RgNB6M60lUvK2l` | Live mode |
| RAZORPAY_KEY_SECRET | `i4GM8FcOw34g438OMecg2z78` | Keep secret |
| RAZORPAY_WEBHOOK_SECRET | `(Get from Razorpay)` | After webhook setup |
| GOOGLE_APPLICATION_CREDENTIALS_JSON | `(In clipboard)` | Base64 Firebase JSON |
| SECRET_KEY | `tHeuznMsSOk20GDNATd6JlYFZx9QyUah` | Flask sessions |
| CHROME_BIN | `/usr/bin/google-chrome` | Auto |
| CHROMEDRIVER_PATH | `/usr/local/bin/chromedriver` | Auto |
| PYTHONPATH | `/app` | Auto |
| DISPLAY | `:99` | Auto |
| PORT | `5000` | Auto |

---

## 🎉 That's It!

Your app will be live in ~10 minutes with:
- ✅ Payment gateway working
- ✅ User authentication
- ✅ Email automation
- ✅ Job tracking
- ✅ Subscription management

**Need help?** Check `DEPLOY_TO_RENDER.md` for detailed guide.
