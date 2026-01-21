#!/usr/bin/env python3
"""
Script to remove theme references from all panel files.
"""
import os
import re

PANELS_DIR = r'c:\Users\fatin\Downloads\aiwebdevtest\pulse\src\pulse\panels'

PANEL_FILES = [
    'disk.py',
    'network.py', 
    'storage.py',
    'kernel.py',
    'process.py',
    'insight.py',
    'main_view.py'
]

def update_panel_file(filepath):
    """Update a single panel file to remove theme references."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Remove the import line
    content = re.sub(r'from pulse\.state import current_theme\n', '', content)
    
    # Replace theme color references
    content = re.sub(r'current_theme\["accent"\]', '"cyan"', content)
    content = re.sub(r'current_theme\["focus"\]', '"cyan"', content)
    content = re.sub(r'current_theme\["alarm"\]', '"red"', content)
    content = re.sub(r'current_theme\["read"\]', '"cyan"', content)
    content = re.sub(r'current_theme\["write"\]', '"yellow"', content)
    
    # Remove heat parameter from function calls
    content = re.sub(r', current_theme\["heat"\]', '', content)
    
    # Remove manual style.border and style.color assignments for alarm
    content = re.sub(r'\s*self\.styles\.border = \("heavy", current_theme\["alarm"\]\)\n', '', content)
    content = re.sub(r'\s*self\.styles\.border = \("heavy", "red"\)\n', '', content)
    content = re.sub(r'\s*self\.styles\.color = current_theme\["alarm"\]\n', '', content)
    content = re.sub(r'\s*self\.styles\.color = "red"\n', '', content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    print("Updating panel files to remove theme references...\n")
    
    updated_count = 0
    for filename in PANEL_FILES:
        filepath = os.path.join(PANELS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"⚠ {filename}: File not found")
            continue
        
        if update_panel_file(filepath):
            print(f"✓ {filename}: Updated")
            updated_count += 1
        else:
            print(f"- {filename}: No changes needed")
    
    print(f"\n✓ Complete! Updated {updated_count} panel files.")

if __name__ == '__main__':
    main()
