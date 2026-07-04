import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\core\models.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update CompanySettlement
company_target = """    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='created_company_settlements',"""

company_replacement = """    notes = models.TextField(_('Notes'), blank=True)
    receipt_image = models.ImageField(_('Receipt Image'), upload_to='settlements/companies/', null=True, blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='created_company_settlements',"""

content = content.replace(company_target, company_replacement)

# 2. Update DelegateSettlement
delegate_target = """    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='created_delegate_settlements',"""

delegate_replacement = """    notes = models.TextField(_('Notes'), blank=True)
    receipt_image = models.ImageField(_('Receipt Image'), upload_to='settlements/delegates/', null=True, blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='created_delegate_settlements',"""

content = content.replace(delegate_target, delegate_replacement)

# 3. Update VendorSettlement
vendor_target = """    notes = models.TextField(_('Notes'), blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Vendor Settlement')"""

vendor_replacement = """    notes = models.TextField(_('Notes'), blank=True)
    receipt_image = models.ImageField(_('Receipt Image'), upload_to='settlements/vendors/', null=True, blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Vendor Settlement')"""

content = content.replace(vendor_target, vendor_replacement)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated models.py with receipt_image fields successfully.")
