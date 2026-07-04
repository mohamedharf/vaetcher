import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\التسويات\TASKS_DETAILED.md"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace checkboxes for Phase 2 (Frontend)
replacements = {
    "- [ ] إضافة Tabs للتنقل بين أنواع التسويات": "- [x] إضافة Tabs للتنقل بين أنواع التسويات",
    "- [ ] تحويل البيانات من Hardcoded إلى Dynamic": "- [x] تحويل البيانات من Hardcoded إلى Dynamic",
    "- [ ] إضافة Loading States و Error Handling": "- [x] إضافة رسائل الأخطاء والنجاح (Messages Framework)",
    "- [ ] Vendor Settlements Table": "- [x] Vendor Settlements Table",
    "- [ ] Company Settlements Table": "- [x] Company Settlements Table",
    "- [ ] Delegate Settlements Table": "- [x] Delegate Settlements Table",
    "- [ ] تحديث Settlement Confirmation Modal": "- [x] تحديث Settlement Confirmation Modal",
    "- [ ] إضافة Form Validation": "- [x] إضافة Form Validation",
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated tasks")
