import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\core\views.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Fix the import
content = content.replace("from django.db.models import Sum", "from django.db.models import Sum, Q")

# Fix the usage
content = content.replace("models.Q(id=v.id) | models.Q(parent_vendor=v)", "Q(id=v.id) | Q(parent_vendor=v)")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed models.Q in core/views.py")
