import re
from typing import Dict, Optional, List
from datetime import datetime


class JobPostAnalyzer:
    """Heuristic job post analyzer that avoids heavy ML deps.

    This uses a set of regex patterns and keyword matching to extract
    company, location, and skills from a post description. It's not as
    powerful as a full NLP model but is lightweight and works well for
    short job snippets.
    """

    def __init__(self):
        self.location_patterns = [
            r"\b(?:in|at|from)\s+([A-Z][A-Za-z0-9 &\-]+(?:,\s*[A-Z][A-Za-z0-9 &\-]+)*)",
            r"Location\s*[:\-]\s*([A-Z][A-Za-z0-9 &\-]+(?:,\s*[A-Z][A-Za-z0-9 &\-]+)*)",
        ]

        self.company_patterns = [
            r"(?:at|with|from|for)\s+([A-Z][A-Za-z0-9 &\-]+?)(?:\.|,|\s|$)",
            r"^([A-Z][A-Za-z0-9 &\-]+)\s+-",
            r"^([A-Z][A-Za-z0-9 &\-]+)\s+is\s+",
        ]

        # Lightweight skill keywords grouped by category
        self.skills_keywords = {
            'languages': ['python', 'java', 'javascript', 'c++', 'ruby', 'php', 'typescript', 'golang'],
            'frameworks': ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'node', 'express'],
            'cloud': ['aws', 'azure', 'gcp', 'kubernetes', 'docker', 'terraform'],
            'databases': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch'],
            'tools': ['git', 'jenkins', 'jira', 'confluence', 'ansible', 'puppet', 'chef']
        }

    def extract_company_name(self, text: str) -> Optional[str]:
        """Try several regex patterns to infer the company name."""
        if not text:
            return None

        # Try explicit patterns
        for pattern in self.company_patterns:
            m = re.search(pattern, text)
            if m:
                name = m.group(1).strip()
                # strip trailing prepositions or words
                name = re.sub(r"\s+(is|a|the|company|inc|llc|corp)\b.*$", '', name, flags=re.I)
                return name

        # Fallback: look for ALL-CAPS or Title Case token sequences near start
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            first = lines[0]
            m = re.match(r"([A-Z][A-Za-z0-9&\- ]{2,40})", first)
            if m:
                cand = m.group(1).strip()
                if len(cand) > 2:
                    return cand

        return None

    def extract_location(self, text: str) -> Optional[str]:
        """Try regex patterns and heuristics to find a location string."""
        if not text:
            return None

        for pattern in self.location_patterns:
            m = re.search(pattern, text, flags=re.I)
            if m:
                return m.group(1).strip()

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

        company = post_data.get('company') or self.extract_company_name(desc)
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
    sample = {
        'description': (
            "Exciting opportunity at Veersa Technologies India in Noida! "
            "We're hiring a DevOps Engineer. Required: Jenkins, GitHub Actions, Docker, Kubernetes. "
            "Location: Noida, India"
        )
    }
    print(analyzer.analyze_job_post(sample))