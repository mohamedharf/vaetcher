import re

with open('core/views.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

classes_to_find = [
    'CustomManagerDashboardView',
    'CustomPOSView',
    'CustomDoctorsView',
    'CustomVendorsDirectoryView',
    'CustomVendorSettlementsView',
    'CustomEventsWizardView',
    'CustomEmailLogsView',
    'CustomSystemSettingsView'
]

for cls in classes_to_find:
    pattern = re.compile(rf'class\s+{cls}\b')
    found = False
    for i, line in enumerate(lines):
        if pattern.search(line):
            print(f"{cls} found at line {i+1}")
            # Find next class or end of file to estimate block size
            next_class_line = len(lines)
            for j in range(i+1, len(lines)):
                if lines[j].startswith('class '):
                    next_class_line = j + 1
                    break
            print(f"  Range: {i+1} to {next_class_line}")
            found = True
            break
    if not found:
        print(f"{cls} NOT found")
