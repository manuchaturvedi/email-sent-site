import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from selenium import webdriver
from selenium.webdriver.common.by import By

# --- Flask setup ---
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ✅ Fixed Chrome profile path
CHROME_PROFILE_PATH = r"D:\Profile"  # must exist & have LinkedIn logged in


# --- Email sending ---
def send_email(smtp_server, smtp_port, sender_email, sender_app_password,
               receiver_email, subject, body, attachment_path=None):
    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(attachment_path)}"
            )
            msg.attach(part)

        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(sender_email, sender_app_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"✅ Sent email to {receiver_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {receiver_email}: {e}")
        return False


# --- LinkedIn scraping (headless) ---
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={CHROME_PROFILE_PATH}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    return driver


def scrape_emails_from_linkedin():
    search_urls = [
        "https://www.linkedin.com/search/results/content/?datePosted=%22past-week%22&keywords=devops%20hiring%20OR%20cloud%20hiring%20OR%20site-reliability%20hiring",
        "https://www.linkedin.com/in/bharath-kumar-reddy2103/recent-activity/all/",
        "https://www.linkedin.com/in/rohit-barahate-patil-1297a1210/"
    ]

    driver = init_driver()
    all_emails = set()

    try:
        for url in search_urls:
            driver.get(url)
            time.sleep(4)
            for _ in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
            mailtos = driver.find_elements(By.XPATH, "//a[contains(@href, 'mailto:')]")
            for m in mailtos:
                href = m.get_attribute("href")
                if href and href.startswith("mailto:"):
                    all_emails.add(href.replace("mailto:", ""))
    finally:
        driver.quit()

    print(f"🧾 Scraped {len(all_emails)} emails: {all_emails}")
    return list(all_emails)


# --- Flask route ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        smtp_server = request.form.get("smtp_server", "smtp.gmail.com").strip()
        smtp_port = request.form.get("smtp_port", "587").strip()
        sender_email = request.form.get("sender_email", "").strip()
        sender_app_password = (
            request.form.get("sender_app_password", "").strip()
            or os.getenv("SMTP_APP_PASSWORD")
        )
        subject = request.form.get("subject", "").strip()
        content = request.form.get("content", "").strip()
        resume = request.files.get("resume")

        if not (sender_email and sender_app_password and subject and content):
            flash("Please fill all required fields (email, app password, subject, content).", "danger")
            return redirect(url_for("index"))

        attachment_path = None
        if resume and resume.filename:
            filename = secure_filename(resume.filename)
            attachment_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            resume.save(attachment_path)

        flash("Scraping LinkedIn emails (headless mode)... please wait.", "info")

        try:
            emails = scrape_emails_from_linkedin()
        except Exception as e:
            flash(f"Error scraping LinkedIn: {e}", "danger")
            if attachment_path and os.path.exists(attachment_path):
                os.remove(attachment_path)
            return redirect(url_for("index"))

        if not emails:
            flash("No emails found.", "warning")
            return redirect(url_for("index"))

        success = 0
        for email in emails:
            if send_email(smtp_server, smtp_port, sender_email, sender_app_password,
                          email, subject, content, attachment_path):
                success += 1
            time.sleep(1)

        if attachment_path and os.path.exists(attachment_path):
            os.remove(attachment_path)

        flash(f"✅ Sent {success}/{len(emails)} emails successfully!", "success")
        return redirect(url_for("index"))

    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
