# 🔐 Firebase Credentials for Render Deployment

## Copy This JSON Content:
Open file: `sendmail/linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json`
Copy the ENTIRE contents (all 14 lines)

## Convert to Base64:
1. Go to: https://www.base64encode.org/
2. Paste the entire JSON content
3. Click "Encode"
4. Copy the resulting base64 string

## Add to Render Environment Variables:
```
Variable Name: GOOGLE_APPLICATION_CREDENTIALS_JSON
Value: [paste your base64 string here]
```

## ⚠️ SECURITY NOTE:
- Never commit Firebase credentials to GitHub
- Only add them as environment variables in Render
- The app will automatically decode them in production

## Quick Command (if you have base64 tool):
```bash
base64 -w 0 sendmail/linkedin-7c251-firebase-adminsdk-fbsvc-c9b46f2c3d.json
```

This will output the base64 string directly.