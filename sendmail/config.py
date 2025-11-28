"""
Application configuration settings.
Centralizes all configuration constants and environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ========== Flask Configuration ==========
SECRET_KEY = "super-secret-key-change-this"


# ========== File Storage Configuration ==========
UPLOAD_FOLDER = 'uploads'
JOB_POSTS_FILE = 'job_posts.json'
SENT_EMAILS_FILE = 'sent_emails.json'


# ========== Payment Gateway Configuration ==========
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_live_RgNB6M60lUvK2l")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "i4GM8FcOw34g438OMecg2z78")


# ========== LinkedIn Configuration ==========
# Optional persistent Chrome profile directory helps preserve LinkedIn login state
CHROME_PROFILE_DIR = None
_env_profile = os.getenv("CHROME_PROFILE_DIR")
_default_profile = r"D:\Profile"

if _env_profile:
    CHROME_PROFILE_DIR = _env_profile
elif os.path.exists(_default_profile):
    CHROME_PROFILE_DIR = _default_profile

# LinkedIn credentials for programmatic login (fallback)
LINKEDIN_EMAIL = "manudrive04@gmail.com"
LINKEDIN_PASSWORD = "Jpking@232"


# ========== Subscription Plans Configuration ==========
SUBSCRIPTION_PLANS = {
    'free': {
        'name': 'Free Plan',
        'daily_email_limit': 10,
        'price': 0,
        'features': [
            '10 emails per day',
            'Basic automation',
            'Email support'
        ]
    },
    'basic': {
        'name': 'Basic Plan',
        'daily_email_limit': 50,
        'price': 499,
        'features': [
            '50 emails per day',
            'Advanced automation',
            'Priority support',
            'Email tracking'
        ]
    },
    'premium': {
        'name': 'Premium Plan',
        'daily_email_limit': 200,
        'price': 999,
        'features': [
            '200 emails per day',
            'Unlimited automation',
            '24/7 priority support',
            'Advanced analytics',
            'Custom templates'
        ]
    }
}


# ========== Admin Configuration ==========
ADMIN_EMAIL = "manuchaturvedi28mc@gmail.com"


# ========== Application Defaults ==========
DEFAULT_SEARCH_TIME_PERIOD = 'past-week'
DEFAULT_EMAIL_LIMIT_FREE = 10
DEFAULT_EMAIL_LIMIT_BASIC = 50
DEFAULT_EMAIL_LIMIT_PREMIUM = 200
