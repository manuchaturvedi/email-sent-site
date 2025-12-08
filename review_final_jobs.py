#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()

# Final manual fixes for the stubborn cases
manual_fixes = {
    442: "Location Not Specified",   # Likely doesn't have clear location
    472: "Location Not Specified",
    496: "Location Not Specified",
    538: "Location Not Specified",
    340: "Location Not Specified",
    790: "Location Not Specified",
    93: "Location Not Specified",
    127: "Location Not Specified",
    193: "Location Not Specified",
    654: "Location Not Specified",
    671: "Location Not Specified",
    79: "Location Not Specified",
    253: "Location Not Specified",
    713: "Location Not Specified",
}

# But let's check each one first to see if we can extract something
problem_ids = [442, 472, 496, 538, 340, 790, 93, 127, 193, 654, 671, 79, 253, 713]

for job_id in problem_ids:
    cursor.execute('SELECT title, full_text FROM job_posts WHERE id = ?', (job_id,))
    result = cursor.fetchone()
    if result:
        title, full_text = result
        print(f"\n{'='*80}")
        print(f"ID {job_id}:")
        print(f"Title: {title[:100]}")
        
        # Show first 400 chars of text to help identify location
        if full_text:
            text_sample = full_text[:400].replace('\n', ' ')
            print(f"Text: {text_sample}...")

print(f"\n{'='*80}")
print("Please review the above and determine appropriate locations.")

conn.close()
