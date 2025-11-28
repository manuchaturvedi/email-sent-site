"""
Email service for sending transactional emails and alerts.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "mail@justmailit.in"
SMTP_USER = "manudrive06@gmail.com"
SENDER_PASSWORD = "ozds nrqo gduy mnwd"
ADMIN_EMAIL = "manudrive06@gmail.com"


def send_plain_email(recipient_email: str, subject: str, body: str) -> bool:
    """
    Send a simple plain-text email using SMTP.
    
    Args:
        recipient_email: Email address of the recipient
        subject: Email subject line
        body: Plain text body of the email
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        msg = MIMEMultipart()
        msg["From"] = f"JustMailIt <{SENDER_EMAIL}>"
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg["Reply-To"] = SENDER_EMAIL
        msg.attach(MIMEText(body, "plain", "utf-8"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        server.quit()
        
        print(f"[OK] Email sent to {recipient_email}: {subject}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email to {recipient_email}: {e}")
        return False


def send_admin_alert(user_email: str, error_type: str, error_message: str, additional_info: dict = None):
    """
    Send alert email to admin when automation or system errors occur.
    
    Args:
        user_email: Email of the user who experienced the error
        error_type: Type/category of the error
        error_message: Detailed error message
        additional_info: Optional dict with additional context
    """
    try:
        subject = f"🚨 JustMailIt Automation Failed - {error_type}"
        
        body = f"""
AUTOMATION FAILURE ALERT
========================

User: {user_email}
Error Type: {error_type}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Error Details:
{error_message}

"""
        
        if additional_info:
            body += "\nAdditional Information:\n"
            for key, value in additional_info.items():
                body += f"  {key}: {value}\n"
        
        body += f"""
---
This is an automated alert from JustMailIt monitoring system.
Please investigate and resolve the issue.

Dashboard: https://justmailit.in/admin
"""
        
        send_plain_email(recipient_email=ADMIN_EMAIL, subject=subject, body=body)
        print(f"[ALERT] Admin notification sent for {error_type}")
    except Exception as e:
        print(f"[ERROR] Failed to send admin alert: {e}")
