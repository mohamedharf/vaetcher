"""
Script to wrap plain Arabic string messages in views.py with _() for i18n.
Usage: python scripts/wrap_messages_i18n.py
"""
import re
import sys
import os

def wrap_messages(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Pattern 1: messages.success/error/warning/info(request, 'string')
    # Wrap single-quoted plain strings (not already _(), not f-strings)
    def wrap_single_quote(m):
        method = m.group(1)
        string = m.group(2)
        return f"messages.{method}(request, _('{string}'))"
    
    # Pattern: messages.xxx(request, 'some arabic text') — simple single-quoted string
    pattern_sq = r"messages\.(success|error|warning|info)\(request,\s*'([^']+)'\)"
    content = re.sub(pattern_sq, wrap_single_quote, content)
    
    # Pattern 2: messages.xxx(request, "string") — simple double-quoted string  
    def wrap_double_quote(m):
        method = m.group(1)
        string = m.group(2)
        # Skip if already has _() or other wrappers
        if string.startswith('_('):
            return m.group(0)
        return f'messages.{method}(request, _("{string}"))'
    
    pattern_dq = r'messages\.(success|error|warning|info)\(request,\s*"([^"]+)"\)'
    content = re.sub(pattern_dq, wrap_double_quote, content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {filepath}")
        # Count changes
        orig_count = len(re.findall(r"messages\.(success|error|warning|info)\(request,\s*['\"]", original))
        new_count_unwrapped = len(re.findall(r"messages\.(success|error|warning|info)\(request,\s*['\"]", content))
        print(f"  Before: {orig_count} calls, After unwrapped: {new_count_unwrapped}")
    else:
        print(f"No changes in: {filepath}")

if __name__ == '__main__':
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    views_files = [
        os.path.join(base, 'core', 'views.py'),
        os.path.join(base, 'accounts', 'views.py'),
    ]
    for vf in views_files:
        if os.path.exists(vf):
            wrap_messages(vf)
            print(f"Done: {vf}")
        else:
            print(f"Not found: {vf}")
