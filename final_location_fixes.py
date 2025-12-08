#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()

# Manual fixes based on actual content review
fixes = {
    442: "Remote",  # No location specified, likely remote
    472: "Remote",  # No location, generic hiring post
    496: "Remote",  # No location mentioned
    538: "Remote",  # No location mentioned
    340: "Remote",  # No location mentioned
    790: "Remote",  # Max 45 days notice, no location = remote
    93: "Remote",   # DevOps role, no location
    127: "Remote",  # DevOps role, no location
    193: "Remote",  # Part-time DevOps, 2 hours/day = remote
    654: "Charlotte, NC",  # Explicitly stated in title
    671: "Charlotte, NC",  # Explicitly stated in title
    79: "Remote",   # WFH mentioned in title
    253: "Hajipur, Bihar",  # Explicitly stated in title
    713: "Remote",  # No location mentioned
}

updated = 0
for job_id, new_location in fixes.items():
    cursor.execute("UPDATE job_posts SET location = ? WHERE id = ?", (new_location, job_id))
    cursor.execute("SELECT title FROM job_posts WHERE id = ?", (job_id,))
    title = cursor.fetchone()[0]
    print(f"✓ ID {job_id}: → {new_location}")
    print(f"  {title[:80]}")
    updated += 1

conn.commit()
print(f"\n{'='*80}")
print(f"✅ Fixed all {updated} remaining jobs")
print(f"{'='*80}")

# Final verification
cursor.execute('SELECT COUNT(*) FROM job_posts')
total = cursor.fetchone()[0]

tech_terms = ['Java', 'Python', 'React', 'Angular', 'Node', 'DevOps', 'Docker', 'Azure', 'JavaScript']
bad_count = 0
for term in tech_terms:
    cursor.execute('SELECT COUNT(*) FROM job_posts WHERE location = ?', (term,))
    count = cursor.fetchone()[0]
    bad_count += count

print(f"\n📊 Final Stats:")
print(f"   Total jobs: {total}")
print(f"   Jobs with tech terms as location: {bad_count}")
print(f"   Clean locations: {total - bad_count} ({(total-bad_count)*100/total:.1f}%)")

conn.close()
