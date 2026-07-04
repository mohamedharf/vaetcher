import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\core\models.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
current_class = None

for line in lines:
    new_lines.append(line)
    
    # Track class names
    if line.startswith("class "):
        current_class = line.split("(")[0].replace("class ", "").strip()
        
    # Insert receipt_image right after notes field in the specific classes
    if "notes = models.TextField" in line:
        if current_class == "VendorSettlement":
            new_lines.append("    receipt_image = models.ImageField(_('Receipt Image'), upload_to='settlements/vendors/', null=True, blank=True)\n")
            print("Added to VendorSettlement")
        elif current_class == "CompanySettlement":
            new_lines.append("    receipt_image = models.ImageField(_('Receipt Image'), upload_to='settlements/companies/', null=True, blank=True)\n")
            print("Added to CompanySettlement")
        elif current_class == "DelegateSettlement":
            new_lines.append("    receipt_image = models.ImageField(_('Receipt Image'), upload_to='settlements/delegates/', null=True, blank=True)\n")
            print("Added to DelegateSettlement")

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Finished robust update of models.py")
