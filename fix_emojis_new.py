#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Replace all Unicode emojis with ASCII equivalents in app.py
"""

def fix_emojis(file_path):
    """Replace all emojis in the file with ASCII equivalents"""
    print(f"Reading {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Emoji to ASCII replacements - using actual emoji characters
    replacements = [
        ('🚀', '[*]'),
        ('🆔', '[#]'),
        ('👤', '[@]'),
        ('▶️', '[>]'),
        ('➕', '[+]'),
        ('🐳', '[DOCKER]'),
        ('📁', '[FOLDER]'),
        ('✅', '[OK]'),
        ('🔍', '[DEBUG]'),
        ('❌', '[ERROR]'),
        ('🧹', '[DONE]'),
        ('⚠️', '[WARN]'),
        ('⚠', '[WARN]'),
        ('📄', '[INFO]'),
        ('🔐', '[LOAD]'),
        ('📊', '[COUNT]'),
        ('📅', '[DATE]'),
        ('📋', '[PLAN]'),
        ('📈', '[STAT]'),
        ('🚫', '[STOP]'),
        ('🔌', '[CONN]'),
        ('💓', '[BEAT]'),
        ('📥', '[REQ]'),
        ('💾', '[SAVE]'),
        ('🧵', '[THREAD]'),
        ('🔧', '[INSTALL]'),
        ('🔑', '[LOGIN]'),
        ('🔺', '[USE]'),
        ('🔹', '[EMPTY]'),
        ('👁️', '[VISIBLE]'),
        ('👁', '[VISIBLE]'),
        ('🪟', '[WIN]'),
        ('⏳', '[WAIT]'),
        ('🌐', '[WWW]'),
        ('📜', '[SCROLL]'),
        ('📧', '[EMAIL]'),
        ('📨', '[SENT]'),
        ('🛑', '[STOP!]'),
        ('🎉', '[COMPLETE]'),
    ]
    
    # Count total replacements
    total_replacements = 0
    
    # Replace each emoji
    for emoji, ascii_replacement in replacements:
        count = content.count(emoji)
        if count > 0:
            print(f"  Replacing '{emoji}' with {ascii_replacement}: {count} occurrences")
            content = content.replace(emoji, ascii_replacement)
            total_replacements += count
    
    # Write back
    print(f"\nWriting changes back to {file_path}...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Done! Made {total_replacements} replacements.")
    return total_replacements

if __name__ == "__main__":
    fix_emojis("sendmail/app.py")
