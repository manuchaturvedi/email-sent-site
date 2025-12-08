#!/usr/bin/env python3
import sqlite3
import re

conn = sqlite3.connect('/app/justmailit.db')
cursor = conn.cursor()

# Jobs that were skipped - need smarter extraction
problem_ids = [10, 12, 18, 32, 34, 57, 68, 72, 79, 83, 93, 127, 172, 193, 195, 236, 253, 259, 260, 
               294, 305, 324, 340, 394, 442, 443, 460, 472, 481, 486, 488, 496, 517, 518, 537, 538, 
               550, 556, 559, 592, 596, 605, 616, 623, 629, 654, 657, 664, 671, 680, 713, 744, 750, 
               754, 769, 779, 781, 786, 788, 790]

def smart_extract_location(text, title):
    """More aggressive location extraction"""
    if not text:
        return None
    
    combined = title + "\n" + text
    
    # Try multiple patterns
    patterns = [
        # Explicit location markers
        (r'📍\s*(?:Location|Locations?)[:\s]*([^\n\r]+?)(?:\n|$|•|🧑)', True),
        (r'(?:Location|Locations?)[:\s]+([^\n\r]+?)(?:\n|$|•)', True),
        (r'(?:based in|located in|office in|work (?:from|in))\s+([A-Z][a-z]+(?:,\s*[A-Z]{2})?)', False),
        # Work mode patterns
        (r'(Remote|Hybrid|WFO|Work From Home)', False),
        # City patterns
        (r'\b(Bangalore|Bengaluru|Mumbai|Delhi|Hyderabad|Chennai|Pune|Kolkata|Ahmedabad|Gurgaon|Gurugram|Noida|Kochi|Chandigarh|Jaipur|Indore|Mohali|Surat|Vadodara)\b', False),
        # International cities
        (r'\b(New York|San Francisco|Los Angeles|Chicago|Austin|Dallas|London|Singapore|Dubai|Amsterdam|Berlin|Sydney|Toronto|Seattle|Boston)\b', False),
    ]
    
    for pattern, is_primary in patterns:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            
            # Clean up
            location = re.sub(r'\s*\(.*?\)', '', location)
            location = re.sub(r'\s*[–-].*$', '', location)
            location = re.sub(r'\s*\|.*(?:Job Type|Work Mode|Experience).*$', '', location, flags=re.IGNORECASE)
            location = location.strip(' |,.:;')
            
            # If it's a valid location string
            if 2 < len(location) < 150:
                # Skip if it's just a tech term
                tech_keywords = ['Java', 'Python', 'React', 'Node', 'Angular', 'Docker', 'DevOps', 'AWS', 'Azure']
                if location in tech_keywords:
                    continue
                    
                return location
    
    # Fallback: look for "WFO" or "Office" mentions with city nearby
    match = re.search(r'(?:WFO|Office|based)\s*[:\s]*([A-Z][a-z]+)', combined, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None

updated_count = 0

for job_id in problem_ids:
    cursor.execute('SELECT title, location, full_text FROM job_posts WHERE id = ?', (job_id,))
    result = cursor.fetchone()
    if not result:
        continue
    
    title, current_location, full_text = result
    new_location = smart_extract_location(full_text, title)
    
    if new_location and new_location != current_location:
        cursor.execute("UPDATE job_posts SET location = ? WHERE id = ?", (new_location, job_id))
        updated_count += 1
        print(f"✓ ID {job_id}: {current_location} → {new_location}")
    else:
        # Keep the current location if we can't find better
        print(f"⚠ ID {job_id}: Keeping '{current_location}'")

conn.commit()
print(f"\n{'='*80}")
print(f"✅ Updated {updated_count} more jobs")
print(f"{'='*80}")

conn.close()
