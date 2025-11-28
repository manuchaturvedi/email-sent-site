"""
Test Email Script - Send sample email to recruiter
This shows exactly what recruiters will receive when users apply through JustMailIt
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from datetime import datetime

# Email Configuration (same as app.py)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "mail@justmailit.in"  # Custom domain email
SMTP_USER = "manudrive06@gmail.com"  # Gmail account for authentication
SENDER_PASSWORD = "ozds nrqo gduy mnwd"  # Gmail App Password

# Test Data
RECRUITER_EMAIL = "manuchaturvedi28mc@gmail.com"  # You as recruiter
USER_EMAIL = "28manuchaturvedi@gmail.com"  # Job seeker (reply-to address)

# Sample Job Application
SUBJECT = "Application for Software Developer Position - John Doe"
EMAIL_BODY = """Dear Hiring Manager,

I am writing to express my interest in the Software Developer position at your esteemed organization. As an experienced professional with expertise in Python, JavaScript, React, Node.js, AWS, Docker, I am confident that I can contribute effectively to your team.

Key Highlights:
• 5+ years experienced in the field
• Strong proficiency in Python, JavaScript, React, Node.js, AWS, Docker
• Proven track record of delivering quality results
• Excellent problem-solving and communication skills

I have attached my resume for your review. I would welcome the opportunity to discuss how my background aligns with your needs.

Thank you for considering my application. I look forward to hearing from you.

Best regards,
John Doe
Email: 28manuchaturvedi@gmail.com
Phone: +91-9876543210"""

# Sample Resume Path (optional - you can attach a real PDF if you want)
RESUME_PATH = None  # Set to actual path if you want to test with resume

def send_test_email():
    """Send test email to see what recruiters receive"""
    try:
        print("=" * 70)
        print("🚀 SENDING TEST EMAIL TO RECRUITER")
        print("=" * 70)
        print(f"📧 FROM: {SENDER_EMAIL} (JustMailIt branded email)")
        print(f"📧 TO: {RECRUITER_EMAIL} (You as recruiter)")
        print(f"📧 BCC: {USER_EMAIL} (User gets copy for tracking)")
        print(f"📧 REPLY-TO: {USER_EMAIL} (Job seeker's email)")
        print(f"📧 SUBJECT: {SUBJECT}")
        print("=" * 70)
        
        # Create message
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL  # mail@justmailit.in
        msg["To"] = RECRUITER_EMAIL
        msg["Bcc"] = USER_EMAIL  # User gets a copy (hidden from recruiter)
        msg["Reply-To"] = USER_EMAIL  # Replies go to job seeker
        msg["Subject"] = SUBJECT
        
        # Attach email body
        msg.attach(MIMEText(EMAIL_BODY, "plain", "utf-8"))
        
        # Attach resume if path provided
        if RESUME_PATH and os.path.exists(RESUME_PATH):
            print(f"📎 Attaching resume: {RESUME_PATH}")
            with open(RESUME_PATH, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(RESUME_PATH)}"
                )
                msg.attach(part)
        else:
            print("📎 No resume attached (set RESUME_PATH to test with resume)")
        
        # Connect to Gmail SMTP
        print("\n🔌 Connecting to Gmail SMTP...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        
        print("🔐 Authenticating...")
        server.login(SMTP_USER, SENDER_PASSWORD)
        
        print("📤 Sending email...")
        recipients = [RECRUITER_EMAIL, USER_EMAIL]  # Both receive the email
        server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        server.quit()
        
        print("\n" + "=" * 70)
        print("✅ EMAIL SENT SUCCESSFULLY!")
        print("=" * 70)
        print("\n📥 Check TWO inboxes:")
        print("   1. RECRUITER: manuchaturvedi28mc@gmail.com (sees application)")
        print("   2. USER: 28manuchaturvedi@gmail.com (gets BCC copy for tracking)")
        print("\n🔍 What you'll see as recruiter:")
        print("   - FROM: mail@justmailit.in (Professional branded sender)")
        print("   - TO: manuchaturvedi28mc@gmail.com")
        print("   - SUBJECT: Application for Software Developer Position - John Doe")
        print("   - When you click REPLY, it will go to: 28manuchaturvedi@gmail.com")
        print("\n🔍 What you'll see as user (28manuchaturvedi@gmail.com):")
        print("   - BCC copy of the EXACT same email")
        print("   - You can see what was sent to the recruiter")
        print("   - Perfect for tracking your applications!")
        print("\n💡 This is exactly what recruiters AND users receive!")
        print("=" * 70)
        
    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ ERROR SENDING EMAIL")
        print("=" * 70)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TEST EMAIL SCRIPT - JustMailIt")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print("\nThis script will send a test job application email")
    print("so you can see exactly what recruiters receive.\n")
    
    # Confirmation
    response = input("Send test email? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        send_test_email()
    else:
        print("\n❌ Cancelled by user")
