import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\التسويات\TASKS_DETAILED.md"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace checkboxes for Phase 1
replacements = {
    "- [ ] إنشاء `CompanySettlement` Model": "- [x] إنشاء `CompanySettlement` Model",
    "- [ ] إنشاء `DelegateSettlement` Model": "- [x] إنشاء `DelegateSettlement` Model",
    "- [ ] تحسين `VendorSettlement` بإضافة حقول جديدة": "- [x] تحسين `VendorSettlement` بإضافة حقول جديدة",
    "- [ ] إنشاء Migrations": "- [x] إنشاء Migrations",
    "- [ ] التحقق من إنشاء الجداول بشكل صحيح": "- [x] التحقق من إنشاء الجداول بشكل صحيح",
    "⚠️ Incomplete": "✅ Completed (Models added)",
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated tasks")
