# LinkedIn Email Automation

A Flask web application for automating LinkedIn email outreach using Selenium and Firebase authentication.

## Features
- 🔐 Secure user authentication with Firebase
- 📧 Automated email sending to LinkedIn contacts
- 🤖 Headless Chrome automation
- 📎 Resume attachment support
- 🎯 Custom email templates

## Setup Instructions

1. **Environment Setup**
   ```bash
   # Create virtual environment
   python -m venv .venv
   
   # Activate virtual environment
   # On Windows:
   .venv\Scripts\activate
   # On Linux/Mac:
   source .venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Firebase Configuration**
   - Create a Firebase project at [Firebase Console](https://console.firebase.google.com)
   - Enable Email/Password authentication
   - Download your Firebase Admin SDK JSON
   - Rename it to `firebase-credentials.json` and place in the project root
   - Copy `.env.example` to `.env` and fill in your Firebase credentials

3. **Environment Variables**
   Copy `.env.example` to `.env` and fill in:
   - Flask secret key
   - Firebase configuration
   - SMTP settings

4. **Running the Application**
   ```bash
   python app.py
   ```
   Visit `http://localhost:5000` in your browser.

## Security Notes
- Never commit `.env` or Firebase credentials to version control
- Keep your Firebase Admin SDK JSON private
- Use environment variables for sensitive data
- Regularly update dependencies

## Project Structure
```
sendmail/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not in git)
├── .env.example       # Environment variables template
├── firebase-credentials.json  # Firebase Admin SDK (not in git)
├── templates/
│   ├── index_live.html    # Main application interface
│   ├── index.html         # Static version
│   └── login.html         # Authentication pages
└── uploads/          # Temporary storage for uploads
```

## Dependencies
- Flask
- Firebase Admin SDK
- Selenium
- python-dotenv
- email libraries