import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\core\models.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# We'll completely replace VendorSettlement and Transaction
# And add CompanySettlement and DelegateSettlement

new_models = """from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.db.models import Sum

class PharmaceuticalCompany(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='company_profile', verbose_name=_('User'), null=True, blank=True)
    name = models.CharField(_('Name'), max_length=255, unique=True)
    contact_person = models.CharField(_('Contact Person'), max_length=255)
    phone = models.CharField(_('Phone'), max_length=20)
    email = models.EmailField(_('Email'))
    address = models.TextField(_('Address'))
    specialties = models.ManyToManyField('accounts.Specialty', related_name='companies', verbose_name=_('Specialties'), blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    is_deleted = models.BooleanField(default=False, verbose_name=_('Is Deleted'))

    class Meta:
        verbose_name = _('Pharmaceutical Company')
        verbose_name_plural = _('Pharmaceutical Companies')

    def __str__(self):
        return self.name

    @property
    def clean_name(self):
        if self.is_deleted and '_del_' in self.name:
            return self.name.split('_del_')[0]
        return self.name
        
    @property
    def clean_email(self):
        if self.is_deleted and self.email.startswith('del_'):
            parts = self.email.split('_', 2)
            if len(parts) == 3:
                return parts[2]
        return self.email

class CompanySettlement(models.Model):
    company = models.ForeignKey(
        'core.PharmaceuticalCompany',
        on_delete=models.CASCADE,
        related_name='settlements'
    )
    total_budget_allocated = models.DecimalField(_('Total Budget Allocated'), max_digits=12, decimal_places=2, default=0)
    total_vouchers_distributed = models.DecimalField(_('Total Vouchers Distributed'), max_digits=12, decimal_places=2, default=0)
    total_amount_spent = models.DecimalField(_('Total Amount Spent by Doctors'), max_digits=12, decimal_places=2, default=0)
    settlement_amount = models.DecimalField(_('Settlement Amount'), max_digits=12, decimal_places=2, default=0)
    settlement_date = models.DateField(_('Settlement Date'))
    settlement_status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('PENDING', 'معلق'),
            ('PARTIAL', 'تسوية جزئية'),
            ('COMPLETED', 'مكتمل'),
        ],
        default='PENDING'
    )
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='created_company_settlements',
        null=True, blank=True
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Company Settlement')
        verbose_name_plural = _('Company Settlements')
        ordering = ['-settlement_date']
        
    def get_unused_budget(self):
        return self.total_budget_allocated - self.total_vouchers_distributed

class DelegateSettlement(models.Model):
    delegate = models.ForeignKey(
        'accounts.Delegate',
        on_delete=models.CASCADE,
        related_name='settlements'
    )
    company = models.ForeignKey(
        'core.PharmaceuticalCompany',
        on_delete=models.CASCADE,
        related_name='delegate_settlements'
    )
    events_assigned = models.IntegerField(_('Events Assigned'), default=0)
    doctors_registered = models.IntegerField(_('Doctors Registered'), default=0)
    commission_rate = models.DecimalField(_('Commission Rate (%)'), max_digits=5, decimal_places=2, default=0)
    total_commission = models.DecimalField(_('Total Commission'), max_digits=12, decimal_places=2, default=0)
    settlement_date = models.DateField(_('Settlement Date'))
    settlement_status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('PENDING', 'معلق'),
            ('COMPLETED', 'مكتمل'),
            ('DISPUTED', 'محل نزاع'),
        ],
        default='PENDING'
    )
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='created_delegate_settlements',
        null=True, blank=True
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Delegate Settlement')
        verbose_name_plural = _('Delegate Settlements')
        ordering = ['-settlement_date']

class VendorSettlement(models.Model):
    vendor = models.ForeignKey('accounts.Vendor', on_delete=models.CASCADE, verbose_name=_('Vendor'))
    amount_settled = models.DecimalField(_('Amount Settled'), max_digits=12, decimal_places=2)
    admin_commission_amount = models.DecimalField(_('Admin Commission Amount'), max_digits=12, decimal_places=2, default=0)
    net_amount_to_vendor = models.DecimalField(_('Net Amount to Vendor'), max_digits=12, decimal_places=2, default=0)
    settlement_date = models.DateField(_('Settlement Date'))
    settlement_status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('PENDING', 'معلق'),
            ('COMPLETED', 'مكتمل'),
            ('FAILED', 'فشل'),
        ],
        default='PENDING'
    )
    payment_method = models.CharField(
        _('Payment Method'),
        max_length=50,
        choices=[
            ('BANK', 'تحويل بنكي'),
            ('CASH', 'نقدي'),
            ('CHECK', 'شيك'),
        ],
        blank=True
    )
    transactions = models.ManyToManyField(
        'core.Transaction',
        blank=True,
        related_name='vendor_settlement_many',
        verbose_name=_('Transactions Settled')
    )
    notes = models.TextField(_('Notes'), blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Vendor Settlement')
        verbose_name_plural = _('Vendor Settlements')

    def calculate_admin_commission(self):
        total_commission = self.transactions.aggregate(Sum('management_fee_amount'))['management_fee_amount__sum'] or 0
        return Decimal(total_commission)

    def calculate_net_amount(self):
        total_spent = self.transactions.aggregate(Sum('amount_spent'))['amount_spent__sum'] or 0
        return Decimal(total_spent)

    def clean(self):
        super().clean()
        if self.vendor and self.amount_settled:
            from django.db.models import Sum, Q
            from accounts.models import Vendor
            from core.models import Transaction, VendorSettlement
            
            vendors = Vendor.objects.filter(Q(id=self.vendor.id) | Q(parent_vendor=self.vendor))
            total_sales = Transaction.objects.filter(vendor__in=vendors).aggregate(total=Sum('total_deducted'))['total'] or 0
            
            qs = VendorSettlement.objects.filter(vendor__in=vendors)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            total_settlements = qs.aggregate(total=Sum('amount_settled'))['total'] or 0
            
            available_balance = total_sales - total_settlements
            
            if self.amount_settled > available_balance:
                from django.core.exceptions import ValidationError
                raise ValidationError({"amount_settled": f"رصيد المتاح للتاجر لا يكفي. الرصيد المتاح هو {available_balance} ج.م"})

    def __str__(self):
        return f"{self.vendor} - {self.amount_settled} - {self.settlement_date}"

class Transaction(models.Model):
    vouchers = models.ManyToManyField('events.Voucher', related_name='transactions', verbose_name=_('Vouchers'))
    vendor = models.ForeignKey('accounts.Vendor', on_delete=models.PROTECT, verbose_name=_('Vendor'))
    doctor = models.ForeignKey('accounts.Doctor', on_delete=models.PROTECT, verbose_name=_('Doctor'))
    created_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, verbose_name=_('Created By'), related_name='transactions_created', null=True, blank=True)
    amount_spent = models.DecimalField(_('Amount Spent'), max_digits=10, decimal_places=2)
    management_fee_percentage = models.DecimalField(_('Management Fee Percentage'), max_digits=5, decimal_places=2, default=25.00)
    management_fee_amount = models.DecimalField(_('Management Fee Amount'), max_digits=10, decimal_places=2)
    total_deducted = models.DecimalField(_('Total Deducted'), max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(_('Transaction Date'), auto_now_add=True)
    items_description = models.TextField(_('Items Description'), blank=True)
    invoice_number = models.CharField(_('Invoice Number'), max_length=100, unique=True)
    
    # Old link kept for backward compatibility if needed, but many-to-many is added in VendorSettlement
    settlement = models.ForeignKey(
        VendorSettlement, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transactions_legacy',
        verbose_name=_('Settlement')
    )

    class Meta:
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')

    def __str__(self):
        return f"{self.invoice_number} - {self.doctor} at {self.vendor}"
"""

with open(filepath, "w", encoding="utf-8") as f:
    f.write(new_models)
print("Updated models.py")
