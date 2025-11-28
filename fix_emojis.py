#!/usr/bin/env python3
"""
Replace all Unicode emojis with ASCII equivalents in app.py
"""

import re

# Emoji to ASCII replacements
EMOJI_MAP = {
    '≡ƒÜÇ': '[*]',
    '≡ƒô¥': '[#]',
    '≡ƒæñ': '[@]',
    'ΓÜÖ∩╕Å': '[>]',
    '≡ƒöç': '[+]',
    '≡ƒîÉ': '[!]',
    '≡ƒùé': '[.]',
    'Γ£à': '[OK]',
    '≡ƒöì': '[DEBUG]',
    'Γ¥î': '[ERROR]',
    '≡ƒº╣': '[DONE]',
    'ΓÜá∩╕Å': '[WARN]',
    '≡ƒôä': '[INFO]',
    '≡ƒöæ': '[LOAD]',
    '≡ƒôº': '[COUNT]',
    '≡ƒôà': '[DATE]',
    '≡ƒÆ│': '[PLAN]',
    '≡ƒôè': '[STAT]',
    '≡ƒöÆ': '[STOP]',
    '≡ƒöî': '[CONN]',
    '≡ƒÆô': '[BEAT]',
    '≡ƒôÑ': '[REQ]',
    '≡ƒÆ╛': '[SAVE]',
    '≡ƒº╡': '[START]',
    '≡ƒöä': '[INSTALL]',
    '≡ƒöÉ': '[LOGIN]',
    '≡ƒöº': '[USE]',
    'Γä╣∩╕Å': '[EMPTY]',
    '≡ƒæü∩╕Å': '[VISIBLE]',
    '≡ƒÅá': '[WIN]',
    'ΓÅ│': '[WAIT]',
}

def fix_emojis(file_path):
    """Replace all emojis in the file with ASCII equivalents"""
    print(f"Reading {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count replacements
    replacement_count = 0
    
    # Replace each emoji
    for emoji, ascii_replacement in EMOJI_MAP.items():
        count = content.count(emoji)
        if count > 0:
            print(f"  Replacing {repr(emoji)} with {ascii_replacement}: {count} occurrences")
            content = content.replace(emoji, ascii_replacement)
            replacement_count += count
    
    # Write back
    print(f"\nWriting changes back to {file_path}...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Done! Made {replacement_count} replacements.")

if __name__ == "__main__":
    fix_emojis("sendmail/app.py")
