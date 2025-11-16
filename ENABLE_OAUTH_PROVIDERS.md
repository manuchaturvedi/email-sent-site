# Enable Google and LinkedIn Authentication in Firebase

## Current Issue
Error: "The given sign-in provider is disabled for this Firebase project"

## Solution: Enable OAuth Providers in Firebase Console

### Step 1: Access Firebase Console
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: **linkedin-7c251**

### Step 2: Enable Google Authentication
1. Click on **Authentication** in the left sidebar
2. Click on the **Sign-in method** tab
3. Find **Google** in the list of providers
4. Click on **Google**
5. Toggle the **Enable** switch to ON
6. Click **Save**

### Step 3: Enable LinkedIn Authentication (OIDC Provider)
1. Still in **Authentication > Sign-in method** tab
2. Scroll down and click **Add new provider**
3. Select **OpenID Connect**
4. Configure the provider:
   - **Name**: LinkedIn
   - **Client ID**: Get from [LinkedIn Developers](https://www.linkedin.com/developers/)
   - **Client Secret**: Get from LinkedIn Developers
   - **Issuer**: `https://www.linkedin.com/oauth`
   - **Provider ID**: `oidc.linkedin` (must match the code)

### Step 4: Create LinkedIn OAuth App (if not already created)
1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Click **Create app**
3. Fill in app details:
   - **App name**: JustMailIt
   - **LinkedIn Page**: Your company page
   - **App logo**: Upload your logo
4. After creation, go to **Auth** tab
5. Add **Authorized redirect URLs**:
   - Copy the OAuth redirect URI from Firebase Console (shown when setting up OIDC provider)
   - It will look like: `https://linkedin-7c251.firebaseapp.com/__/auth/handler`
6. In **Products** tab, request access to:
   - **Sign In with LinkedIn using OpenID Connect**
   - **Share on LinkedIn**
7. Copy **Client ID** and **Client Secret** to Firebase OIDC provider settings

### Alternative: Email/Password Only (Temporary)
If you want to test without OAuth immediately, you can:
1. Comment out the Google/LinkedIn buttons in login.html
2. Use only email/password authentication (already enabled)

### Verify Setup
After enabling:
1. Clear browser cache
2. Refresh the application at http://localhost:5000
3. Try logging in with Google or LinkedIn
4. Check browser console (F12) for any additional errors

### Current Status
- ✅ Email/Password authentication: Enabled
- ⚠️ Google authentication: **Needs to be enabled in Firebase Console**
- ⚠️ LinkedIn authentication: **Needs OIDC provider setup in Firebase Console**

### Files Modified for OAuth
- `sendmail/templates/login.html` - Added `loginWithGoogle()` and `loginWithLinkedIn()` functions
- Both buttons are now enabled and functional once Firebase providers are configured
