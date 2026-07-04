import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\core\views.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# For vendor_settlement
old_vendor_create = """                VendorSettlement.objects.create(
                    vendor_id=vendor_id,
                    amount_settled=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    payment_method=method,
                    settlement_status='COMPLETED'
                )"""

new_vendor_create = """                image = request.FILES.get('receipt_image')
                VendorSettlement.objects.create(
                    vendor_id=vendor_id,
                    amount_settled=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    payment_method=method,
                    settlement_status='COMPLETED',
                    receipt_image=image
                )"""

# For company_settlement
old_company_create = """                CompanySettlement.objects.create(
                    company_id=company_id,
                    settlement_amount=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    settlement_status='COMPLETED',
                    created_by=request.user
                )"""

new_company_create = """                image = request.FILES.get('receipt_image')
                CompanySettlement.objects.create(
                    company_id=company_id,
                    settlement_amount=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    settlement_status='COMPLETED',
                    created_by=request.user,
                    receipt_image=image
                )"""

# For delegate_settlement
old_delegate_create = """                DelegateSettlement.objects.create(
                    delegate_id=delegate_id,
                    company_id=company_id,
                    total_commission=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    settlement_status='COMPLETED',
                    created_by=request.user
                )"""

new_delegate_create = """                image = request.FILES.get('receipt_image')
                DelegateSettlement.objects.create(
                    delegate_id=delegate_id,
                    company_id=company_id,
                    total_commission=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    settlement_status='COMPLETED',
                    created_by=request.user,
                    receipt_image=image
                )"""

content = content.replace(old_vendor_create, new_vendor_create)
content = content.replace(old_company_create, new_company_create)
content = content.replace(old_delegate_create, new_delegate_create)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated core/views.py with image upload handling successfully.")
