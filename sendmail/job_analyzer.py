"""
Job Analyzer Module - AI-powered job post analysis with LLM
Analyzes job posts and extracts relevant information using NLP models
"""
import re
import os
from typing import Dict, Any, Optional

# Try to import OpenAI for LLM processing, fall back to pattern matching if not available
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("[INFO] OpenAI not available. Using pattern-based extraction.")

class JobAnalyzer:
    def __init__(self):
        """Initialize the job analyzer with LLM and fallback patterns"""
        self.role_patterns = {
            'Java Developer': ['java developer', 'java engineer', 'java programmer', 'spring boot', 'j2ee', 'java backend', 'java full stack'],
            'Python Developer': ['python developer', 'python engineer', 'django', 'flask developer', 'python backend'],
            'Frontend Developer': ['frontend developer', 'frontend engineer', 'react developer', 'angular developer', 'vue developer', 'javascript developer', 'web developer'],
            'Full Stack Developer': ['full stack', 'fullstack developer', 'mern', 'mean stack', 'full-stack engineer'],
            'Backend Developer': ['backend developer', 'backend engineer', 'api developer', 'server side'],
            'Mobile Developer': ['mobile developer', 'android developer', 'ios developer', 'react native', 'flutter developer', 'mobile engineer'],
            'UI/UX Designer': ['ui designer', 'ux designer', 'product designer', 'visual designer', 'graphic designer', 'ui/ux'],
            'Data Scientist': ['data scientist', 'ml engineer', 'machine learning', 'ai engineer', 'data analyst', 'data engineer'],
            'DevOps Engineer': ['devops', 'site reliability', 'sre', 'cloud engineer', 'infrastructure', 'platform engineer'],
            'QA Engineer': ['qa engineer', 'test engineer', 'quality assurance', 'sdet', 'automation tester', 'manual tester'],
            'Product Manager': ['product manager', 'pm', 'product owner', 'product lead', 'program manager'],
            'Technical Lead': ['tech lead', 'technical lead', 'team lead', 'engineering lead', 'lead developer'],
            'Software Engineer': ['software engineer', 'sde', 'software developer'],
            'Architect': ['architect', 'solution architect', 'system architect', 'principal engineer', 'staff engineer'],
        }
        
        self.experience_patterns = {
            'Intern': ['intern', 'internship', 'trainee'],
            'Junior': ['junior', 'entry level', '0-2 years', 'fresher'],
            'Mid-Level': ['mid level', '2-5 years', '3-5 years'],
            'Senior': ['senior', '5+ years', '5-8 years', 'lead'],
            'Principal': ['principal', 'staff', 'architect', '8+ years']
        }
        
        # Check for OpenAI API key
        self.use_llm = False
        if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            self.use_llm = True
            print("[AI] ✓ OpenAI LLM enabled for job analysis")
        else:
            print("[INFO] Using advanced pattern-based extraction")
    
    def analyze_post(self, post_data):
        """
        Analyze a job post and extract/enhance information using AI techniques
        
        Args:
            post_data: Dictionary containing job post information
            
        Returns:
            Enhanced job post data with extracted title, role, and other fields
        """
        # Start with the original post data
        analyzed_post = post_data.copy()
        
        # Extract job title if not present or improve existing one
        analyzed_post['title'] = self._extract_job_title(post_data)
        
        # Extract job role/position
        analyzed_post['role'] = self._extract_job_role(post_data)
        
        # Extract experience level
        analyzed_post['experience_level'] = self._extract_experience_level(post_data)
        
        # Extract company name if not present or generic
        if 'company' not in analyzed_post or not analyzed_post['company'] or analyzed_post['company'] in ['Company Not Found', 'Company Not Specified', '']:
            analyzed_post['company'] = self._extract_company(post_data)
        
        # ALWAYS re-extract location to override generic "Remote/On-site" defaults
        # Only keep existing location if it's specific (not generic)
        existing_location = analyzed_post.get('location', '')
        
        # Check if location is invalid or generic
        invalid_location_indicators = [
            'Remote/On-site', 'Remote/On-Site', 'Location Not Specified', '',
            'profile', 'processed', 'immediately', 'hashtag', 'apply', 'appy',
            'candidates', 'interested', 'click', 'details', '💼', '📅', 
            'Experience', 'experience', 'Core Java', 'Java'
        ]
        
        should_reextract = (
            not existing_location or
            existing_location in ['Remote/On-site', 'Remote/On-Site', 'Location Not Specified', ''] or
            any(indicator.lower() in existing_location.lower() for indicator in invalid_location_indicators) or
            len(existing_location) > 50  # Location names shouldn't be too long
        )
        
        if should_reextract:
            analyzed_post['location'] = self._extract_location(post_data)
        
        # Extract skills if not present
        if 'skills' not in analyzed_post or not analyzed_post['skills']:
            analyzed_post['skills'] = self._extract_skills(post_data)
        
        # Ensure required fields have defaults
        analyzed_post.setdefault('job_type', 'Full-time')
        analyzed_post.setdefault('posted_date', '')
        analyzed_post.setdefault('url', '')
        
        return analyzed_post
    
    def _extract_job_title(self, post_data):
        """Extract and clean job title from post data using enhanced pattern analysis"""
        # Get existing title
        title = post_data.get('title', '')
        description = post_data.get('description', '')
        
        # Enhanced pattern-based extraction
        text = (title + ' ' + description)
        
        # Look for explicit "Position:" or "Role:" patterns
        position_match = re.search(r'(?:position|role|hiring|job)\s*[:|-]\s*([^\n.!?]+)', text, re.IGNORECASE)
        if position_match:
            extracted = position_match.group(1).strip()
            if len(extracted) > 5 and len(extracted) < 100:
                return self._clean_title(extracted)
        
        # Look for role patterns with context
        for role, patterns in self.role_patterns.items():
            for pattern in patterns:
                if pattern in text.lower():
                    # Extract context around the pattern
                    match = re.search(rf'([^.!?\n]*{pattern}[^.!?\n]*)', text, re.IGNORECASE)
                    if match:
                        extracted = match.group(1).strip()
                        cleaned = self._clean_title(extracted)
                        if len(cleaned) > 5:
                            return cleaned
        
        # Try existing title if present
        if title and len(title) > 10:
            return self._clean_title(title)
        
        # Extract first meaningful line from description
        lines = description.split('\n')
        for line in lines:
            line = line.strip()
            if 10 < len(line) < 100 and not line.lower().startswith(('location', 'experience', 'salary')):
                return self._clean_title(line)
        
        return "Job Position"
    
    def _extract_job_role_llm(self, post_data):
        """Extract job role using OpenAI LLM"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            title = post_data.get('title', '')
            description = post_data.get('description', '')
            text = (title + ' ' + description)[:600]
            
            roles_list = "Software Engineer, Data Scientist, DevOps Engineer, Product Manager, UI/UX Designer, QA Engineer, Technical Lead, Architect"
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"Classify the job role into ONE of these categories: {roles_list}. Return ONLY the category name, nothing else."},
                    {"role": "user", "content": f"Classify this job:\n\n{text}"}
                ],
                temperature=0.1,
                max_tokens=20
            )
            
            role = response.choices[0].message.content.strip()
            
            # Validate it's one of our known roles
            if role in self.role_patterns:
                return role
                
        except Exception as e:
            print(f"[LLM] Role extraction error: {e}")
            return None
        
        return None
    
    def _extract_job_role(self, post_data):
        """Extract job role category with better priority"""
        # Try LLM first if available
        if self.use_llm:
            llm_role = self._extract_job_role_llm(post_data)
            if llm_role:
                print(f"[LLM] Extracted role: {llm_role}")
                return llm_role
        
        title = post_data.get('title', '').lower()
        description = post_data.get('description', '').lower()
        
        # Check title first (higher priority)
        for role, patterns in self.role_patterns.items():
            for pattern in patterns:
                if pattern in title:
                    return role
        
        # Then check description
        for role, patterns in self.role_patterns.items():
            # Use word boundaries for better matching
            for pattern in patterns:
                # Check for exact word match to avoid false positives
                if re.search(r'\b' + re.escape(pattern) + r'\b', description):
                    return role
        
        # Try to detect from common keywords
        if any(word in title + ' ' + description for word in ['data', 'analytics', 'scientist', 'analyst', 'ml', 'machine learning']):
            return "Data Scientist"
        if any(word in title + ' ' + description for word in ['devops', 'sre', 'infrastructure', 'cloud', 'aws', 'azure', 'gcp']):
            return "DevOps Engineer"
        if any(word in title + ' ' + description for word in ['qa', 'test', 'quality', 'automation']):
            return "QA Engineer"
        if any(word in title + ' ' + description for word in ['product manager', 'pm ', 'product owner', 'scrum']):
            return "Product Manager"
        if any(word in title + ' ' + description for word in ['ui', 'ux', 'design', 'designer', 'figma']):
            return "UI/UX Designer"
        if any(word in title + ' ' + description for word in ['architect', 'principal', 'staff engineer']):
            return "Architect"
        if any(word in title + ' ' + description for word in ['lead', 'manager', 'head', 'director']):
            return "Technical Lead"
        
        return "Software Engineer"  # Default role
    
    def _extract_experience_level(self, post_data):
        """Extract experience level from job post"""
        text = (post_data.get('title', '') + ' ' + post_data.get('description', '')).lower()
        
        for level, patterns in self.experience_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return level
        
        return "Mid-Level"  # Default
    
    def _clean_title(self, title):
        """Clean and format job title"""
        # Remove emojis and special characters
        title = re.sub(r'[🔥🚀📍💼📅🔍📩👨‍💻💻🎯✨⭐️🌟]', '', title)
        
        # Remove hashtags
        title = re.sub(r'#\w+', '', title)
        
        # Remove extra whitespace
        title = ' '.join(title.split())
        
        # Remove common prefixes and their variations
        title = re.sub(r'^(we\'re\s+hiring|we\'re\s+on\s+the\s+hunt|hiring|urgent|immediate|job|position|opening|greeting)[:|-]?\s*', '', title, flags=re.IGNORECASE)
        
        # Remove location patterns: "Location: City, State" or "📍 Location: City"
        title = re.sub(r'(?:location|📍)\s*[:|-]?\s*[^,|\n]+(?:,\s*[^|\n]+)?', '', title, flags=re.IGNORECASE)
        
        # Remove experience patterns: "Experience: X+ years" or "Exp: X+"
        title = re.sub(r'(?:experience|exp)\s*[:|-]?\s*\d+\+?\s*(?:years?)?', '', title, flags=re.IGNORECASE)
        
        # Remove type patterns: "Type: Contract" or "💼 Type: Full-time"
        title = re.sub(r'(?:type|duration)\s*[:|-]?\s*\w+', '', title, flags=re.IGNORECASE)
        
        # Remove location in parentheses at the end: "Position (City, State)"
        title = re.sub(r'\s*\([^)]*\)\s*$', '', title)
        
        # Remove company name if it appears with "at" or "@"
        title = re.sub(r'\s+(?:at|@)\s+.*$', '', title, flags=re.IGNORECASE)
        
        # Remove trailing punctuation and special chars
        title = re.sub(r'[:|\-–—]+$', '', title)
        
        # Clean extra whitespace again
        title = ' '.join(title.split())
        
        # Capitalize properly
        title = title.strip().title()
        
        # Limit length
        if len(title) > 60:
            title = title[:57] + '...'
        
        return title if title else "Job Position"
    
    def _extract_company_llm(self, post_data):
        """Extract company name using OpenAI LLM"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            description = post_data.get('description', '')
            title = post_data.get('title', '')
            email = post_data.get('email') or post_data.get('recruiter_email', '')
            text = f"Title: {title}\nEmail: {email}\nDescription: {description[:500]}"
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Extract ONLY the company name from job posts. Return just the company name, nothing else. If unclear, return 'Company Not Specified'."},
                    {"role": "user", "content": f"Extract company name:\n\n{text}"}
                ],
                temperature=0.1,
                max_tokens=30
            )
            
            company = response.choices[0].message.content.strip()
            company = company.replace('Company:', '').replace('Name:', '').strip().strip('"\'')
            
            if company and len(company) < 100 and company != "Company Not Specified":
                return company
                
        except Exception as e:
            print(f"[LLM] Company extraction error: {e}")
            return None
        
        return None
    
    def _extract_company(self, post_data):
        """Extract company name from email domain or post data"""
        # Try LLM first if available
        if self.use_llm:
            llm_company = self._extract_company_llm(post_data)
            if llm_company and llm_company != "Company Not Specified":
                print(f"[LLM] Extracted company: {llm_company}")
                return llm_company
        
        # First try to extract from email domain
        email = post_data.get('email') or post_data.get('recruiter_email', '')
        if email and '@' in email:
            domain = email.split('@')[1].split('.')[0]
            # Clean up common patterns
            if domain not in ['gmail', 'yahoo', 'outlook', 'hotmail', 'icloud']:
                # Convert domain to proper company name
                company_name = domain.replace('-', ' ').replace('_', ' ').title()
                if len(company_name) > 2 and len(company_name) < 30:
                    return company_name
        
        # Try various fields that might contain company name
        company_fields = ['company', 'company_name', 'employer', 'organization']
        
        for field in company_fields:
            if field in post_data and post_data[field]:
                company = str(post_data[field]).strip()
                if company and company not in ['Company Not Found', 'Company Not Specified', '']:
                    # If too long, try to shorten it
                    if len(company) > 50:
                        # Take first part before common separators
                        for sep in [' - ', ' | ', ':', ',']:
                            if sep in company:
                                company = company.split(sep)[0].strip()
                                break
                    if len(company) <= 50:
                        return company
        
        # Pattern-based extraction from title
        title = post_data.get('title', '')
        description = post_data.get('description', '')
        
        # Look for "at Company" pattern
        if 'at ' in title.lower():
            parts = title.lower().split('at ')
            if len(parts) > 1:
                company = parts[-1].strip().title()
                if len(company) < 50:
                    return company
        
        return "Company Not Specified"
    
    def _extract_location_llm(self, post_data):
        """Extract location using OpenAI LLM"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            description = post_data.get('description', '')
            title = post_data.get('title', '')
            text = (title + ' ' + description)[:1000]  # Limit to 1000 chars
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a location extraction expert. Extract ONLY the city name (and state/country if mentioned) from job posts. Return ONLY the location, nothing else. If no specific city is found, return 'Location Not Specified'. Do NOT return work modes like 'Remote', 'Hybrid', 'On-site' unless no city is mentioned."},
                    {"role": "user", "content": f"Extract the job location from this text:\n\n{text}"}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            location = response.choices[0].message.content.strip()
            
            # Validate the response
            if location and len(location) < 100 and location != "Location Not Specified":
                # Clean up common LLM artifacts
                location = location.replace("Location:", "").replace("City:", "").strip()
                location = location.strip('."\'')
                return location
            
        except Exception as e:
            print(f"[LLM] Error: {e}")
            return None
        
        return None
    
    def _extract_location(self, post_data):
        """Extract location from post data with LLM and pattern matching"""
        
        # Try LLM extraction first if available
        if self.use_llm:
            llm_location = self._extract_location_llm(post_data)
            if llm_location and llm_location != "Location Not Specified":
                print(f"[LLM] Extracted location: {llm_location}")
                return llm_location
        
        # Try various fields that might contain location
        location_fields = ['location', 'city', 'address', 'workplace']
        
        for field in location_fields:
            if field in post_data and post_data[field]:
                location = str(post_data[field]).strip()
                # Skip generic/invalid locations
                if location and location not in ['Location Not Specified', 'Remote/On-site', 'Remote/On-Site']:
                    cleaned = self._clean_location(location)
                    if cleaned and len(cleaned) > 2:
                        print(f"[LOC] Using cleaned field location: {cleaned}")
                        return cleaned
                else:
                    print(f"[LOC] Skipping generic location: {location}")
        
        # Enhanced pattern-based extraction
        description = post_data.get('description', '')
        title = post_data.get('title', '')
        text = title + ' ' + description
        
        print(f"[LOC] Extracting from text: {text[:100]}...")
        
        # Look for explicit location patterns FIRST (highest priority)
        # Pattern 1: "Location: City, State" or "📍 Location: City" or "Location : City"
        # More restrictive pattern - capture only up to 60 chars or until common separators
        location_match = re.search(r'(?:📍|location)\s*[:|-]?\s*([A-Za-z][A-Za-z\s,()-]{1,60}?)(?:\s*💼|\s*📅|\s*🔍|\s*experience|\s*exp\s*:|\s*type\s*:|\s*duration|\s*notice|\||\n|\r|$)', text, re.IGNORECASE)
        if location_match:
            location = location_match.group(1).strip()
            print(f"[LOC] Found pattern match: {location}")
            cleaned = self._clean_location(location)
            if cleaned and len(cleaned) > 2 and cleaned not in ['Remote', 'On-Site', 'Onsite', 'Hybrid']:
                print(f"[LOC] Returning: {cleaned}")
                return cleaned
        
        # Pattern 2: "in City" or "at City" patterns
        in_at_pattern = r'(?:in|at)\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z]{2,})?)'
        in_at_match = re.search(in_at_pattern, text)
        if in_at_match:
            location = in_at_match.group(1).strip()
            cleaned = self._clean_location(location)
            if cleaned and 3 < len(cleaned) < 40:
                return cleaned
        
        # Pattern 3: US Cities with States (comprehensive list)
        us_cities = r'\b(New York|San Francisco|Austin|Seattle|Boston|Chicago|Los Angeles|Denver|Atlanta|Dallas|Charlotte|Houston|Phoenix|Philadelphia|San Antonio|San Diego|San Jose|Portland|Las Vegas|Miami|Tampa|Orlando|Minneapolis|Detroit|Nashville|Baltimore|Cleveland|Pittsburgh|St\.\s*Louis|Cincinnati|Kansas City|Indianapolis|Columbus|Milwaukee|Sacramento|Raleigh|Memphis|Richmond|Louisville|Salt Lake City|Jacksonville|Oklahoma City|Tucson|Albuquerque|Fresno|Mesa|Virginia Beach|Arlington|Omaha|Colorado Springs)\s*,?\s*(NY|CA|TX|WA|MA|IL|CO|GA|NC|AZ|PA|OR|NV|FL|MN|MI|TN|MD|OH|MO|IN|WI|UT|OK|NM|VA|NE)?\b'
        
        # Pattern 4: Indian Cities with States
        indian_cities = r'\b(Bangalore|Bengaluru|Hyderabad|Mumbai|Pune|Delhi|New Delhi|Gurugram|Gurgaon|Noida|Chennai|Ahmedabad|Kolkata|Jaipur|Surat|Lucknow|Kanpur|Nagpur|Indore|Thane|Bhopal|Visakhapatnam|Pimpri-Chinchwad|Patna|Vadodara|Ghaziabad|Ludhiana|Agra|Nashik|Faridabad|Meerut|Rajkot|Kalyan-Dombivali|Vasai-Virar|Varanasi|Srinagar|Aurangabad|Dhanbad|Amritsar|Navi Mumbai|Allahabad|Ranchi|Howrah|Coimbatore|Jabalpur|Gwalior|Vijayawada|Jodhpur|Madurai|Raipur|Kota|Chandigarh)\s*,?\s*(Karnataka|Telangana|Maharashtra|Delhi|NCR|Haryana|Tamil Nadu|Gujarat|West Bengal|Rajasthan|UP|Uttar Pradesh|Madhya Pradesh|Punjab|Andhra Pradesh)?\b'
        
        # Pattern 5: International Cities
        international_cities = r'\b(London|Dubai|Singapore|Toronto|Vancouver|Montreal|Sydney|Melbourne|Berlin|Paris|Amsterdam|Madrid|Barcelona|Munich|Frankfurt|Zurich|Stockholm|Copenhagen|Oslo|Helsinki|Dublin|Brussels|Vienna|Prague|Warsaw|Riyadh|Jeddah|Abu Dhabi|Doha|Kuwait City|Muscat|Manama|Cairo|Johannesburg|Cape Town|Nairobi|Lagos|Accra|Hong Kong|Tokyo|Seoul|Bangkok|Manila|Jakarta|Kuala Lumpur|Ho Chi Minh City|Hanoi|Beijing|Shanghai|Shenzhen|Guangzhou)\b'
        
        # Try to find cities in order of specificity
        for pattern in [us_cities, indian_cities, international_cities]:
            city_match = re.search(pattern, text, re.IGNORECASE)
            if city_match:
                location = city_match.group(0).strip()
                # Clean and format
                parts = [p.strip() for p in location.split(',') if p.strip()]
                if len(parts) > 1:
                    return f"{parts[0].title()}, {parts[1].upper()}"
                return location.title()
        
        # Check for work mode keywords ONLY if no city was found
        text_lower = text.lower()
        
        # Try one more time to extract city before falling back to work mode
        # Look for patterns like "Location: Remote" vs "Location: Bangalore"
        city_after_location = re.search(r'location\s*[:|-]?\s*([a-z]+(?:\s+[a-z]+)?)', text_lower)
        if city_after_location:
            potential_city = city_after_location.group(1).strip()
            # Check if it's a work mode or an actual city
            if potential_city not in ['remote', 'hybrid', 'onsite', 'on-site', 'wfh', 'work from home']:
                return potential_city.title()
        
        # Only return work modes if absolutely no city location found
        if 'remote' in text_lower:
            if 'hybrid' in text_lower:
                return "Hybrid/Remote"
            # Check if there's a city mentioned with remote
            simple_city = re.search(r'remote.*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', text)
            if simple_city:
                return f"{simple_city.group(1)} (Remote)"
            return "Remote"
        elif 'hybrid' in text_lower:
            return "Hybrid"
        elif 'on-site' in text_lower or 'onsite' in text_lower:
            # Try to find the city for on-site
            simple_city = re.search(r'(?:on-?site|onsite).*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', text)
            if simple_city:
                return f"{simple_city.group(1)} (On-site)"
            return "On-site"
        elif 'work from home' in text_lower or 'wfh' in text_lower:
            return "Remote"
        
        return "Location Not Specified"
    
    def _clean_location(self, location):
        """Clean location string from mixed data"""
        # Remove emojis
        location = re.sub(r'[🔥🚀📍💼📅🔍📩👨‍💻💻🎯✨⭐️🌟]', '', location)
        
        # Remove "Location:" prefix if present
        location = re.sub(r'^(?:location|📍)\s*[:|-]?\s*', '', location, flags=re.IGNORECASE)
        
        # Filter out completely invalid location text
        invalid_patterns = [
            r'your\s+profile',
            r'will\s+be\s+processed',
            r'immediately',
            r'hashtag',
            r'apply',
            r'appy',
            r'share\s+only',
            r'candidates',
            r'interested',
            r'click\s+here',
            r'details',
            r'description',
            r'requirements',
            r'experience\s*:',
            r'duration\s*:',
            r'core\s*:',
            r'java\s*:',
            r'type\s*:'
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, location, re.IGNORECASE):
                return None
        
        # Extract just the city/state part, stopping at experience, type, or other metadata
        location = re.sub(r'(?:experience|exp|notice|type|duration|mandatory|if interested|please|💼|📅|\(onsite\)|\(on-site\)|\(remote\)).*$', '', location, flags=re.IGNORECASE)
        
        # Remove parenthetical work modes but keep the city
        location = re.sub(r'\s*\(\s*(?:onsite|on-site|remote|hybrid)\s*\)', '', location, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        location = ' '.join(location.split())
        
        # Remove trailing punctuation and special chars
        location = location.strip(' ,;:|-–—.!')
        
        # Handle "City, State" format properly
        if ',' in location:
            parts = [p.strip() for p in location.split(',')]
            if len(parts) == 2 and 2 <= len(parts[0]) <= 30 and 2 <= len(parts[1]) <= 20:
                return f"{parts[0].title()}, {parts[1].upper()}"
        
        # Validate it's a reasonable location (not too long, has some letters)
        if location and 2 < len(location) < 50 and any(c.isalpha() for c in location):
            # Don't title case if it's already in proper format
            if location[0].isupper():
                return location
            return location.title()
        
        return None
    
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