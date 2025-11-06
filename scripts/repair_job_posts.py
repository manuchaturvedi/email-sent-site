#!/usr/bin/env python3
"""
Attempt to repair a truncated/malformed job_posts.json by salvaging any complete
JSON objects from the top-level array. Creates a timestamped backup before writing.
Prints a short summary and exits with 0 on success, 2 on no objects recovered.
"""
from pathlib import Path
import json, datetime, sys

root = Path(r"c:/Users/windows 10/Desktop/AI_support")
jp = root / 'job_posts.json'
if not jp.exists():
    print(f"ERROR: {jp} does not exist")
    sys.exit(1)

content = jp.read_text(encoding='utf-8', errors='replace')
# Quick check: try full parse first
try:
    parsed = json.loads(content)
    print("job_posts.json is valid JSON already. No repair needed.")
    print(f"Found {len(parsed) if isinstance(parsed, list) else 'non-list JSON'} entries")
    sys.exit(0)
except Exception as e:
    print(f"Full JSON parse failed: {e}")

# Create backup
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup = root / f'job_posts.json.bak.{ts}'
backup.write_text(content, encoding='utf-8')
print(f"Backup written to: {backup}")

# Attempt salvage: find complete top-level objects inside top-level array
s = content
# find first '['
idx = s.find('[')
if idx == -1:
    print("No top-level array found. Cannot salvage.")
    sys.exit(2)

i = idx + 1
n = len(s)
objs = []
while i < n:
    # skip whitespace and commas
    while i < n and s[i] in ' \t\r\n,':
        i += 1
    if i >= n:
        break
    if s[i] != '{':
        # Unexpected content; skip until next { or end
        nxt = s.find('{', i)
        if nxt == -1:
            break
        i = nxt
    # parse object by brace depth
    depth = 0
    j = i
    in_string = False
    escape = False
    while j < n:
        ch = s[j]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    j += 1
                    # attempt to parse s[i:j]
                    candidate = s[i:j]
                    try:
                        obj = json.loads(candidate)
                        objs.append(obj)
                        print(f"Recovered object #{len(objs)} at chars {i}-{j}")
                        i = j
                    except Exception as ee:
                        # can't parse this object; skip it
                        print(f"Failed to parse candidate object at {i}-{j}: {ee}")
                        i = j
                    break
        j += 1
    else:
        # hit end of file while inside an object - truncated
        break

print(f"Total recovered objects: {len(objs)}")
if len(objs) == 0:
    # nothing salvageable; write an empty array to allow app to continue
    new_content = '[]\n'
    jp.write_text(new_content, encoding='utf-8')
    print(f"No objects recovered. Replaced {jp.name} with empty array []. Original backed up to {backup.name}.")
    sys.exit(2)
else:
    # write the recovered objects into file
    new = json.dumps(objs, indent=2, ensure_ascii=False)
    jp.write_text(new + '\n', encoding='utf-8')
    print(f"Wrote {len(objs)} recovered objects to {jp}")
    sys.exit(0)
