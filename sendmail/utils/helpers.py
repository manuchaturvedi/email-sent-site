"""
Helper utility functions for the application
These are pure utility functions with no side effects or external dependencies
"""

def extract_company_from_email(email):
    """Extract and format company name from email address"""
    try:
        # Get domain part
        domain = email.split('@')[1]
        
        # Remove common TLDs
        domain = domain.replace('.com', '').replace('.co.uk', '').replace('.org', '')
        domain = domain.replace('.net', '').replace('.io', '').replace('.ai', '')
        domain = domain.replace('.edu', '').replace('.gov', '').replace('.in', '')
        
        # Handle subdomains (e.g., hr.company.com -> company)
        parts = domain.split('.')
        if len(parts) > 1:
            # Take the last part before TLD (usually company name)
            domain = parts[-1]
        
        # Clean and format
        domain = domain.strip().replace('-', ' ').replace('_', ' ')
        
        # Capitalize each word
        company_name = ' '.join(word.capitalize() for word in domain.split())
        
        return company_name if company_name else "Unknown Company"
    except:
        return "Unknown Company"


def parse_skills(skills_string):
    """Parse skills from string - handles both commas and spaces as separators"""
    if not skills_string:
        return []
    
    import re
    # Replace commas with spaces, then split by spaces and filter empty strings
    # This handles: "python,java", "python, java", "python java", "python  java"
    skills_string = skills_string.replace(',', ' ')
    skill_list = [s.strip() for s in skills_string.split() if s.strip()]
    return skill_list
