import re
from typing import Dict, List, Optional

# geonamescache provides a reasonably comprehensive city list we can use
try:
    import geonamescache
except Exception:
    geonamescache = None

# Mapping for email domains to company names
COMPANY_DOMAIN_MAP = {
    # IT Services & Consulting
    'hcltech': 'HCLTech',
    'ibm': 'IBM',
    'microsoft': 'Microsoft',
    'google': 'Google',
    'amazon': 'Amazon',
    'aws': 'Amazon Web Services',
    'tcs': 'TCS',
    'wipro': 'Wipro',
    'accenture': 'Accenture',
    'infosys': 'Infosys',
    'capgemini': 'Capgemini',
    'cognizant': 'Cognizant',
    'techmahindra': 'Tech Mahindra',
    'mindtree': 'Mindtree',
    'deloitte': 'Deloitte',
    'pwc': 'PwC',
    'kpmg': 'KPMG',
    'ey': 'EY',
    
    # Product Companies
    'oracle': 'Oracle',
    'salesforce': 'Salesforce',
    'vmware': 'VMware',
    'adobe': 'Adobe',
    'intel': 'Intel',
    'cisco': 'Cisco',
    'dell': 'Dell',
    'hp': 'HP',
    'sap': 'SAP',
    
    # Indian Companies
    'zomato': 'Zomato',
    'swiggy': 'Swiggy',
    'flipkart': 'Flipkart',
    'myntra': 'Myntra',
    'paytm': 'Paytm',
    'phonepe': 'PhonePe',
    'razorpay': 'Razorpay',
    'byju': "BYJU'S",
    'byjus': "BYJU'S",
    
    # Variations
    'tataelxsi': 'Tata Elxsi',
    'tataconsultancyservices': 'TCS',
    'technomahindra': 'Tech Mahindra',
    'ltimindtree': 'LTIMindtree',
    'larsentoubro': 'L&T',
    'lnt': 'L&T'
}

class JobAnalyzer:
    def __init__(self):
        # Helper function for cleaning location text
        def clean_location(text):
            if not text:
                return None
            # Remove common noise and normalize spacing
            text = re.sub(r'\s+', ' ', text)
            # Trim off common trailing phrases that are not part of the place
            # e.g., "Bangalore Notice: Upto 15 Days..." -> keep "Bangalore"
            text = re.split(r'(?i)\b(?:notice|if interested|please|mandatory|contact|email|apply)\b', text)[0]
            text = text.strip('.,;')
            # Remove common suffixes that don't add value
            text = re.sub(r'\s*(?:only|option|available)\s*$', '', text, flags=re.IGNORECASE)
            return text.strip()

        # Words that should never be treated as a location (roles, verbs, generic words)
        self._location_token_blacklist = set([
            'mentor', 'mentorand', 'mentor,', 'mentor.', 'mentor-', 'mentor–',
            'team', 'teams', 'apply', 'applynow', 'apply now', 'contact', 'call',
            'whatsapp', 'note', 'notice', 'experience', 'hiring', 'hiringnow',
            'jobs', 'job', 'opportunity', 'opportunities', 'career', 'careers',
            'enterprise', 'of', 'and', 'with'
        ])

        # Common location patterns
        self.location_patterns = [
            r"location[:\s-]+([^\.!\n]+)",  # Match until end of line or punctuation
            r"📍\s*(?:location)?[:\s-]*([^\.!\n]+)",  # Emoji location marker
            r"(?:in|at|from)\s+([A-Za-z0-9\s,\-]+(?:(?:,\s*)?(?:India|USA|UK|Canada))?)",
            r"(?:remote|work from home|wfh|on-site|hybrid)",
            r"(?:on-site|hybrid|remote)\s*(?:in|at)?\s*\(?([^\.!\n\)]+)\)?",
            r"([A-Za-z\s]+)(?:\s*,\s*(?:India|USA|UK|Canada|UP|Delhi NCR))",
            r"(?:noida|gurgaon|gurugram|bengaluru|bangalore|mumbai|delhi|pune)[,\s-]*(?:sector|phase)?[,\s-]*(?:\d+)?",
            r"(?:sector|phase)[- ](?:\d+[a-z]?)\s*[,]?\s*([^\.!\n,]+)",  # For sector/phase specific locations
        ]

        # Make clean_location available to other methods
        self.clean_location = clean_location

        # Define skill categories and keywords
        self.skills_dict = {
            'programming': [
                'python', 'java', 'javascript', 'typescript', 'c\+\+', 'ruby', 'php', 'scala',
                'golang', 'rust', 'swift', 'kotlin', 'dart', 'r programming'
            ],
            'web_technologies': [
                'html', 'css', 'react', 'angular', 'vue', 'node\.?js', 'django', 'flask',
                'spring boot', 'laravel', 'express\.?js', 'next\.?js', 'nuxt', 'svelte'
            ],
            'cloud': [
                'aws', 'azure', 'gcp', 'google cloud', 'cloud computing', 'serverless',
                'lambda', 'ec2', 's3', 'rds', 'dynamodb', 'kubernetes', 'docker', 'terraform',
                'cloudformation', 'ansible', 'jenkins', 'gitlab ci', 'github actions'
            ],
            'databases': [
                'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
                'cassandra', 'oracle', 'graphql', 'dynamodb', 'mariadb'
            ],
            'ai_ml': [
                'machine learning', 'artificial intelligence', 'deep learning', 'nlp',
                'computer vision', 'tensorflow', 'pytorch', 'scikit-learn', 'pandas',
                'numpy', 'opencv', 'keras'
            ],
            'tools': [
                'git', 'github', 'gitlab', 'bitbucket', 'jira', 'confluence', 'slack',
                'postman', 'swagger', 'linux', 'bash', 'powershell', 'agile', 'scrum'
            ]
        }

        # Build a city name set using geonamescache (if available).
        # We store lowercase names and a sorted list (longer names first) to prefer multi-word matches.
        try:
            if geonamescache:
                gc = geonamescache.GeonamesCache()
                cities = gc.get_cities()
                city_names = set()
                for _, info in cities.items():
                    name = info.get('name')
                    if name:
                        city_names.add(name.lower())
                    # include ASCII/alternate where present
                    ascii_name = info.get('ascii')
                    if ascii_name:
                        city_names.add(ascii_name.lower())
                # keep sorted list for longest-first matching
                self.city_names = city_names
                self.city_list_sorted = sorted(list(city_names), key=lambda s: len(s), reverse=True)
            else:
                self.city_names = set()
                self.city_list_sorted = []
        except Exception:
            self.city_names = set()
            self.city_list_sorted = []

    def extract_location(self, text: str) -> str:
        """Extract location information from text."""
        if not text:
            return "Location not specified"

        # Clean and normalize text first
        text = ' '.join(text.split())  # Normalize whitespace

        # Check for explicit "Location:" patterns first
        location_headers = [
            r'Location:\s*([^\.!\n]+)',
            r'📍\s*(?:Location:)?\s*([^\.!\n]+)',
        ]

        # Helper for consistent mode-location formatting
        def format_mode_location(mode: str, location: str) -> str:
            if not location:
                return mode.title()
            return f"{mode.title()} - {location.title()}"

        # Try to extract from location headers first
        for pattern in location_headers:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and match.group(1):
                location = self.clean_location(match.group(1))
                if not location:
                    continue

                # Reject obvious role/verb tokens that sometimes appear near Location lines
                low_loc = location.lower().strip()
                first_token = low_loc.split()[0] if low_loc else ''
                if first_token in self._location_token_blacklist or low_loc in self._location_token_blacklist:
                    # skip this match and continue searching
                    continue

                # Check if location contains mode information
                mode_match = re.search(r'(on-site|remote|hybrid|work from home)[^\w]*(.+)', location, re.IGNORECASE)
                if mode_match:
                    mode = mode_match.group(1)
                    loc = self.clean_location(mode_match.group(2))
                    if loc:
                        # ensure loc is not a role token
                        if loc.lower().split()[0] in self._location_token_blacklist:
                            continue
                        return format_mode_location(mode, loc)
                    return mode.title()
                return location.title()

        # Check for mode-specific patterns
        mode_patterns = {
            'On-Site': r'on-site\s*(?:(?:in|at)\s+)?\(?([^\.!\n\)]+)\)?',
            'Remote': r'remote\s*(?:(?:in|at)\s+)?\(?([^\.!\n\)]+)\)?',
            'Hybrid': r'hybrid\s*(?:(?:in|at)\s+)?\(?([^\.!\n\)]+)\)?',
            'Work From Home': r'work\s*from\s*home\s*(?:(?:in|at)\s+)?\(?([^\.!\n\)]+)\)?'
        }

        for mode, pattern in mode_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match and match.group(1):
                location = self.clean_location(match.group(1))
                return format_mode_location(mode, location)

        # Look for cities with sectors/phases
        city_patterns = [
            r'(?:noida|gurgaon|gurugram|bengaluru|bangalore|mumbai|delhi|pune)'
            r'[,\s-]*(?:sector|phase)?[,\s-]*(?:\d+[a-z]?)?',
            r'(?:sector|phase)[- ](?:\d+[a-z]?)\s*[,]?\s*([^\.!\n,]+)',
            r'([A-Za-z\s]+)(?:\s*,\s*(?:India|USA|UK|Canada|UP|Delhi NCR))',
        ]

        for pattern in city_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(0) if not match.groups() else match.group(1)
                location = self.clean_location(location)
                if location:
                    low_loc = location.lower().strip()
                    first_token = low_loc.split()[0] if low_loc else ''
                    if first_token in self._location_token_blacklist or low_loc in self._location_token_blacklist:
                        continue
                    return location.title()

        # Look for any location with hyphen/dash/parentheses combinations
        separators = [
            r'([^–\n]+)\s*[–-]\s*([^\.!\n]+)',  # dash separator
            r'([^(\n]+)\s*\(\s*([^\.!\n\)]+)\)',  # parentheses
        ]
        
        for pattern in separators:
            match = re.search(pattern, text)
            if match:
                part1 = self.clean_location(match.group(1))
                part2 = self.clean_location(match.group(2))
                if not part1 or not part2:
                    continue

                # If either part is a known city, prefer returning the city
                city1 = self.extract_city_from_text(part1)
                city2 = self.extract_city_from_text(part2)
                if city1 and not city2:
                    return city1
                if city2 and not city1:
                    return city2

                # If one part clearly indicates mode, return Mode - Location
                if re.search(r'on-site|onsite|on site|remote|work from home|wfh|hybrid', part1, re.IGNORECASE) and city2:
                    return f"{part1.title()} - {city2}"
                if re.search(r'on-site|onsite|on site|remote|work from home|wfh|hybrid', part2, re.IGNORECASE) and city1:
                    return f"{part2.title()} - {city1}"

                # If neither side looks like a city or mode, avoid guessing a combined location
                # This prevents headlines like "Opt Talent - Let’s Connect" from becoming a location
                continue

        # Try general location patterns as last resort
        general_patterns = [
            r'(?:in|at|from)\s+([A-Za-z0-9\s,\-]+(?:(?:,\s*)?(?:India|USA|UK|Canada))?)',
            r'([A-Za-z\s]+)(?:\s*,\s*(?:India|USA|UK|Canada|UP|Delhi NCR))',
        ]

        for pattern in general_patterns:
            match = re.search(pattern, text)
            if match and match.group(1):
                location = self.clean_location(match.group(1))
                if location:
                    low_loc = location.lower().strip()
                    first_token = low_loc.split()[0] if low_loc else ''
                    if first_token in self._location_token_blacklist or low_loc in self._location_token_blacklist:
                        continue
                    return location.title()

        return "Location not specified"

    def extract_city_from_text(self, text: str) -> Optional[str]:
        """Try to find a city name present in text using the prebuilt city list.

        Returns the matched city (title-cased) or None.
        """
        if not text or not self.city_list_sorted:
            return None

        # Normalize whitespace
        normalized = ' '.join(text.split())

        # Try longest-first matching to prefer multi-word city names.
        # Only accept a city match if it appears in a reasonable 'location' context
        # (near words like 'location', '📍', 'in', 'at', commas, or parentheses).
        context_indicators = ['location', 'loc', '📍', 'in ', ' at ', ' near ', ',', '(', ')', 'on-site', 'onsite', 'hybrid']
        for city in self.city_list_sorted:
            try:
                for m in re.finditer(r"\b" + re.escape(city) + r"\b", normalized, re.IGNORECASE):
                    start = m.start()
                    # Look for indicators in a small window around the match
                    pre = normalized[max(0, start - 40):start].lower()
                    post = normalized[start:start + 40].lower()
                    found_context = any(ind in pre or ind in post for ind in context_indicators)
                    if found_context:
                        return city.title()
                    # otherwise skip this match as it's likely a verb/role mention (e.g., 'mentor')
            except re.error:
                continue

        return None

    def is_probable_link(self, text: str) -> bool:
        """Return True if text looks like a URL or link/keyword pointing to a webpage."""
        if not text or not isinstance(text, str):
            return False
        return bool(re.search(r'https?://|www\.|linkedin\.com|mailto:|bit\.ly/|tinyurl\.|\.com/|\.in/|http\b', text, re.IGNORECASE))

    def _normalize_location_str(self, loc: Optional[str]) -> str:
        """Normalize location strings to a concise value.

        Rules:
        - If a known city is present, return the city (title-cased).
        - If contains both remote and on-site indicators -> 'Remote/On-site'
        - If contains only remote -> 'Remote'
        - If contains only on-site -> 'On-site'
        - If contains hybrid -> 'Hybrid'
        - Otherwise return 'Location not specified'
        """
        if not loc or not isinstance(loc, str):
            return "Location not specified"

        s = loc.strip()
        if not s:
            return "Location not specified"

        # If loc looks like a URL/link, do not treat it as a location
        if self.is_probable_link(s):
            return "Location not specified"

        # Try direct city match first
        city = self.extract_city_from_text(s)
        if city:
            return city

        low = s.lower()
        remote = bool(re.search(r'\bremote\b|work from home|wfh', low))
        on_site = bool(re.search(r'\bon-?site\b|\bon site\b|onsite\b', low))
        hybrid = bool(re.search(r'\bhybrid\b', low))

        if remote and on_site:
            return 'Remote/On-site'
        if remote:
            return 'Remote'
        if on_site:
            return 'On-site'
        if hybrid:
            return 'Hybrid'

        # If it looks like a simple location token (city/state), try to extract the first word group
        m = re.search(r'([A-Za-z\-\.\s]{2,60})(?:,|\b)', s)
        if m:
            candidate = m.group(1).strip()
            # verify candidate isn't a generic word
            if len(candidate) > 1 and not re.search(r'^(notice|experience|apply|send|job|hiring)$', candidate, re.IGNORECASE):
                # if this candidate contains a known city substring, prefer that
                city2 = self.extract_city_from_text(candidate)
                if city2:
                    return city2
                # avoid returning generic role-like tokens as location
                if candidate.lower().split()[0] in self._location_token_blacklist or candidate.lower() in self._location_token_blacklist:
                    return "Location not specified"
                return candidate.title()

        return "Location not specified"

    def extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract skills from text and categorize them."""
        text = text.lower()
        found_skills = {category: [] for category in self.skills_dict}

        for category, skills in self.skills_dict.items():
            for skill in skills:
                if re.search(r'\b' + skill + r'\b', text):
                    # Clean up the found skill (remove regex escapes)
                    clean_skill = skill.replace('\\', '').replace('\.?', '.')
                    found_skills[category].append(clean_skill.title())

        # Remove empty categories
        return {k: sorted(list(set(v))) for k, v in found_skills.items() if v}

    def extract_company_from_email(self, email: str) -> Optional[str]:
        """Extract company name from email domain."""
        if not email:
            return None
            
        try:
            # Get domain parts
            parts = email.lower().split('@')
            if len(parts) != 2:
                return None
            
            # Split domain into parts (e.g., 'careers.company.co.in' -> ['careers', 'company', 'co', 'in'])
            domain_parts = parts[1].split('.')
            
            # Skip common email providers and their subdomains
            common_providers = {
                'gmail', 'yahoo', 'hotmail', 'outlook', 'live', 'aol', 'mail',
                'zoho', 'icloud', 'proton', 'yandex', 'rediff', 'protonmail'
            }
            if any(provider in domain_parts for provider in common_providers):
                return None

            # Try each part of the domain (excluding TLDs)
            tlds = {'com', 'co', 'org', 'net', 'edu', 'gov', 'mil', 'in', 'uk', 'us', 'eu'}
            potential_domains = [part for part in domain_parts if part not in tlds]

            # Check each potential domain part
            for domain in potential_domains:
                # Direct mapping check
                if domain in COMPANY_DOMAIN_MAP:
                    return COMPANY_DOMAIN_MAP[domain]
                
                # Try to match parts of compound domains
                # E.g., 'hcltechsolutions' should match 'hcltech'
                for company_domain, company_name in COMPANY_DOMAIN_MAP.items():
                    # Check if the company domain is a substantial part of the email domain
                    # or vice versa, but require at least 60% match to avoid false positives
                    if (company_domain in domain and len(company_domain) >= len(domain) * 0.6) or \
                       (domain in company_domain and len(domain) >= len(company_domain) * 0.6):
                        return company_name

            # If no match found in mapping, try to format the most likely domain part
            # Choose the longest non-TLD part as it's most likely the company name
            if potential_domains:
                main_domain = max(potential_domains, key=len)
                # Clean up domain to make it look like a company name
                company = main_domain.replace('-', ' ').replace('_', ' ')
                company = ' '.join(word.capitalize() for word in company.split())
                return company

            return None
        except Exception as e:
            print(f"Error extracting company from email: {str(e)}")
            return None

    def extract_company_from_description(self, text: str) -> Optional[str]:
        """Extract company name from job description."""
        if not text:
            return None
            
        # Common company name patterns
        patterns = [
            # Explicit company mentions
            r'(?i)company:\s*([A-Z][A-Za-z0-9\s&\'\.]+?)(?=\s+(?:is|are|we|in|,|\.|!|$))',
            r'(?i)organization:\s*([A-Z][A-Za-z0-9\s&\'\.]+?)(?=\s+(?:is|are|we|in|,|\.|!|$))',
            r'(?i)employer:\s*([A-Z][A-Za-z0-9\s&\'\.]+?)(?=\s+(?:is|are|we|in|,|\.|!|$))',
            
            # Job at Company patterns
            r'(?i)(?:job|position|opportunity|role|opening)\s+(?:is\s+)?(?:available\s+)?at\s+([A-Z][A-Za-z0-9\s&\'\.]+?)(?=\s+(?:is|are|we|in|,|\.|!|$))',
            r'(?i)at\s+([A-Z][A-Za-z0-9\s&\'\.]+?)(?=\s+(?:is|are|we|in|,|\.|!|$))',
            
            # Company is hiring patterns
            r'(?i)([A-Z][A-Za-z0-9\s&\'\.]+?)\s+is\s+(?:hiring|looking|seeking|recruiting|offering)',
            r'(?i)([A-Z][A-Za-z0-9\s&\'\.]+?)\s+(?:has|have)\s+(?:an?\s+)?(?:opening|opportunity|position|vacancy)',
            
            # Join Company patterns
            r'(?i)join\s+([A-Z][A-Za-z0-9\s&\'\.]+?)(?=\s+(?:as|and|in|,|\.|!|$))',
            r'(?i)work\s+(?:with|for)\s+([A-Z][A-Za-z0-9\s&\'\.]+?)(?=\s+(?:as|and|in|,|\.|!|$))'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                company = match.group(1).strip()
                # Clean up common suffixes
                company = re.sub(r'(?i)\s+(?:pvt\.?\s+ltd\.?|limited|inc\.?|corp\.?|corporation|company)$', '', company)
                # Check if the extracted company is in our known mappings (case-insensitive)
                for _, known_name in COMPANY_DOMAIN_MAP.items():
                    if company.lower() == known_name.lower():
                        return known_name
                return company
                
        return None

    def analyze_post(self, post_data: Dict) -> Dict:
        """Analyze a job post to extract location, company, and skills."""
        description = post_data.get('description', '')
        email = post_data.get('email', '')
        enhanced = post_data.copy()

        # Helper: consider these as 'empty' placeholders we should override
        # include common variants such as 'Company Not Found' that appear in imports
        empty_placeholders = {
            '', None, 'not found', 'n/a', 'unknown', 'not specified', 'location not specified',
            'company not found', 'company not specified', 'company not provided', 'company notavailable',
            'company not available'
        }

        # Location extraction is disabled per user request; preserve existing value if present
        # enhanced['location'] remains unchanged

        # Extract or override company - try description first, then email
        cur_company = enhanced.get('company', '')
        # Treat certain labels like 'Company Not Found' as placeholders
        cur_company_val = cur_company if not isinstance(cur_company, str) else cur_company.lower().strip()
        if not cur_company or (isinstance(cur_company, str) and cur_company_val in empty_placeholders):
            company = self.extract_company_from_description(description)
            if not company:
                company = self.extract_company_from_email(email)
            # As a last resort, attempt to infer company from other fields (e.g., subject, title)
            if not company:
                for k, v in post_data.items():
                    if k in ('description', 'company', 'location'):
                        continue
                    if not isinstance(v, str) or not v:
                        continue
                    if v.lower().strip() in empty_placeholders:
                        continue
                    # Skip fields that are clearly links or URLs
                    if self.is_probable_link(v):
                        continue
                        # try description-style extraction on this field
                        company = self.extract_company_from_description(v)
                        if company:
                            break
                        company = self.extract_company_from_email(v)
                        if company:
                            break
            if company:
                enhanced['company'] = company

        # Extract skills if missing or empty
        if 'skills' not in enhanced or not enhanced.get('skills'):
            enhanced['skills'] = self.extract_skills(description)

        # Skipping all further location inference and normalization by user request.

        # Location normalization disabled; return enhanced post as-is
        return enhanced