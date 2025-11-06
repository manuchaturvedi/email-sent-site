import sys, os
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, 'sendmail'))
from job_analyzer import JobAnalyzer

s = JobAnalyzer()
text = '''Dear Connections,

📣 We have a urgent hiring for .Net Technical lead.

Role: .Net Technical Lead:
Experience: Minimum 8-13 years

📍 Location: Thane West (100 percent work from office, no hybrid, no work from home)

Must-haves/You’re good at:
● Good at Full stack development, ability to design modules independently.
● Proficient in C#,MVC, HTML5, CSS, JavaScript, Web Services, WCF, Web API.
● Proficient normalizing database schema from the raw problem statement, SQL Server, Transact SQL,
stored procedures, triggers, DTS packages.
● Strong understanding of object-oriented programming and SOLID design principles.
● Experience with applying design and architectural patterns.
● Good at understanding requirements and estimation.
● Ability to own a technology stack for the program as a whole.
● Ability to adapt and mentor the team according to the technology roadmap.

Nice-to-haves/You’re Extra Awesome if:
● You enjoy solving problems: You love taking on challenges and finding creative solutions. You don’t get
flustered easily. If you don’t know an answer, you’ll dig in until you find it.
● You think on your feet: You like learning new things & you learn quickly. When things change, you know

Interested candidates can share their updated CV onor whatsapp on 8108961282'''

print('extract_location ->', s.extract_location(text))
print('normalize ->', s._normalize_location_str(s.extract_location(text)))
print('city match ->', s.extract_city_from_text(text))
