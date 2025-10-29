# app.py
import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import smtplib
from dotenv import load_dotenv

# Load .env (optional) - useful for keeping secrets out of code
load_dotenv()

# CONFIG
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB upload limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.secret_key = os.getenv("FLASK_SECRET_KEY", str(uuid.uuid4()))  # change in production!

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def send_email(smtp_server, smtp_port, sender_email, sender_password,
               receiver_email, subject, body, attachment_path=None):
    """Send a single email with optional attachment. Returns (success, message)."""
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
            part.add_header("Content-Disposition",
                            f"attachment; filename={os.path.basename(attachment_path)}")
            msg.attach(part)

        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        return True, f"Email sent to {receiver_email}"
    except Exception as e:
        return False, str(e)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Get form fields
        smtp_server = request.form.get("smtp_server", "smtp.gmail.com")
        smtp_port = request.form.get("smtp_port", "587")
        sender_email = request.form.get("sender_email", "").strip()
        # Accept smtp password either from form or from env var if left blank
        sender_password = request.form.get("sender_password", "").strip() or os.getenv("SMTP_APP_PASSWORD")
        receiver_email = request.form.get("receiver_email", "").strip()
        subject = request.form.get("subject", "").strip()
        content = request.form.get("content", "").strip()

        # Basic validation
        if not (sender_email and sender_password and receiver_email):
            flash("Please provide sender email, SMTP password (or set SMTP_APP_PASSWORD env), and receiver email.", "danger")
            return redirect(url_for("index"))

        # Handle file upload
        resume = request.files.get("resume")
        attachment_path = None
        if resume and resume.filename:
            if allowed_file(resume.filename):
                filename = secure_filename(resume.filename)
                # avoid collisions
                unique_name = f"{uuid.uuid4().hex}_{filename}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
                resume.save(save_path)
                attachment_path = save_path
            else:
                flash("Unsupported file type. Allowed: pdf, doc, docx", "danger")
                return redirect(url_for("index"))

        # Send the email
        success, msg = send_email(smtp_server, smtp_port, sender_email, sender_password,
                                 receiver_email, subject, content, attachment_path)

        # Clean up uploaded file (optional): remove file after sending
        if attachment_path and os.path.exists(attachment_path):
            try:
                os.remove(attachment_path)
            except Exception:
                pass

        if success:
            flash("Email sent successfully!", "success")
        else:
            flash(f"Failed to send email: {msg}", "danger")

        return redirect(url_for("index"))

    # GET
    return render_template("index.html")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # optional: protected download of uploaded file if you need to serve it
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

if __name__ == "__main__":
    # For development only. Use a proper WSGI server for production.
    app.run(host="0.0.0.0", port=5000, debug=True)
