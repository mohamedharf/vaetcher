from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
from decimal import Decimal
from accounts.models import Vendor, Doctor
from events.models import Voucher
from .models import Transaction
import random
import string
import threading
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
#  SHARED ASYNC EMAIL UTILITY
# ─────────────────────────────────────────────────────────────

def send_email_async(subject, template_name, context, recipient_email, fail_silently=True):
    """
    Shared utility: renders an HTML email template and sends it asynchronously
    using a background thread so it never blocks the main request.
    Falls back to plain-text if rendering fails.
    """
    def _send():
        from core.models import EmailLog
        from accounts.models import Vendor
        from django.db import connection
        try:
            if 'global_system_vendor' not in context:
                try:
                    context['global_system_vendor'] = Vendor.objects.filter(role='ADMIN', is_deleted=False).order_by('id').first()
                except Exception:
                    pass
            
            html_content = render_to_string(template_name, context)
            plain_text = subject
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=fail_silently)
            
            # Log success
            EmailLog.objects.create(
                recipient=recipient_email, 
                subject=subject, 
                template_used=template_name, 
                status='SUCCESS'
            )
        except Exception as e:
            logger.error(f"[send_email_async] Failed to send '{subject}' to {recipient_email}: {e}")
            # Log failure
            EmailLog.objects.create(
                recipient=recipient_email, 
                subject=subject, 
                template_used=template_name, 
                status='FAILED',
                error_message=str(e)
            )
        finally:
            connection.close()

    threading.Thread(target=_send, daemon=True).start()


def generate_otp():
    """Generates a 6-digit numeric OTP."""
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(doctor, otp, amount, vendor_name):
    """Sends OTP to doctor's email (async, HTML template) and stores it in cache."""
    import uuid
    transaction_token = str(uuid.uuid4())

    # Store OTP data in cache first
    cache_data = {
        'otp': otp,
        'doctor_id': doctor.id,
        'amount': amount,
        'attempts': 0
    }
    cache.set(f"otp_token_{transaction_token}", cache_data, timeout=600)

    if not doctor.email:
        return transaction_token  # no email, but token still stored

    context = {
        'doctor_name': doctor.name,
        'otp': otp,
        'amount': amount,
        'vendor_name': vendor_name,
        'is_transfer': False,
    }
    send_email_async(
        subject="رمز تأكيد عملية الخصم - نظام حضرموت",
        template_name="emails/otp_email.html",
        context=context,
        recipient_email=doctor.email,
    )
    return transaction_token


def send_transfer_otp_email(from_doctor, to_doctor, voucher, otp):
    """Sends OTP to the RECIPIENT doctor's email for transfer confirmation (async, HTML)."""
    import uuid
    transaction_token = str(uuid.uuid4())

    # Store OTP data in cache first
    cache_data = {
        'otp': otp,
        'from_doctor_id': from_doctor.id,
        'to_doctor_id': to_doctor.id,
        'voucher_id': voucher.id,
        'attempts': 0
    }
    cache.set(f"transfer_otp_{transaction_token}", cache_data, timeout=600)

    if not to_doctor.email:
        return transaction_token

    context = {
        'doctor_name': to_doctor.name,
        'otp': otp,
        'from_doctor': from_doctor.name,
        'amount': voucher.current_balance,
        'is_transfer': True,
    }
    send_email_async(
        subject="رمز تأكيد استلام قسيمة - نظام حضرموت",
        template_name="emails/otp_email.html",
        context=context,
        recipient_email=to_doctor.email,
    )
    return transaction_token

def verify_otp(token, input_otp):
    """Verifies OTP and tracks failed attempts."""
    cache_key = f"otp_token_{token}"
    data = cache.get(cache_key)
    
    if not data:
        return False, "انتهت صلاحية الرمز أو أنه غير صالح."
        
    if data['attempts'] >= 5:
        cache.delete(cache_key)
        return False, "لقد تجاوزت الحد الأقصى للمحاولات (5). يرجى طلب رمز جديد."
        
    if data['otp'] == input_otp:
        return True, data
        
    # Increment attempts
    data['attempts'] += 1
    cache.set(cache_key, data, timeout=600)
    
    remaining = 5 - data['attempts']
    if remaining > 0:
        return False, f"رمز غير صحيح. متبقي لديك {remaining} محاولات."
    else:
        cache.delete(cache_key)
        return False, "لقد تجاوزت الحد الأقصى للمحاولات. يرجى طلب رمز جديد."

def process_transaction(vendor, doctor, amount_spent, items_description="", created_by=None):
    """
    Processes a transaction for a doctor at a vendor.
    Deducts the total amount (spent + fee) from the doctor's active vouchers.
    """
    amount_spent = Decimal(amount_spent)
    
    # Use parent vendor's settings if this is a cashier
    effective_vendor = vendor
    if vendor.role == 'CASHIER' and vendor.parent_vendor:
        effective_vendor = vendor.parent_vendor

    # Check if vendor has management fee enabled
    management_fee_percentage = (effective_vendor.management_fee_percentage / Decimal("100.00")) if effective_vendor.has_management_fee else Decimal("0.00")
    management_fee_amount = amount_spent * management_fee_percentage
    total_deducted = amount_spent + management_fee_amount

    # Get active vouchers
    active_vouchers = Voucher.objects.filter(
        doctor=doctor, 
        is_active=True, 
        current_balance__gt=0
    ).order_by('expiry_date')

    total_balance = sum(v.current_balance for v in active_vouchers)

    if total_balance < total_deducted:
        raise ValidationError(f"Insufficient balance. Available: {total_balance}, Required: {total_deducted}")

    remaining_to_deduct = total_deducted
    used_vouchers = []
    
    with transaction.atomic():
        for voucher in active_vouchers:
            if remaining_to_deduct <= 0:
                break
            
            used_vouchers.append(voucher)

            if voucher.current_balance >= remaining_to_deduct:
                voucher.current_balance -= remaining_to_deduct
                remaining_to_deduct = 0
                if voucher.current_balance == 0:
                    voucher.is_active = False
            else:
                deduction = voucher.current_balance
                remaining_to_deduct -= deduction
                voucher.current_balance = 0
                voucher.is_active = False
            
            voucher.save()

        # Create Transaction record
        import uuid
        trx = Transaction.objects.create(
            vendor=effective_vendor,
            doctor=doctor,
            created_by=created_by,
            amount_spent=amount_spent,
            management_fee_percentage=management_fee_percentage * 100,
            management_fee_amount=management_fee_amount,
            total_deducted=total_deducted,
            items_description=items_description,
            invoice_number=str(uuid.uuid4())
        )
        trx.vouchers.set(used_vouchers)
        
        # Clear OTP from cache after successful transaction
        cache.delete(f"otp_token_{created_by.id if created_by else 'anon'}") # This was a cleanup placeholder, actual cleanup is by token

        # ── إشعار داخلي للإدارة عند إتمام معاملة بيع ──
        try:
            from .models import Notification
            from accounts.models import User as UserModel
            admin_users = UserModel.objects.filter(is_staff=True, is_active=True)
            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    message=f"تم تسجيل معاملة بيع بقيمة {amount_spent} ج.م للدكتور {doctor.name} في متجر {effective_vendor.name}.",
                    notification_type='SETTLEMENT',
                    link='/custom-settlements/'
                )
        except Exception:
            pass

        return trx
