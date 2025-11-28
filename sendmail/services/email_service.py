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

# HTML Email Template
def get_html_template(content, title="JustMailIt"):
    """
    Generate professional HTML email template with logo and styling.
    
    Args:
        content: HTML content to include in the email body
        title: Email title/heading
        
    Returns:
        str: Complete HTML email template
    """
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f7fafc; line-height: 1.6;">
    <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #f7fafc;">
        <tr>
            <td style="padding: 40px 20px;">
                <!-- Main Container -->
                <table role="presentation" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    <!-- Header with Logo -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                            <img src="https://justmailit.in/static/images/justmailit-logo.png" alt="JustMailIt" style="max-width: 200px; height: auto; margin-bottom: 10px;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">{title}</h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            {content}
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 30px; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0 0 10px 0; color: #718096; font-size: 14px;">
                                <strong>JustMailIt</strong> - Automate Your Job Search
                            </p>
                            <p style="margin: 0 0 15px 0; color: #a0aec0; font-size: 13px;">
                                🌐 <a href="https://justmailit.in" style="color: #667eea; text-decoration: none;">justmailit.in</a>
                            </p>
                            <p style="margin: 0; color: #cbd5e0; font-size: 12px;">
                                © {datetime.now().year} JustMailIt. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
                
                <!-- Privacy Notice -->
                <table role="presentation" style="max-width: 600px; margin: 20px auto 0;">
                    <tr>
                        <td style="text-align: center; color: #a0aec0; font-size: 12px;">
                            <p style="margin: 0;">
                                You're receiving this because you signed up for JustMailIt.<br>
                                Questions? Reply to this email - we're here to help!
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''


def send_html_email(recipient_email: str, subject: str, html_content: str, plain_text: str = None) -> bool:
    """
    Send HTML email with fallback to plain text.
    
    Args:
        recipient_email: Email address of the recipient
        subject: Email subject line
        html_content: HTML content of the email
        plain_text: Plain text fallback (optional)
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        msg = MIMEMultipart('alternative')
        msg["From"] = f"JustMailIt <{SENDER_EMAIL}>"
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg["Reply-To"] = SENDER_EMAIL
        
        # Attach plain text version first (fallback)
        if plain_text:
            msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        
        # Attach HTML version
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        server.quit()
        
        print(f"[OK] HTML email sent to {recipient_email}: {subject}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send HTML email to {recipient_email}: {e}")
        return False


def send_plain_email(recipient_email: str, subject: str, body: str) -> bool:
    """
    Send a simple plain-text email using SMTP.
    Note: For better user experience, consider using send_html_email() instead.
    
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


def send_verification_email(recipient_email: str, verify_link: str) -> bool:
    """Send professional email verification email with HTML template."""
    subject = "✉️ Verify your JustMailIt account"
    
    html_content = get_html_template(f'''
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 64px; margin-bottom: 20px;">✉️</div>
            <h2 style="color: #2d3748; margin: 0 0 10px 0; font-size: 24px; font-weight: 700;">Verify Your Email</h2>
            <p style="color: #718096; margin: 0; font-size: 16px;">Thanks for signing up!</p>
        </div>
        
        <p style="color: #4a5568; margin: 0 0 25px 0; font-size: 15px; line-height: 1.6;">
            Welcome to JustMailIt! We're excited to help you automate your job search. Please verify your email address to get started.
        </p>
        
        <div style="text-align: center; margin: 35px 0;">
            <a href="{verify_link}" style="display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: #ffffff; text-decoration: none; padding: 16px 40px; border-radius: 8px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.4);">
                Verify Email Address
            </a>
        </div>
        
        <div style="background-color: #f7fafc; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea; margin: 30px 0;">
            <p style="color: #4a5568; margin: 0; font-size: 14px;">
                <strong style="color: #2d3748;">⏰ Link expires in 24 hours</strong><br>
                If you didn't create an account, you can safely ignore this email.
            </p>
        </div>
        
        <p style="color: #718096; margin: 25px 0 0 0; font-size: 14px; text-align: center;">
            Or copy and paste this link:<br>
            <a href="{verify_link}" style="color: #667eea; word-break: break-all; font-size: 13px;">{verify_link}</a>
        </p>
    ''', "Verify Your Email")
    
    plain_text = f"""Hi,

Thanks for signing up for JustMailIt. Please verify your email address by clicking the link below:

{verify_link}

This link will expire in 24 hours.

If you didn't create this account, please ignore this email.

Best regards,
JustMailIt Team"""
    
    return send_html_email(recipient_email, subject, html_content, plain_text)


def send_password_reset_email(recipient_email: str, reset_link: str) -> bool:
    """Send professional password reset email with HTML template."""
    subject = "🔐 Reset your JustMailIt password"
    
    html_content = get_html_template(f'''
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 64px; margin-bottom: 20px;">🔐</div>
            <h2 style="color: #2d3748; margin: 0 0 10px 0; font-size: 24px; font-weight: 700;">Reset Your Password</h2>
            <p style="color: #718096; margin: 0; font-size: 16px;">We received a request to reset your password</p>
        </div>
        
        <p style="color: #4a5568; margin: 0 0 25px 0; font-size: 15px; line-height: 1.6;">
            Click the button below to set a new password for your JustMailIt account. If you didn't request this, you can safely ignore this email.
        </p>
        
        <div style="text-align: center; margin: 35px 0;">
            <a href="{reset_link}" style="display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: #ffffff; text-decoration: none; padding: 16px 40px; border-radius: 8px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.4);">
                Reset Password
            </a>
        </div>
        
        <div style="background-color: #fff5f5; padding: 20px; border-radius: 8px; border-left: 4px solid #fc8181; margin: 30px 0;">
            <p style="color: #742a2a; margin: 0; font-size: 14px;">
                <strong>⏰ This link expires in 1 hour</strong><br>
                <span style="color: #c53030;">For your security, please don't share this link with anyone.</span>
            </p>
        </div>
        
        <p style="color: #718096; margin: 25px 0 0 0; font-size: 14px; text-align: center;">
            Or copy and paste this link:<br>
            <a href="{reset_link}" style="color: #667eea; word-break: break-all; font-size: 13px;">{reset_link}</a>
        </p>
    ''', "Reset Your Password")
    
    plain_text = f"""Hi,

We received a request to reset your JustMailIt password. Click the link below to set a new password:

{reset_link}

This link will expire in 1 hour. If you did not request a password reset, you can ignore this email.

Best regards,
JustMailIt Team"""
    
    return send_html_email(recipient_email, subject, html_content, plain_text)


def send_welcome_email(recipient_email: str, dashboard_url: str) -> bool:
    """Send professional welcome email with HTML template."""
    subject = "🎉 Welcome to JustMailIt - Your Job Search Automation Starts Now!"
    
    html_content = get_html_template(f'''
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 64px; margin-bottom: 20px;">🎉</div>
            <h2 style="color: #2d3748; margin: 0 0 10px 0; font-size: 26px; font-weight: 700;">Welcome to JustMailIt!</h2>
            <p style="color: #718096; margin: 0; font-size: 16px;">Your job search automation starts now</p>
        </div>
        
        <p style="color: #4a5568; margin: 0 0 25px 0; font-size: 15px; line-height: 1.6;">
            Congratulations! Your email has been verified and you're all set to start automating your job applications.
        </p>
        
        <div style="background: linear-gradient(135deg, #e0e7ff, #f3e8ff); padding: 25px; border-radius: 10px; margin: 25px 0;">
            <h3 style="color: #5a67d8; margin: 0 0 15px 0; font-size: 18px; font-weight: 700;">✨ What You Can Do:</h3>
            <ul style="color: #4c51bf; margin: 0; padding-left: 20px; line-height: 1.8;">
                <li>🤖 Automate LinkedIn job scraping</li>
                <li>📧 Send personalized emails to recruiters</li>
                <li>🎯 Target specific roles and skills</li>
                <li>📊 Track your application progress</li>
                <li>⏰ Schedule automated job searches</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 35px 0;">
            <a href="{dashboard_url}" style="display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: #ffffff; text-decoration: none; padding: 16px 40px; border-radius: 8px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.4);">
                Go to Dashboard
            </a>
        </div>
        
        <div style="background-color: #fffff0; padding: 20px; border-radius: 8px; border-left: 4px solid #f6ad55; margin: 30px 0;">
            <p style="color: #744210; margin: 0 0 10px 0; font-size: 14px;">
                <strong>💡 Pro Tip:</strong>
            </p>
            <p style="color: #975a16; margin: 0; font-size: 14px; line-height: 1.6;">
                Make sure your email content includes your contact information (email and phone) so recruiters can easily reach you!
            </p>
        </div>
        
        <p style="color: #4a5568; margin: 25px 0 0 0; font-size: 14px; line-height: 1.6; text-align: center;">
            Need help getting started? Just reply to this email and we'll assist you!
        </p>
    ''', "Welcome to JustMailIt")
    
    plain_text = f"""Welcome to JustMailIt!

Congratulations! Your email has been verified.

What You Can Do:
✅ Automate LinkedIn job scraping
✅ Send personalized emails to recruiters
✅ Target specific roles and skills
✅ Track your application progress
✅ Schedule automated job searches

Getting Started:
1. Sign in at: {dashboard_url}
2. Complete your profile
3. Use our AI Email Generator
4. Start your automation!

💡 Pro Tip: Include your contact info in emails so recruiters can reach you.

Need help? Just reply to this email.

Best regards,
The JustMailIt Team"""
    
    return send_html_email(recipient_email, subject, html_content, plain_text)


def send_automation_summary_email(recipient_email: str, emails_sent: int, search_role: str, mode: str = "automation") -> bool:
    """Send professional automation summary email with HTML template."""
    subject = f"✅ Automation Complete - {emails_sent} Emails Sent Successfully"
    
    mode_text = "scraping and sending" if mode == "automation" else "quick batch sending"
    
    html_content = get_html_template(f'''
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 64px; margin-bottom: 20px;">✅</div>
            <h2 style="color: #2d3748; margin: 0 0 10px 0; font-size: 24px; font-weight: 700;">Automation Complete!</h2>
            <p style="color: #718096; margin: 0; font-size: 16px;">Your emails have been sent successfully</p>
        </div>
        
        <div style="background: linear-gradient(135deg, #d4fc79, #96e6a1); padding: 30px; border-radius: 10px; text-align: center; margin: 25px 0;">
            <div style="font-size: 48px; font-weight: 700; color: #22543d; margin-bottom: 10px;">{emails_sent}</div>
            <div style="color: #276749; font-size: 18px; font-weight: 600;">Emails Sent to Recruiters</div>
        </div>
        
        <div style="background-color: #f7fafc; padding: 25px; border-radius: 8px; margin: 25px 0;">
            <h3 style="color: #2d3748; margin: 0 0 15px 0; font-size: 16px; font-weight: 700;">📊 Summary:</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #718096; font-size: 14px;">🔍 Search Role:</td>
                    <td style="padding: 8px 0; color: #2d3748; font-size: 14px; font-weight: 600; text-align: right;">{search_role}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #718096; font-size: 14px;">📧 Emails Sent:</td>
                    <td style="padding: 8px 0; color: #2d3748; font-size: 14px; font-weight: 600; text-align: right;">{emails_sent}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #718096; font-size: 14px;">⚙️ Mode:</td>
                    <td style="padding: 8px 0; color: #2d3748; font-size: 14px; font-weight: 600; text-align: right;">{mode_text.title()}</td>
                </tr>
            </table>
        </div>
        
        <div style="background-color: #ebf8ff; padding: 20px; border-radius: 8px; border-left: 4px solid #4299e1; margin: 30px 0;">
            <p style="color: #2c5282; margin: 0; font-size: 14px; line-height: 1.6;">
                <strong>📬 What's Next?</strong><br>
                Keep an eye on your inbox for responses from recruiters. Good luck with your job search!
            </p>
        </div>
        
        <div style="text-align: center; margin: 35px 0;">
            <a href="https://justmailit.in/dashboard" style="display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: #ffffff; text-decoration: none; padding: 14px 35px; border-radius: 8px; font-weight: 600; font-size: 15px; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.4); margin: 0 5px;">
                View Dashboard
            </a>
            <a href="https://justmailit.in/automation" style="display: inline-block; background: #ffffff; color: #667eea; text-decoration: none; padding: 14px 35px; border-radius: 8px; font-weight: 600; font-size: 15px; border: 2px solid #667eea; margin: 0 5px;">
                Start Another
            </a>
        </div>
    ''', "Automation Complete")
    
    plain_text = f"""✅ Automation Complete!

Your email automation has finished successfully.

📊 SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Emails Sent: {emails_sent}
🔍 Search Role: {search_role}
⚙️ Mode: {mode_text}

📬 What's Next?
Keep an eye on your inbox for responses from recruiters. Good luck!

View Dashboard: https://justmailit.in/dashboard

Best regards,
JustMailIt Team"""
    
    return send_html_email(recipient_email, subject, html_content, plain_text)
