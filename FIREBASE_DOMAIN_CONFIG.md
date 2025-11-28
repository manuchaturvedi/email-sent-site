# Firebase Custom Domain Configuration Guide

## Problem
Password reset and email verification links are redirecting to Firebase's default domain instead of justmailit.in.

## Solution
You need to configure Firebase to use your custom domain for action links.

## Steps to Fix

### 1. Add Authorized Domain in Firebase Console

1. Go to: https://console.firebase.google.com/project/justmailit-d6f2d/authentication/settings
2. Click on **"Templates"** tab at the top
3. Scroll down to **"Authorized domains"** section
4. Click **"Add domain"**
5. Enter: `justmailit.in`
6. Click **"Add"**

### 2. Configure Action URL (CRITICAL)

1. In the same **Templates** tab, scroll to **"Customize action URL"**
2. You should see a field for **"Action URL"**
3. Enter: `https://justmailit.in`
4. Click **"Save"**

This tells Firebase to redirect ALL email action links (password reset, email verification) to your domain instead of the default Firebase hosted page.

### 3. Verify Email Templates

1. Still in **Templates** tab, check these templates:
   - **Password reset** template
   - **Email address verification** template

2. Each template should have variables like:
   ```
   %LINK%
   ```
   This link will now point to: `https://justmailit.in/?mode=resetPassword&oobCode=xxxxx`

3. Make sure templates look professional and mention your domain

### 4. Test the Flow

After configuration:

#### Test Password Reset:
1. Go to https://justmailit.in
2. Click "Forgot Password"
3. Enter your email
4. Check email inbox
5. Click the reset link
6. **Should redirect to**: `https://justmailit.in/?mode=resetPassword&oobCode=xxxxx`
7. Custom modal should appear on your site

#### Test Email Verification:
1. Sign up with new email
2. Check verification email
3. Click verification link
4. **Should redirect to**: `https://justmailit.in/?verified=true`
5. Your custom landing page should show success message

### 5. Code Changes Already Made

✅ Updated `actionCodeSettings` to use `https://justmailit.in` for:
- Email verification: `https://justmailit.in/?verified=true`
- Password reset: `https://justmailit.in/?reset=success`
- Facebook email verification: `https://justmailit.in/?verified=true`

✅ Custom password reset modal handler already detects `?mode=resetPassword&oobCode=` in URL

## Important Notes

### URL Parameters Handled:
- `?mode=resetPassword&oobCode=xxxxx` → Shows custom password reset modal
- `?verified=true` → Can show success message (optional)
- `?reset=success` → Can show success message (optional)

### Domain Must Match:
- Firebase action URL: `https://justmailit.in`
- Code settings: `https://justmailit.in`
- Actual hosted site: `https://justmailit.in`

All three MUST match exactly (including https://).

## Troubleshooting

### If links still go to Firebase domain:
1. Clear browser cache
2. Wait 5-10 minutes for Firebase changes to propagate
3. Try in incognito/private window
4. Check Firebase console that domain is saved
5. Ensure you clicked "Save" after entering action URL

### If reset modal doesn't appear:
1. Open browser console (F12)
2. Look for: "Password reset mode detected"
3. Check URL has: `?mode=resetPassword&oobCode=`
4. Verify `handlePasswordReset()` is being called on page load

### If you see "Invalid Reset Link":
1. Reset code expired (1 hour validity)
2. Code already used
3. Request new password reset

## Next Deployment

After making Firebase console changes, deploy the updated landing.html:

```powershell
# Transfer to Pi
scp "c:\Users\windows 10\Desktop\AI_support\sendmail\templates\landing.html" manu@192.168.31.36:/home/manu/justmailit/sendmail/templates/

# SSH to Pi and restart
ssh manu@192.168.31.36 "docker cp /home/manu/justmailit/sendmail/templates/landing.html justmailit-app:/app/sendmail/templates/ && docker restart justmailit-app"
```

## Verification Checklist

- [ ] Added `justmailit.in` to Firebase authorized domains
- [ ] Set Action URL to `https://justmailit.in` in Firebase console
- [ ] Deployed updated landing.html to production
- [ ] Tested password reset flow end-to-end
- [ ] Tested email verification flow end-to-end
- [ ] Verified links redirect to justmailit.in (not Firebase)
- [ ] Custom modals appear correctly on your domain

---

**After completing these steps, all Firebase email links will redirect to your domain with the proper action codes, and your custom modals will handle the password reset and verification flows beautifully!**
