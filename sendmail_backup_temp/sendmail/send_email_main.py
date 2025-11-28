from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

# Function to send email with attachment
def send_email(smtp_server, smtp_port, sender_email, sender_password, receiver_email, subject, body, attachment_path=None):
    try:
        # Set up the MIME
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Attach file (if provided)
        if attachment_path:
            attachment = open(attachment_path, "rb")
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)  # Encode the attachment in base64
            part.add_header('Content-Disposition', f'attachment; filename={attachment_path.split("/")[-1]}')
            msg.attach(part)
            attachment.close()

        # Set up the server and login
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        # Send the email
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print(f"Email sent to {receiver_email}")
        return True  # Indicate email was sent successfully
    except Exception as e:
        print(f"Failed to send email to {receiver_email}. Error: {e}")
        return False  # Indicate failure to send email

# Read the email content from a file
def get_email_content(content_file):
    if not os.path.exists(content_file):
        raise FileNotFoundError(f"{content_file} does not exist.")
    with open(content_file, 'r') as file:
        content = file.read()
    return content

# Save scraped emails to a file
def save_emails_to_file(emails, filename='C:/Users/28man/Downloads/project_and_test/flipkart/email_linkedln/email_list.txt'):
    # Remove duplicates by converting the list to a set and back to a list
    emails = list(set(emails))
    if not emails:
        print("No emails to save.")
        return
    
    with open(filename, 'w') as file:
        for email in emails:
            file.write(email + '\n')
    print(f"Saved {len(emails)} email(s) to {filename}.")

# Check if email has been sent by checking history file
def get_sent_email_history(history_file):
    if os.path.exists(history_file):
        with open(history_file, 'r') as file:
            sent_emails = file.read().splitlines()
        return set(sent_emails)
    else:
        return set()

# Add email to sent history
def add_to_sent_history(history_file, email):
    with open(history_file, 'a') as file:
        file.write(email + '\n')
    print(f"Added {email} to sent history.")

# Scrape email addresses from LinkedIn
def scrape_emails_from_linkedin(driver, search_url):
    driver.get(search_url)
    time.sleep(5)  # Allow the page to load

    # Scroll 5 times to load more content
    for _ in range(1):  # Adjust the number of scrolls as needed
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  # Wait for the content to load

        # Check and click on "Show more results" if available
        try:
            show_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Show more results')]")
            show_more_button.click()
            time.sleep(3)  # Wait for more results to load
            print("Clicked 'Show more results'.")
        except Exception:
            pass

    # Extract all mailto links (email addresses)
    mailtos = driver.find_elements(By.XPATH, "//a[contains(@href, 'mailto:')]")
    emails = [mailto.get_attribute('href').replace('mailto:', '') for mailto in mailtos]
    return emails

# Main function
def main():
    # Configuration for the email
    smtp_server = 'smtp.gmail.com'  # Example: Gmail SMTP server
    smtp_port = 587  # Standard port for TLS
    sender_email = 'manudrive06@gmail.com'
    sender_password = 'ozds nrqo gduy mnwd'  # Use app password if using Gmail 
    content_file = 'C:/Users/28man/Downloads/project_and_test/flipkart/email_linkedln/email_context.txt'  # File containing the email body
    subject = 'Application for DevOps Cloud Engineer Role – Manu Chaturvedi'  # Email subject
    attachment_path = 'C:/Users/28man/Downloads/project_and_test/flipkart/Manu_DEVOPS_Cloud.pdf'  # Path to the file you want to attach

    # List of LinkedIn search URLs (DevOps and Cloud hiring, past week)
    search_urls = [
        "https://www.linkedin.com/search/results/content/?datePosted=%22past-week%22&keywords=devops%20hiring%20OR%20cloud%20hiringOR%20site-reliability%20hiring",
       
    ]

    # Path to the Chrome WebDriver and profile
    chrome_driver_path = "C:/Users/28man/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe"
    chrome_profile_path = "C:\\Users\\28man\\Documents\\linkedln"

    # Set up Chrome options to use the existing profile
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={chrome_profile_path}")
    options.add_argument("--start-maximized")

    # Initialize WebDriver
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    # Email history file to track sent emails
    email_history_file = 'C:/Users/28man/Downloads/project_and_test/flipkart/email_linkedln/email_history.txt'

    try:
        # Get the list of already sent emails
        sent_emails = get_sent_email_history(email_history_file)

        all_email_addresses = set()  # Use a set to keep emails unique
        for search_url in search_urls:
            # Scrape email addresses from each LinkedIn URL
            email_addresses = scrape_emails_from_linkedin(driver, search_url)
            for email in email_addresses:
                if email not in all_email_addresses and email not in sent_emails:
                    print(f"Scraped email: {email}")  # Print each email immediately after scraping
                    all_email_addresses.add(email)  # Add to the set to ensure uniqueness

        # Save the scraped emails to a file after collecting from all URLs
        if all_email_addresses:
            save_emails_to_file(all_email_addresses)
            print(f"Scraped {len(all_email_addresses)} unique email(s).")
        else:
            print("No email addresses found.")

        # Get email content
        email_content = get_email_content(content_file)
        email_list = list(all_email_addresses)  # Convert the set to a list to send emails

        # Send email to each recipient with the attachment
        for receiver_email in email_list:
            if send_email(smtp_server, smtp_port, sender_email, sender_password, receiver_email, subject, email_content, attachment_path):
                add_to_sent_history(email_history_file, receiver_email)  # Add email to history after sending

        # Save the remaining emails (those that were not emailed)
        save_emails_to_file(all_email_addresses)

    except FileNotFoundError as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
