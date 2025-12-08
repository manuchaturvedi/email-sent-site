import sys
sys.path.insert(0, '/app/sendmail')
from database import Database

db = Database('/app/justmailit.db')
posts = db.get_job_posts('manuchaturvedi28mc@gmail.com', limit=None)
print(f'Total job posts: {len(posts)}')
if len(posts) > 0:
    print(f'First job: {posts[0].get("title", "No title")}')
    print(f'Company: {posts[0].get("company", "No company")}')
