import os
import re

def process_html_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 1. Add {% load i18n %} if not present
    if '{% load i18n %}' not in content:
        if '{% extends' in content:
            # Insert after the extends tag
            content = re.sub(r'({%\s*extends[^%]+%})', r'\1\n{% load i18n %}', content, count=1)
        else:
            # Insert at the top
            content = '{% load i18n %}\n' + content

    # 2. Find Arabic text in attributes: placeholder, title, value
    attr_pattern = r'(placeholder|title|value)="([^"{]*[\u0600-\u06FF]+[^"{]*)"'
    def attr_repl(m):
        attr = m.group(1)
        text = m.group(2)
        if '{%' in text or '{{' in text:
            return m.group(0)
        return f'{attr}="{{% trans \'{text.strip()}\' %}}"'
    
    content = re.sub(attr_pattern, attr_repl, content)

    # 3. Find pure Arabic text between > and <
    # We avoid matching if there's { or } inside to prevent messing up Django tags.
    node_pattern = r'>([^<{}]+[\u0600-\u06FF]+[^<{}]+)<|>([\u0600-\u06FF]+)<'
    
    def text_repl(m):
        # The text can be in group 1 or group 2
        text = m.group(1) if m.group(1) is not None else m.group(2)
        
        stripped = text.strip()
        if not stripped:
            return f'>{text}<'
        
        # Skip if already wrapped (though the regex excludes { so it shouldn't happen)
        if '{% trans' in text or '{{' in text:
            return f'>{text}<'
            
        # Clean up multiple spaces and newlines inside the text
        cleaned = re.sub(r'\s+', ' ', stripped)
        cleaned_escaped = cleaned.replace("'", "\\'")
        
        # Find leading and trailing whitespace to preserve HTML formatting
        leading_ws = text[:len(text) - len(text.lstrip())]
        trailing_ws = text[len(text.rstrip()):]
        
        return f'>{leading_ws}{{% trans \'{cleaned_escaped}\' %}}{trailing_ws}<'

    content = re.sub(node_pattern, text_repl, content)

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, 'templates')
    
    modified_count = 0
    total_count = 0
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                total_count += 1
                filepath = os.path.join(root, file)
                if process_html_file(filepath):
                    modified_count += 1
                    print(f"Modified: {os.path.relpath(filepath, base_dir)}")
                    
    print(f"\nTotal HTML files processed: {total_count}")
    print(f"Files modified: {modified_count}")

if __name__ == '__main__':
    main()
