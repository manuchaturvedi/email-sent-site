"""
Job Analyzer Module - Simplified version for cloud deployment
Analyzes job posts and extracts relevant information
"""

class JobAnalyzer:
    def __init__(self):
        """Initialize the job analyzer"""
        pass
    
    def analyze_post(self, post_data):
        """
        Analyze a job post and extract/enhance information
        
        Args:
            post_data: Dictionary containing job post information
            
        Returns:
            Enhanced job post data with additional fields
        """
        # Start with the original post data
        analyzed_post = post_data.copy()
        
        # Extract company name if not present
        if 'company' not in analyzed_post or not analyzed_post['company']:
            analyzed_post['company'] = self._extract_company(post_data)
        
        # Extract location if not present
        if 'location' not in analyzed_post or not analyzed_post['location']:
            analyzed_post['location'] = self._extract_location(post_data)
        
        # Extract skills if not present
        if 'skills' not in analyzed_post or not analyzed_post['skills']:
            analyzed_post['skills'] = self._extract_skills(post_data)
        
        # Ensure required fields have defaults
        analyzed_post.setdefault('job_type', 'Full-time')
        analyzed_post.setdefault('posted_date', '')
        analyzed_post.setdefault('url', '')
        
        return analyzed_post
    
    def _extract_company(self, post_data):
        """Extract company name from post data"""
        # Try various fields that might contain company name
        company_fields = ['company', 'company_name', 'employer', 'organization']
        
        for field in company_fields:
            if field in post_data and post_data[field]:
                return str(post_data[field]).strip()
        
        # Try to extract from title or description
        title = post_data.get('title', '')
        description = post_data.get('description', '')
        
        # Look for common patterns in title
        if 'at ' in title.lower():
            parts = title.lower().split('at ')
            if len(parts) > 1:
                return parts[-1].strip().title()
        
        return "Company Not Specified"
    
    def _extract_location(self, post_data):
        """Extract location from post data"""
        # Try various fields that might contain location
        location_fields = ['location', 'city', 'address', 'workplace']
        
        for field in location_fields:
            if field in post_data and post_data[field]:
                return str(post_data[field]).strip()
        
        # Common location keywords in descriptions
        description = post_data.get('description', '').lower()
        title = post_data.get('title', '').lower()
        
        if 'remote' in description or 'remote' in title:
            return "Remote"
        elif 'hybrid' in description or 'hybrid' in title:
            return "Hybrid"
        elif 'on-site' in description or 'onsite' in description:
            return "On-site"
        
        return "Location Not Specified"
    
    def _extract_skills(self, post_data):
        """Extract skills from post data"""
        # Try to get skills from existing field
        if 'skills' in post_data and post_data['skills']:
            return post_data['skills']
        
        # Common tech skills to look for
        common_skills = [
            'python', 'javascript', 'java', 'react', 'nodejs', 'aws', 
            'docker', 'kubernetes', 'devops', 'sql', 'git', 'linux',
            'flask', 'django', 'vue', 'angular', 'mongodb', 'postgresql'
        ]
        
        description = post_data.get('description', '').lower()
        title = post_data.get('title', '').lower()
        
        found_skills = []
        for skill in common_skills:
            if skill in description or skill in title:
                found_skills.append(skill.title())
        
        return found_skills if found_skills else ["General Skills"]
    
    def get_job_categories(self):
        """Get list of job categories"""
        return [
            "Software Development",
            "DevOps/Cloud",
            "Data Science", 
            "Product Management",
            "Design",
            "Marketing",
            "Sales",
            "Other"
        ]
    
    def categorize_job(self, post_data):
        """Categorize job based on title and description"""
        title = post_data.get('title', '').lower()
        description = post_data.get('description', '').lower()
        
        # Define category keywords
        categories = {
            "Software Development": ['developer', 'engineer', 'programmer', 'software', 'frontend', 'backend', 'fullstack'],
            "DevOps/Cloud": ['devops', 'cloud', 'aws', 'docker', 'kubernetes', 'infrastructure', 'sre'],
            "Data Science": ['data scientist', 'analyst', 'machine learning', 'ai', 'ml', 'analytics'],
            "Product Management": ['product manager', 'pm', 'product owner', 'scrum master'],
            "Design": ['designer', 'ui', 'ux', 'graphic', 'visual'],
            "Marketing": ['marketing', 'content', 'seo', 'social media', 'digital marketing'],
            "Sales": ['sales', 'account manager', 'business development', 'bd']
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in title or keyword in description:
                    return category
        
        return "Other"