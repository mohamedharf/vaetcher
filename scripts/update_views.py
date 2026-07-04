import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\core\views.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# We need to find `class CustomVendorSettlementsView(LoginRequiredMixin, VendorAdminRequiredMixin, TemplateView):`
# and its content, and replace it.

old_class = """class CustomVendorSettlementsView(LoginRequiredMixin, VendorAdminRequiredMixin, TemplateView):
    template_name = 'custom_admin/vendor_settlements.html'"""

new_class = """class CustomVendorSettlementsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'custom_admin/vendor_settlements.html'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.models import VendorSettlement, CompanySettlement, DelegateSettlement, Transaction
        from accounts.models import Vendor
        from django.db.models import Sum
        from decimal import Decimal
        
        # Vendor Metrics
        total_sales_all = Transaction.objects.aggregate(total=Sum('amount_spent'))['total'] or Decimal('0.00')
        total_settled_all = VendorSettlement.objects.filter(settlement_status='COMPLETED').aggregate(total=Sum('amount_settled'))['total'] or Decimal('0.00')
        context['pending_vendor_debts'] = total_sales_all - total_settled_all
        context['expected_admin_fees'] = Transaction.objects.aggregate(total=Sum('management_fee_amount'))['total'] or Decimal('0.00')
        
        # Lists
        context['vendor_settlements'] = VendorSettlement.objects.all().order_by('-settlement_date')
        context['company_settlements'] = CompanySettlement.objects.all().order_by('-settlement_date')
        context['delegate_settlements'] = DelegateSettlement.objects.all().order_by('-settlement_date')
        
        # We need pending vendors list with their stats
        vendors = Vendor.objects.filter(parent_vendor__isnull=True)
        pending_vendors = []
        for v in vendors:
            # aggregate transactions and settlements for v and its branches
            v_family = Vendor.objects.filter(models.Q(id=v.id) | models.Q(parent_vendor=v))
            v_sales = Transaction.objects.filter(vendor__in=v_family).aggregate(t=Sum('amount_spent'))['t'] or Decimal('0.00')
            v_settled = VendorSettlement.objects.filter(vendor__in=v_family, settlement_status='COMPLETED').aggregate(t=Sum('amount_settled'))['t'] or Decimal('0.00')
            v_invoices = Transaction.objects.filter(vendor__in=v_family).count()
            v_debt = v_sales - v_settled
            if v_debt > 0:
                pending_vendors.append({
                    'vendor': v,
                    'debt': v_debt,
                    'invoices_count': v_invoices
                })
        context['pending_vendors'] = pending_vendors
        
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        from django.contrib import messages
        from core.models import VendorSettlement, CompanySettlement, DelegateSettlement
        from decimal import Decimal
        import datetime
        
        if action == 'vendor_settlement':
            vendor_id = request.POST.get('vendor_id')
            amount = request.POST.get('amount')
            date_str = request.POST.get('date', datetime.date.today())
            notes = request.POST.get('notes', '')
            method = request.POST.get('payment_method', 'CASH')
            try:
                VendorSettlement.objects.create(
                    vendor_id=vendor_id,
                    amount_settled=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    payment_method=method,
                    settlement_status='COMPLETED'
                )
                messages.success(request, "تم إصدار تسوية المورد بنجاح وتصفير المديونية المحددة.")
            except Exception as e:
                messages.error(request, f"حدث خطأ: {e}")
                
        elif action == 'company_settlement':
            company_id = request.POST.get('company_id')
            amount = request.POST.get('amount')
            date_str = request.POST.get('date', datetime.date.today())
            notes = request.POST.get('notes', '')
            try:
                CompanySettlement.objects.create(
                    company_id=company_id,
                    settlement_amount=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    settlement_status='COMPLETED',
                    created_by=request.user
                )
                messages.success(request, "تم إصدار تسوية الشركة بنجاح.")
            except Exception as e:
                messages.error(request, f"حدث خطأ: {e}")
                
        elif action == 'delegate_settlement':
            delegate_id = request.POST.get('delegate_id')
            company_id = request.POST.get('company_id')
            amount = request.POST.get('amount')
            date_str = request.POST.get('date', datetime.date.today())
            notes = request.POST.get('notes', '')
            try:
                DelegateSettlement.objects.create(
                    delegate_id=delegate_id,
                    company_id=company_id,
                    total_commission=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    settlement_status='COMPLETED',
                    created_by=request.user
                )
                messages.success(request, "تم إصدار تسوية المندوب بنجاح.")
            except Exception as e:
                messages.error(request, f"حدث خطأ: {e}")

        return self.get(request, *args, **kwargs)"""

if old_class in content:
    content = content.replace(old_class, new_class)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated core/views.py successfully.")
else:
    print("Error: Could not find the class to replace in core/views.py")
