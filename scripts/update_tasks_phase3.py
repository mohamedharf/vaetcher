import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\التسويات\TASKS_DETAILED.md"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace checkboxes for Phase 3
replacements = {
    "- [ ] البحث الفوري داخل الجداول بالاسم والكود": "- [x] البحث الفوري داخل الجداول بالاسم والكود",
    "- [ ] تصدير التقارير إلى Excel/CSV": "- [x] تصدير التقارير إلى Excel/CSV",
    "تصفية البيانات بناءً على التاريخ وحالة الدفع": "تصفية البيانات بناءً على التاريخ وحالة الدفع (من خلال محرك البحث المدمج والفلترة)",
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated tasks")
