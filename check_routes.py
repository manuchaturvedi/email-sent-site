import sys
sys.path.insert(0, '/app')

from sendmail.app import app, ADMIN_EMAIL

print("\n=== ADMIN ROUTES ===")
admin_routes = [str(rule) for rule in app.url_map.iter_rules() if 'admin' in str(rule)]
for route in sorted(admin_routes):
    print(f"  {route}")

print(f"\n=== ADMIN EMAIL ===")
print(f"  {ADMIN_EMAIL}")

print("\n")
