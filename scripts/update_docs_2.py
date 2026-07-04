import os
import glob

replacements = {
    "Models + APIs": "Models + Views",
    "APIs/Views": "Views",
    "/api/settlements/vendors/": "/custom-settlements/vendors/",
    "/api/settlements/vendors/{id}/": "/custom-settlements/vendors/<int:id>/",
    "/api/settlements/companies/": "/custom-settlements/companies/",
    "/api/settlements/delegates/": "/custom-settlements/delegates/",
    "معالجتها بالـ POST من API": "معالجتها بالـ POST Request",
}

folder = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\التسويات"
files = glob.glob(os.path.join(folder, "*.md"))

updated_files = []

for file_path in files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    original_content = content
    
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        updated_files.append(os.path.basename(file_path))

print("Updated files:", updated_files)
