import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\core\admin.py"

content = """from django.contrib import admin
from .models import PharmaceuticalCompany, Transaction, VendorSettlement, CompanySettlement, DelegateSettlement
from unfold.admin import ModelAdmin, TabularInline
from accounts.models import Delegate
from django.utils.translation import gettext_lazy as _

class DelegateInline(TabularInline):
    model = Delegate.companies.through
    extra = 1
    verbose_name = _('Delegate')
    verbose_name_plural = _('Delegates')
    tab = True

class EventRelatedViewPermissionMixin:
    def has_view_permission(self, request, obj=None):
        if super().has_view_permission(request, obj):
            return True
        return request.user.has_perm('events.add_event') or request.user.has_perm('events.change_event')

@admin.register(PharmaceuticalCompany)
class PharmaceuticalCompanyAdmin(EventRelatedViewPermissionMixin, ModelAdmin):
    list_display = ('name', 'contact_person', 'phone')
    search_fields = ('name',)
    inlines = [DelegateInline]

@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ('invoice_number', 'doctor', 'vendor', 'amount_spent', 'total_deducted', 'transaction_date')
    list_filter = ('transaction_date', 'vendor')
    search_fields = ('invoice_number', 'doctor__name', 'vendor__name')
    autocomplete_fields = ('doctor', 'vendor', 'vouchers')
    readonly_fields = ('transaction_date', 'invoice_number')

@admin.register(VendorSettlement)
class VendorSettlementAdmin(ModelAdmin):
    list_display = ('vendor', 'amount_settled', 'admin_commission_amount', 'net_amount_to_vendor', 'settlement_status', 'settlement_date')
    list_filter = ('settlement_status', 'settlement_date', 'vendor')
    search_fields = ('vendor__name',)
    autocomplete_fields = ('vendor',)
    filter_horizontal = ('transactions',)

@admin.register(CompanySettlement)
class CompanySettlementAdmin(ModelAdmin):
    list_display = ('company', 'total_budget_allocated', 'total_vouchers_distributed', 'total_amount_spent', 'settlement_amount', 'settlement_status', 'settlement_date')
    list_filter = ('settlement_status', 'settlement_date', 'company')
    search_fields = ('company__name',)
    autocomplete_fields = ('company', 'created_by')

@admin.register(DelegateSettlement)
class DelegateSettlementAdmin(ModelAdmin):
    list_display = ('delegate', 'company', 'events_assigned', 'doctors_registered', 'total_commission', 'settlement_status', 'settlement_date')
    list_filter = ('settlement_status', 'settlement_date', 'company')
    search_fields = ('delegate__name', 'company__name')
    autocomplete_fields = ('delegate', 'company', 'created_by')
"""

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated admin.py")
