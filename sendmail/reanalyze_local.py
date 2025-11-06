from job_post_analyzer import JobPostAnalyzer
import json
import os

JOB_POSTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'job_posts.json')
JOB_POSTS_FILE = os.path.abspath(JOB_POSTS_FILE)

if __name__ == '__main__':
    print('Loading', JOB_POSTS_FILE)
    try:
        with open(JOB_POSTS_FILE, 'r', encoding='utf-8') as f:
            posts = json.load(f)
    except FileNotFoundError:
        print('No job_posts.json found')
        posts = []

    analyzer = JobPostAnalyzer()
    updated = 0
    for i, p in enumerate(posts):
        enhanced = analyzer.analyze_job_post(p)
        changed = False
        for k in ('company','location','skills'):
            if enhanced.get(k) and enhanced.get(k) != p.get(k):
                changed = True
        if changed:
            posts[i] = enhanced
            updated += 1

    with open(JOB_POSTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f'Completed. Posts updated: {updated} / {len(posts)}')
