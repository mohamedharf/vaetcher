from django.db import models
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Event(models.Model):
    class PaymentTypes(models.TextChoices):
        CASH = 'CASH', _('Cash')
        DEFERRED = 'DEFERRED', _('Deferred')

    name = models.CharField(_('Name'), max_length=255)
    date = models.DateField(_('Event Date'))
    company = models.ForeignKey('core.PharmaceuticalCompany', on_delete=models.CASCADE, related_name='events', verbose_name=_('Company'), null=True, blank=True)
    payment_type = models.CharField(_('Payment Type'), max_length=10, choices=PaymentTypes.choices, default=PaymentTypes.DEFERRED)
    voucher_value = models.DecimalField(_('Voucher Value'), max_digits=10, decimal_places=2)
    voucher_expiry_days = models.IntegerField(_('Voucher Expiry Days'), default=90)
    max_budget = models.DecimalField(_('Max Budget'), max_digits=12, decimal_places=2, default=0.00)
    doctors = models.ManyToManyField('accounts.Doctor', related_name='events', blank=True, verbose_name=_('Doctors'))
    delegates = models.ManyToManyField('accounts.Delegate', related_name='events', blank=True, verbose_name=_('Delegates'))
    specialties = models.ManyToManyField('accounts.Specialty', related_name='events', blank=True, verbose_name=_('Specialties'))
    notes = models.TextField(_('Notes'), blank=True, null=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Event')
        verbose_name_plural = _('Events')

    def __str__(self):
        return f"{self.name} - {self.date}"

class Voucher(models.Model):
    doctor = models.ForeignKey('accounts.Doctor', on_delete=models.CASCADE, related_name='vouchers', verbose_name=_('Doctor'))
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='vouchers', verbose_name=_('Event'), null=True, blank=True)
    company = models.ForeignKey('core.PharmaceuticalCompany', on_delete=models.SET_NULL, verbose_name=_('Company'), null=True, blank=True)
    initial_value = models.DecimalField(_('Initial Value'), max_digits=10, decimal_places=2)
    current_balance = models.DecimalField(_('Current Balance'), max_digits=10, decimal_places=2)
    issue_date = models.DateField(_('Issue Date'), auto_now_add=True)
    expiry_date = models.DateField(_('Expiry Date'))
    is_active = models.BooleanField(_('Is Active'), default=True)
    notes = models.TextField(_('Notes'), blank=True, null=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Voucher')
        verbose_name_plural = _('Vouchers')

    def __str__(self):
        if self.event:
            return f"Voucher for {self.doctor} - {self.event.name}"
        else:
            return f"Voucher for {self.doctor}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.expiry_date:
            if self.event:
                 self.expiry_date = timezone.now().date() + timedelta(days=self.event.voucher_expiry_days)
            else:
                 # Default expiry for custom vouchers if no event is specified
                 self.expiry_date = timezone.now().date() + timedelta(days=90)
        super().save(*args, **kwargs)

    @property
    def consumed_amount(self):
        return self.initial_value - self.current_balance

class VoucherTransfer(models.Model):
    from_doctor = models.ForeignKey('accounts.Doctor', on_delete=models.CASCADE, related_name='transfers_made', verbose_name=_('From Doctor'))
    to_doctor = models.ForeignKey('accounts.Doctor', on_delete=models.CASCADE, related_name='transfers_received', verbose_name=_('To Doctor'))
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='transfers', verbose_name=_('Voucher'))
    transfer_date = models.DateTimeField(_('Transfer Date'), auto_now_add=True)

    class Meta:
        verbose_name = _('Voucher Transfer')
        verbose_name_plural = _('Voucher Transfers')

    def __str__(self):
        return f"{self.from_doctor.name} -> {self.to_doctor.name}"

class EventRequest(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')

    requester_user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='event_requests', verbose_name=_('Requester User'))
    company = models.ForeignKey('core.PharmaceuticalCompany', on_delete=models.CASCADE, related_name='event_requests', null=True, blank=True, verbose_name=_('Company'))
    delegate = models.ForeignKey('accounts.Delegate', on_delete=models.CASCADE, related_name='event_requests', null=True, blank=True, verbose_name=_('Delegate'))
    
    name = models.CharField(_('Event Name'), max_length=255)
    date = models.DateField(_('Event Date'))
    voucher_value = models.DecimalField(_('Voucher Value'), max_digits=10, decimal_places=2)
    max_budget = models.DecimalField(_('Max Budget'), max_digits=12, decimal_places=2, default=0.00)
    notes = models.TextField(_('Notes'), blank=True, null=True)
    
    status = models.CharField(_('Status'), max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Event Request')
        verbose_name_plural = _('Event Requests')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"


class EventRequestDoctor(models.Model):
    event_request = models.ForeignKey(EventRequest, on_delete=models.CASCADE, related_name='requested_doctors', verbose_name=_('Event Request'))
    
    # If the doctor already exists
    existing_doctor = models.ForeignKey('accounts.Doctor', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Existing Doctor'))
    
    # If the doctor does not exist yet
    name = models.CharField(_('Name'), max_length=255, blank=True, null=True)
    phone = models.CharField(_('Phone'), max_length=20, blank=True, null=True)
    email = models.EmailField(_('Email'), blank=True, null=True)
    specialty_name = models.CharField(_('Specialty'), max_length=100, blank=True, null=True)
    
    is_created = models.BooleanField(_('Is Account Created'), default=False)
    
    class Meta:
        verbose_name = _('Event Request Doctor')
        verbose_name_plural = _('Event Request Doctors')

    def __str__(self):
        if self.existing_doctor:
            return f"{self.existing_doctor.name} (Existing)"
        return f"{self.name} (New)"
