import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\التسويات\TASKS_DETAILED.md"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace checkboxes for Phase 1 endpoints
replacements = {
    "- [ ] Django Views مسؤولة عن الـ GET/POST": "- [x] Django Views مسؤولة عن الـ GET/POST",
    "- [ ] Django Context لجلب Vendor Settlements": "- [x] Django Context لجلب Vendor Settlements",
    "- [ ] Django Context لجلب Company Settlements": "- [x] Django Context لجلب Company Settlements",
    "- [ ] Django Context لجلب Delegate Settlements": "- [x] Django Context لجلب Delegate Settlements",
    "- [ ] دالة Post لمعالجة عملية تسوية جديدة": "- [x] دالة Post لمعالجة عملية تسوية جديدة",
    "- [ ] دالة Post لتحديث الحالة": "- [x] دالة Post لتحديث الحالة",
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated tasks")
