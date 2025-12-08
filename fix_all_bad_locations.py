#!/usr/bin/env python3
import sqlite3
import re

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()

# Tech/skill terms that shouldn't be locations
bad_location_terms = [
    'Machine Learning', 'Deep Learning', 'React', 'Angular', 'Node', 'Python',
    'Java', 'JavaScript', 'TypeScript', 'AWS', 'Azure', 'GCP', 'Docker',
    'Kubernetes', 'DevOps', 'Full Stack', 'Frontend', 'Backend', 'API',
    'Microservices', 'REST', 'GraphQL', 'SQL', 'NoSQL', 'MongoDB', 'PostgreSQL',
    'Redis', 'Kafka', 'Spring', 'Django', 'Flask', 'Express', 'Next.js',
    'Vue', 'Svelte', 'C++', 'C#', '.NET', 'PHP', 'Ruby', 'Go', 'Golang',
    'Rust', 'Swift', 'Kotlin', 'Scala', 'CI/CD', 'Jenkins', 'Git', 'GitHub',
    'GitLab', 'Terraform', 'Ansible', 'CloudFormation', 'Lambda', 'EC2',
    'S3', 'RDS', 'DynamoDB', 'Firebase', 'TensorFlow', 'PyTorch', 'Pandas',
    'NumPy', 'Scikit', 'NLP', 'Computer Vision', 'Data Science', 'AI', 'ML',
    'CSS', 'HTML', 'SASS', 'LESS', 'Webpack', 'Babel', 'ESLint', 'Prettier'
]

# Known cities (Indian and international)
known_cities = [
    'Bangalore', 'Bengaluru', 'Mumbai', 'Delhi', 'Hyderabad', 'Chennai', 
    'Pune', 'Kolkata', 'Ahmedabad', 'Gurgaon', 'Gurugram', 'Noida', 
    'Kochi', 'Trivandrum', 'Chandigarh', 'Jaipur', 'Indore', 'Bhopal',
    'Vadodara', 'Surat', 'Nagpur', 'Visakhapatnam', 'Coimbatore',
    'New York', 'San Francisco', 'London', 'Singapore', 'Dubai',
    'Amsterdam', 'Berlin', 'Paris', 'Tokyo', 'Sydney', 'Toronto'
]

def extract_location_from_text(text):
    """Extract location from job post text"""
    if not text:
        return None
    
    # Pattern 1: 📍 Location: or 📍 Locations: (most explicit)
    patterns = [
        r'📍\s*Locations?:\s*([^\n\r•]+?)(?:\n|$|•)',
        r'Location[s]?:\s*([^\n\r•]+?)(?:\n|$|•)',
        r'📍\s*([A-Z][a-z]+(?:\s*[|,/]\s*[A-Z][a-z]+)*)',
        r'(?:based in|located in|office in)\s+([A-Z][a-z]+(?:\s*[|,]\s*[A-Z][a-z]+)*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            
            # Clean up
            location = re.sub(r'\s*\(.*?\)', '', location)  # Remove parentheses
            location = re.sub(r'\s*–.*$', '', location)      # Remove dashes and after
            location = re.sub(r'\s*\|.*Job Type.*$', '', location, flags=re.IGNORECASE)
            location = re.sub(r'\s*\|.*Work Mode.*$', '', location, flags=re.IGNORECASE)
            location = location.strip(' |,')
            
            # Validate: must contain at least one known city or end with state/country
            if any(city.lower() in location.lower() for city in known_cities):
                return location
            if re.search(r'(Remote|Hybrid|WFO|Onsite)', location, re.IGNORECASE):
                return location
            if len(location) > 3 and len(location) < 100:
                return location
    
    return None

# Get all jobs with bad locations
cursor.execute('SELECT id, title, location, full_text FROM job_posts ORDER BY id')
jobs = cursor.fetchall()

updated_count = 0
skipped_count = 0

for job in jobs:
    job_id, title, current_location, full_text = job
    
    # Check if current location is bad
    is_bad = False
    if current_location:
        for tech_term in bad_location_terms:
            if tech_term.lower() == current_location.lower() or \
               (tech_term.lower() in current_location.lower() and 
                not any(city.lower() in current_location.lower() for city in known_cities)):
                is_bad = True
                break
    
    if is_bad:
        # Try to extract proper location
        new_location = extract_location_from_text(full_text)
        
        if new_location and new_location != current_location:
            cursor.execute(
                "UPDATE job_posts SET location = ? WHERE id = ?",
                (new_location, job_id)
            )
            updated_count += 1
            print(f"✓ ID {job_id}: {current_location} → {new_location}")
        else:
            skipped_count += 1
            print(f"⚠ ID {job_id}: Could not extract location (current: {current_location})")

conn.commit()
print(f"\n{'='*80}")
print(f"✅ Updated: {updated_count} jobs")
print(f"⚠ Skipped: {skipped_count} jobs (manual review needed)")
print(f"{'='*80}")

conn.close()
