import re
from typing import Dict, Optional, List
from datetime import datetime


class JobPostAnalyzer:
    """Heuristic job post analyzer that avoids heavy ML deps.

    This uses a set of regex patterns and keyword matching to extract
    company, location, and skills from a post description. It's lightweight
    and tuned with additional heuristics (email domain fallback, title/source
    scanning) to improve company extraction coverage.
    """

    COMMON_EMAIL_PROVIDERS = {
        'gmail', 'yahoo', 'hotmail', 'outlook', 'live', 'icloud', 'aol', 'protonmail', 'yandex', 'gmx'
    }

    def __init__(self):
        # Location patterns: common explicit forms
        self.location_patterns = [
            r"\b(?:in|at|from|based in|headquartered in)\s+([A-Z][A-Za-z0-9 &\-]+(?:,\s*[A-Z][A-Za-z0-9 &\-]+)*)",
            r"Location\s*[:\-]\s*([A-Z][A-Za-z0-9 &\-]+(?:,\s*[A-Z][A-Za-z0-9 &\-]+)*)",
            r"\b([A-Z][A-Za-z]+(?:,\s*[A-Z][A-Za-z]+){0,2})\b",
        ]

        # Company patterns expanded to catch more real-world phrases
        self.company_patterns = [
            r"Company\s*[:\-]\s*([A-Z][A-Za-z0-9 &\-\.]+?)\b",
            r"(?:at|with|from|for|by|through)\s+([A-Z][A-Za-z0-9 &\-\.]+?)(?:\.|,|\s|$)",
            r"Hiring\s+(?:at\s+)?([A-Z][A-Za-z0-9 &\-\.]+?)\b",
            r"Posted\s+by\s+([A-Z][A-Za-z0-9 &\-\.]+?)\b",
            r"\b([A-Z][A-Za-z0-9&\- ]{2,50})\s+-",
            r"\bJoin\s+([A-Z][A-Za-z0-9 &\-\.]+?)\b",
            r"^([A-Z][A-Za-z0-9 &\-\.]+)\s+is\b",
        ]

        # Lightweight skill keywords grouped by category
        self.skills_keywords = {
            'languages': ['python', 'java', 'javascript', 'c++', 'ruby', 'php', 'typescript', 'golang'],
            'frameworks': ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'node', 'express'],
            'cloud': ['aws', 'azure', 'gcp', 'kubernetes', 'docker', 'terraform'],
            'databases': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch'],
            'tools': ['git', 'jenkins', 'jira', 'confluence', 'ansible', 'puppet', 'chef']
        }

    def _cleanup_company(self, name: str) -> str:
        """Normalize company string: remove trailing punctuation and common suffixes."""
        if not name:
            return name
        name = name.strip().rstrip('.,;')
        # remove common suffixes
        name = re.sub(r"\b(inc|llc|ltd|corporation|corp|co|company)\b\.?$", '', name, flags=re.I).strip()
        # collapse extra spaces
        name = re.sub(r"\s{2,}", ' ', name)
        return name

    def _company_from_email(self, email: str) -> Optional[str]:
        """Infer a company name from an email domain when possible.
        Example: jobs@veersa.com -> Veersa
        Skips common providers like gmail/yahoo.
        """
        if not email or '@' not in email:
            return None
        domain = email.split('@')[-1].lower()
        # strip subdomains
        parts = domain.split('.')
        # remove tld parts
        if len(parts) >= 2:
            base = parts[-2]
        else:
            base = parts[0]
        if base in self.COMMON_EMAIL_PROVIDERS:
            return None
        # remove common prefixes
        base = re.sub(r'^(www|mail|careers|jobs|hr|info)-?', '', base)
        # convert to Title Case
        return base.replace('-', ' ').replace('_', ' ').title()

    def extract_company_name(self, text: str, title: Optional[str] = None, email: Optional[str] = None) -> Optional[str]:
        """Try several regex patterns to infer the company name. Also checks title and email as fallbacks."""
        # prefer explicit title/company if provided
        if title:
            t = title.strip()
            if len(t) > 2:
                # title often starts with "Company - Role" or "Company: Role" -> extract
                m = re.match(r"([A-Z][A-Za-z0-9 &\-\.]{2,60})\s*[:\-\|]\s*", t)
                if m:
                    return self._cleanup_company(m.group(1))

        if not text:
            # fallback to email-derived company
            return self._company_from_email(email) if email else None

        # Try explicit patterns in the description
        for pattern in self.company_patterns:
            m = re.search(pattern, text)
            if m:
                name = m.group(1).strip()
                name = self._cleanup_company(name)
                if name:
                    return name

        # Check for 'Company: NAME' variations captured earlier in patterns
        # Fallback: look for ALL-CAPS or Title Case token sequences near start
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            # check each of the first 3 lines for a candidate company token
            for first in lines[:3]:
                # common pattern: "Company Name - Role"
                m = re.match(r"([A-Z][A-Za-z0-9&\-\. ]{2,60})\s*[-:|]\s*", first)
                if m:
                    cand = self._cleanup_company(m.group(1).strip())
                    if cand:
                        return cand
                # title-case sequence
                m2 = re.match(r"([A-Z][A-Za-z0-9&\- ]{2,40})", first)
                if m2:
                    cand2 = self._cleanup_company(m2.group(1).strip())
                    if cand2:
                        return cand2

        # Last-resort: infer from email
        if email:
            inferred = self._company_from_email(email)
            if inferred:
                return inferred

        return None

    def extract_location(self, text: str) -> Optional[str]:
        """Try regex patterns and heuristics to find a location string."""
        if not text:
            return None

        for pattern in self.location_patterns:
            m = re.search(pattern, text, flags=re.I)
            if m:
                candidate = m.group(1).strip()
                # normalize common tokens
                if re.search(r"\b(remote|work from home|wfh)\b", candidate, flags=re.I):
                    return 'Remote'
                return candidate

        # Heuristic: look for common city/state tokens
        m = re.search(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+){0,2})(?:,?\s*(?:India|USA|United States|UK|United Kingdom|Remote))?\b", text)
        if m:
            return m.group(1).strip()

        # Look for 'Remote' or 'Work from home'
        if re.search(r"\b(remote|work from home|wfh)\b", text, flags=re.I):
            return 'Remote'

        return None

    def extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Match known skill keywords in the text. Returns dict of lists."""
        text_low = (text or '').lower()
        found_skills = {k: [] for k in self.skills_keywords}
        for cat, keywords in self.skills_keywords.items():
            for kw in keywords:
                # match whole words and common variants (node -> node.js)
                if re.search(r"\b" + re.escape(kw) + r"\b", text_low):
                    found_skills[cat].append(kw)
        return found_skills

    def analyze_job_post(self, post_data: Dict) -> Dict:
        """Return an enhanced copy of post_data with company/location/skills added when found."""
        desc = (post_data.get('description') or '')
        enhanced = post_data.copy()

        # Pass title/email to company extractor to improve detection
        company = post_data.get('company') or self.extract_company_name(desc, title=post_data.get('title'), email=post_data.get('email'))
        location = post_data.get('location') or self.extract_location(desc)
        skills = self.extract_skills(desc)

        if company:
            enhanced['company'] = company
        if location:
            enhanced['location'] = location
        enhanced['skills'] = skills
        enhanced['analyzed_at'] = datetime.now().isoformat()

        return enhanced


if __name__ == '__main__':
    analyzer = JobPostAnalyzer()
    samples = [
        {
            'title': 'Veersa Technologies - DevOps Engineer',
            'description': "Exciting opportunity at Veersa Technologies India in Noida! We're hiring a DevOps Engineer. Required: Jenkins, GitHub Actions, Docker, Kubernetes. Location: Noida, India",
            'email': 'jobs@veersa.com'
        },
        {
            'description': "Senior Python Developer (Remote) - Company: Acme Cloud Solutions. Required: Python, Django, AWS",
            'email': 'hr@acme-cloud.co'
        },
        {
            'description': "Fullstack role posted by InnovateX in Bangalore. Skills: React, Node.js",
            'email': 'contact@innovatex.com'
        }
    ]

    for s in samples:
        print('---')
        print(analyzer.analyze_job_post(s))
