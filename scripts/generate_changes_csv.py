import sys, json, csv, os
sys.path.insert(0, r'C:\Users\windows 10\Desktop\AI_support')
from sendmail.job_analyzer import JobAnalyzer

ROOT = r'C:\Users\windows 10\Desktop\AI_support'
JOB_POSTS = os.path.join(ROOT, 'job_posts.json')
OUT_CSV = os.path.join(ROOT, 'scripts', 'changed_rows.csv')
OUT_JSON = os.path.join(ROOT, 'scripts', 'changed_rows.json')

with open(JOB_POSTS, 'r', encoding='utf-8') as f:
    data = json.load(f)

analyzer = JobAnalyzer()
changed = []

for i, post in enumerate(data):
    orig_company = (post.get('company') or '').strip()
    orig_location = (post.get('location') or '').strip()
    enhanced = analyzer.analyze_post(post)
    new_company = (enhanced.get('company') or '').strip()
    new_location = (enhanced.get('location') or '').strip()
    if new_company != orig_company or new_location != orig_location:
        changed.append({
            'index': i,
            'email': post.get('email',''),
            'orig_company': orig_company,
            'new_company': new_company,
            'orig_location': orig_location,
            'new_location': new_location,
            'description_snippet': (post.get('description') or '')[:200].replace('\n',' ')
        })

# Write CSV
with open(OUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['index','email','orig_company','new_company','orig_location','new_location','description_snippet'])
    for row in changed:
        writer.writerow([row['index'], row['email'], row['orig_company'], row['new_company'], row['orig_location'], row['new_location'], row['description_snippet']])

# Write JSON snapshot
with open(OUT_JSON, 'w', encoding='utf-8') as jf:
    json.dump(changed, jf, indent=2, ensure_ascii=False)

print(f'Total posts: {len(data)}')
print(f'Changed rows: {len(changed)}')
print(f'CSV -> {OUT_CSV}')
print(f'JSON -> {OUT_JSON}')
