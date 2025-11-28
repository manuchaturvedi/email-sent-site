"""
Test script for LLM-powered job analyzer
"""
import sys
sys.path.append('sendmail')

from job_analyzer import JobAnalyzer

# Test job post data
test_posts = [
    {
        "description": "🚀 We're hiring Java Full Stack Developer with Angular 9+ Years exp 🎯 Location: McLean, VA (Onsite) 💼 Experience: 12+ years",
        "title": "Java Full Stack Engineer"
    },
    {
        "description": "Greeting From Linnk Group.. 🚀 Job Opening: CRM Developer | Riyadh, Saudi Arabia 📅 Experience: 7+ Years 💼 Type: Contract",
        "title": ""
    },
    {
        "description": "We are hiring Dot Net Core Exp: 4+Years Location: Bangalore Notice: Upto 15 Days",
        "company": "TechCorp",
        "location": ""
    }
]

print("=" * 60)
print("Testing LLM-Powered Job Analyzer")
print("=" * 60)

analyzer = JobAnalyzer()

for i, post in enumerate(test_posts, 1):
    print(f"\n[Test {i}]")
    print(f"Input: {post.get('description', '')[:100]}...")
    
    result = analyzer.analyze_post(post)
    
    print(f"✓ Title: {result['title']}")
    print(f"✓ Company: {result['company']}")
    print(f"✓ Location: {result['location']}")
    print(f"✓ Role: {result['role']}")
    print(f"✓ Experience: {result['experience_level']}")

print("\n" + "=" * 60)
print("✅ All tests completed!")
print("=" * 60)
