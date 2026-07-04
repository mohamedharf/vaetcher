from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    class Types(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        DOCTOR = 'DOCTOR', _('Doctor')
        VENDOR = 'VENDOR', _('Vendor')
        COMPANY = 'COMPANY', _('Company')
        DELEGATE = 'DELEGATE', _('Delegate')

    type = models.CharField(
        _('Type'), max_length=50, choices=Types.choices, default=Types.ADMIN
    )
    phone = models.CharField(_('Phone Number'), max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(_('email address'), unique=True, null=True, blank=True)

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        # 1. Clean email and phone fields (convert empty strings to None to satisfy the UNIQUE database constraint)
        if self.email == "":
            self.email = None
        elif self.email:
            self.email = self.email.strip()
            
        if self.phone == "":
            self.phone = None
        elif self.phone:
            self.phone = self.phone.strip()

        # 2. Enforce unique email across all users (excluding empty values)
        if self.email:
            qs = User.objects.filter(email__iexact=self.email)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValueError(_('البريد الإلكتروني مسجل بالفعل لمستخدم آخر في النظام.'))

        # 3. Enforce unique phone across all users (excluding empty values)
        if self.phone:
            qs = User.objects.filter(phone=self.phone)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValueError(_('رقم الهاتف مسجل بالفعل لمستخدم آخر في النظام.'))

        super().save(*args, **kwargs)

class Specialty(models.Model):
    name = models.CharField(_('Name'), max_length=100, unique=True)

    class Meta:
        verbose_name = _('Specialty')
        verbose_name_plural = _('Specialties')

    def __str__(self):
        return self.name

class Delegate(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='delegate_profile', verbose_name=_('User'), null=True, blank=True)
    name = models.CharField(_('Name'), max_length=255)
    phone = models.CharField(_('Phone'), max_length=20, unique=True)
    companies = models.ManyToManyField('core.PharmaceuticalCompany', blank=True, related_name='delegates', verbose_name=_('Companies'))
    specialties = models.ManyToManyField('accounts.Specialty', blank=True, related_name='delegates', verbose_name=_('Specialties'))
    is_deleted = models.BooleanField(default=False, verbose_name=_('Is Deleted'))

    class Meta:
        verbose_name = _('Delegate')
        verbose_name_plural = _('Delegates')

    def __str__(self):
        return self.name

    @property
    def clean_phone(self):
        if self.is_deleted and '_del_' in self.phone:
            return self.phone.split('_del_')[0]
        return self.phone

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile', verbose_name=_('User'))
    name = models.CharField(_('Name'), max_length=255)
    phone = models.CharField(_('Phone'), max_length=20, unique=True)
    email = models.EmailField(_('Email'), unique=True)
    specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Specialty'))
    qr_code = models.CharField(_('QR Code'), max_length=255, blank=True, null=True) # URL or path
    profile_picture = models.ImageField(_('Profile Picture'), upload_to='doctors/profiles/', null=True, blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    is_deleted = models.BooleanField(default=False, verbose_name=_('Is Deleted'))

    class Meta:
        verbose_name = _('Doctor')
        verbose_name_plural = _('Doctors')

    def __str__(self):
        return self.name

    @property
    def clean_phone(self):
        if self.is_deleted and '_del_' in self.phone:
            return self.phone.split('_del_')[0]
        return self.phone
        
    @property
    def clean_email(self):
        if self.is_deleted and self.email.startswith('del_'):
            parts = self.email.split('_', 2)
            if len(parts) == 3:
                return parts[2]
        return self.email

    def get_avatar_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return f"https://ui-avatars.com/api/?name={self.name.replace(' ', '+')}&background=005353&color=fff"

    def save(self, *args, **kwargs):
        if not self.qr_code:
            import uuid
            self.qr_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)
    
    def get_qr_code_url(self):
        """Generate the full URL for QR code scanning"""
        return f"/scan/{self.qr_code}/"

class Vendor(models.Model):
    class VendorRoles(models.TextChoices):
        ADMIN = 'ADMIN', _('Vendor Admin')
        CASHIER = 'CASHIER', _('Vendor Cashier')

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile', verbose_name=_('User'))
    name = models.CharField(_('Name'), max_length=255, unique=True)
    contact_person = models.CharField(_('Contact Person'), max_length=255)
    phone = models.CharField(_('Phone'), max_length=20)
    email = models.EmailField(_('Email'))
    address = models.TextField(_('Address'))
    category = models.CharField(_('Category'), max_length=100) # e.g. Supermarket, Restaurant
    role = models.CharField(
        _('Role'), max_length=20, choices=VendorRoles.choices, default=VendorRoles.ADMIN,
        help_text=_('Vendor Admin has full access, Cashier can only process transactions via QR scan')
    )
    parent_vendor = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, 
        related_name='cashiers_list', verbose_name=_('Parent Vendor'),
        help_text=_('If this is a cashier, specify the parent vendor it belongs to')
    )
    # Financial Information
    bank_info = models.TextField(_('Bank Account Info'), blank=True, null=True, help_text=_('Bank name, Account number, etc.'))
    wallet_info = models.TextField(_('Electronic Wallet Info'), blank=True, null=True, help_text=_('Vodafone Cash, etc.'))
    other_info = models.TextField(_('Other Financial Info'), blank=True, null=True)
    logo = models.ImageField(_('Vendor Logo'), upload_to='vendor_logos/', null=True, blank=True)
    
    management_fee_percentage = models.DecimalField(_('Management Fee Percentage'), max_digits=5, decimal_places=2, default=25.00)
    has_management_fee = models.BooleanField(_('Has Management Fee'), default=True)
    is_active = models.BooleanField(_('Is Active'), default=True)
    is_deleted = models.BooleanField(_('Is Deleted'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Vendor')
        verbose_name_plural = _('Vendors')

    def __str__(self):
        return self.name

    @property
    def clean_name(self):
        if self.is_deleted and '_del_' in self.name:
            return self.name.split('_del_')[0]
        return self.name
        
    @property
    def clean_phone(self):
        if self.is_deleted and '_del_' in self.phone:
            return self.phone.split('_del_')[0]
        return self.phone

    @property
    def clean_email(self):
        if self.is_deleted and self.email.startswith('del_'):
            parts = self.email.split('_', 2)
            if len(parts) == 3:
                return parts[2]
        return self.email
