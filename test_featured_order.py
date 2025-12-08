import sys
sys.path.insert(0, '/app/sendmail')
from database import Database

db = Database('/app/justmailit.db')
posts = db.get_job_posts('manuchaturvedi28mc@gmail.com', limit=20)

print(f'Total posts retrieved: {len(posts)}')
print('\nFirst 10 jobs (should show featured first):')
for i, post in enumerate(posts[:10], 1):
    featured = '⭐ FEATURED' if post.get('featured') else '📄 Normal'
    company = post.get('company', 'Unknown')[:30]
    title = post.get('title', 'No title')[:40]
    print(f'{i}. {featured} | {company} | {title}')
