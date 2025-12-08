#!/usr/bin/env python3
import sqlite3
import re

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()

# Common tech/skill terms that shouldn't be locations
bad_location_patterns = [
    'Machine Learning', 'Deep Learning', 'React', 'Angular', 'Node', 'Python',
    'Java', 'JavaScript', 'TypeScript', 'AWS', 'Azure', 'GCP', 'Docker',
    'Kubernetes', 'DevOps', 'Full Stack', 'Frontend', 'Backend', 'API',
    'Microservices', 'REST', 'GraphQL', 'SQL', 'NoSQL', 'MongoDB', 'PostgreSQL',
    'Redis', 'Kafka', 'Spring', 'Django', 'Flask', 'Express', 'Next.js',
    'Vue', 'Svelte', 'C++', 'C#', '.NET', 'PHP', 'Ruby', 'Go', 'Golang',
    'Rust', 'Swift', 'Kotlin', 'Scala', 'CI/CD', 'Jenkins', 'Git', 'GitHub',
    'GitLab', 'Terraform', 'Ansible', 'CloudFormation', 'Lambda', 'EC2',
    'S3', 'RDS', 'DynamoDB', 'Firebase', 'TensorFlow', 'PyTorch', 'Pandas',
    'NumPy', 'Scikit', 'NLP', 'Computer Vision', 'Data Science', 'AI', 'ML'
]

cursor.execute('SELECT id, title, company, location, full_text FROM job_posts ORDER BY id')
jobs = cursor.fetchall()

bad_jobs = []
for job in jobs:
    job_id, title, company, location, full_text = job
    
    # Check if location is a tech term
    if location and any(tech.lower() in location.lower() for tech in bad_location_patterns):
        bad_jobs.append({
            'id': job_id,
            'title': title[:80],
            'current_location': location,
            'full_text': full_text[:300] if full_text else ''
        })

print(f"Found {len(bad_jobs)} jobs with tech/skill terms as locations:\n")

for job in bad_jobs[:20]:  # Show first 20
    print(f"ID {job['id']}: {job['current_location']}")
    print(f"  Title: {job['title']}")
    
    # Try to extract actual location from text
    text = job['full_text']
    location_patterns = [
        r'📍\s*Locations?:\s*([^\n]+)',
        r'Location[s]?:\s*([^\n]+)',
        r'📍\s*([A-Z][a-z]+(?:\s*[|,]\s*[A-Z][a-z]+)*)',
    ]
    
    found_location = None
    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found_location = match.group(1).strip()
            # Clean up common suffixes
            found_location = re.sub(r'\s*\(.*?\)', '', found_location)
            found_location = re.sub(r'\s*–.*$', '', found_location)
            break
    
    if found_location:
        print(f"  ✓ Found in text: {found_location}")
    print()

print(f"\nTotal bad locations found: {len(bad_jobs)}")
conn.close()
