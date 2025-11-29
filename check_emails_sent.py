import sqlite3

conn = sqlite3.connect('sendmail/justmailit.db')
c = conn.cursor()

c.execute('SELECT COUNT(*) FROM sent_emails')
total = c.fetchone()[0]

c.execute('SELECT to_email, subject, sent_at FROM sent_emails ORDER BY sent_at DESC LIMIT 10')
recent = c.fetchall()

print("=" * 80)
print("EMAILS SENT")
print("=" * 80)
print(f"Total emails sent: {total}")
print("\nLast 10 emails:")
for email in recent:
    print(f"\n  To: {email[0]}")
    print(f"  Subject: {email[1][:60]}...")
    print(f"  Sent: {email[2]}")

conn.close()
