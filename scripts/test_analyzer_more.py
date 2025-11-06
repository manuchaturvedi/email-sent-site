import sys, json
sys.path.insert(0, r'C:\Users\windows 10\Desktop\AI_support')
from sendmail.job_analyzer import JobAnalyzer

analyzer = JobAnalyzer()

samples = [
    # From user's recent rows
    {
        'description': "Let's hashtag #Learn #code #Jobs #IdeaToOutput. Java",
        'company': 'Oneiot',
        'location': '',
        'email': 'career@oneiot.io'
    },
    {
        'description': "🔥 We’re on the hunt for a Senior .NET Developer... 📍 Location: Ahmedabad, Gujarat 💼 Experience: 5+",
        'company': 'Smartlion',
        'location': 'Location: Ahmedabad, Gujarat 💼 Experience: 5+',
        'email': 'khusbu.s@smartlion.co.in'
    },
    {
        'description': "We are hiring Dot Net Core Exp: 4+Years Location: Bangalore Notice: Upto 15 Days If interested, please share your resume : Mandatory .NET Core andCore AWS(OR GCP/Azure) Microservices SQL -REST API ...",
        'company': 'Company Not Found',
        'location': 'Remote/On-site',
        'email': 'Komal.p@sureminds.co.in'
    },
    # recruiter gmail
    {
        'description': "🚀 OPT Talent – Let’s Connect! Hiring: Java, .NET, Full Stack...",
        'company': 'Company Not Found',
        'location': 'Remote/On-site',
        'email': 'Recruitercareits@gmail.com'
    },
    # On-site with parentheses and sector
    {
        'description': 'Location: On-Site (Noida, Sector-16 Office) — No Remote / Work From Home Option',
        'company': '',
        'location': '',
        'email': 'hr@someco.com'
    },
    # Emoji location
    {
        'description': '📍 Location: Gurugram — Immediate joiners required.',
        'company': '',
        'location': '',
        'email': 'jobs@anothersite.com'
    },
    # Hybrid with dash
    {
        'description': 'Location: Bangalore – Marathahalli (Hybrid Mode)',
        'company': '',
        'location': 'Remote/On-site',
        'email': 'contact@companyxyz.com'
    },
    # Work From Home city
    {
        'description': 'Work From Home in Mumbai — Openings for Python developers.',
        'company': '',
        'location': '',
        'email': 'recruit@startup.in'
    },
    # Sector only
    {
        'description': 'Office: Sector-63, Noida — Apply now',
        'company': '',
        'location': '',
        'email': 'careers@techfirm.in'
    },
    # US city
    {
        'description': 'We’re hiring: .NET Developer | Onsite – Erie, PA. Strong C#/.NET skills required.',
        'company': 'Metarpo',
        'location': 'Erie',
        'email': 'jobs@metarpo.com'
    },
    # ambiguous noisy location
    {
        'description': 'Hiring: Full Stack. Location- Remote. Note: Immediate joiners only. Apply ASAP!',
        'company': '',
        'location': 'Remote',
        'email': 'hr@fullstackco.com'
    },
    # company in email subdomain
    {
        'description': 'Senior Engineer role, Riyadh office',
        'company': 'Company Not Found',
        'location': '',
        'email': 'sathvik.shetty@linnk.com'
    },
]

out = []
count_company = 0
count_location = 0
for s in samples:
    orig_company = s.get('company','')
    orig_location = s.get('location','')
    enhanced = analyzer.analyze_post(s)
    if enhanced.get('company','') != orig_company:
        count_company += 1
    if enhanced.get('location','') != orig_location:
        count_location += 1
    out.append({'orig_company': orig_company, 'new_company': enhanced.get('company',''), 'orig_location': orig_location, 'new_location': enhanced.get('location',''), 'email': s.get('email')})

print('company_updates=', count_company, 'location_updates=', count_location)
print(json.dumps(out, indent=2))
