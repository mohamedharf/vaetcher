import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\core\models.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# For CompanySettlement, find notes = models.TextField(_('Notes'), blank=True)
# and add receipt_image
comp_target = """    notes = models.TextField(_('Notes'), blank=True)"""
comp_replacement = """    notes = models.TextField(_('Notes'), blank=True)
    receipt_image = models.ImageField(_('Receipt Image'), upload_to='settlements/companies/', null=True, blank=True)"""

content = content.replace("class CompanySettlement(models.Model):", "# modified CompanySettlement")
content = content.replace(comp_target, comp_replacement, 1)
content = content.replace("# modified CompanySettlement", "class CompanySettlement(models.Model):")

# For DelegateSettlement
del_target = """    notes = models.TextField(_('Notes'), blank=True)"""
del_replacement = """    notes = models.TextField(_('Notes'), blank=True)
    receipt_image = models.ImageField(_('Receipt Image'), upload_to='settlements/delegates/', null=True, blank=True)"""

# To replace only inside DelegateSettlement, we'll locate it
content = content.replace("class DelegateSettlement(models.Model):", "# modified DelegateSettlement")
content = content.replace(del_target, del_replacement, 1)
content = content.replace("# modified DelegateSettlement", "class DelegateSettlement(models.Model):")

# For VendorSettlement
vend_target = """    notes = models.TextField(_('Notes'), blank=True)"""
vend_replacement = """    notes = models.TextField(_('Notes'), blank=True)
    receipt_image = models.ImageField(_('Receipt Image'), upload_to='settlements/vendors/', null=True, blank=True)"""

content = content.replace("class VendorSettlement(models.Model):", "# modified VendorSettlement")
content = content.replace(vend_target, vend_replacement, 1)
content = content.replace("# modified VendorSettlement", "class VendorSettlement(models.Model):")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated models.py with receipt_image fields")
