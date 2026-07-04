from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Event, Voucher
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@receiver(m2m_changed, sender=Event.doctors.through)
def create_vouchers_for_doctors(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action == "post_add":
        # instance is the Event object
        # pk_set contains the primary keys of the added doctors
        for doctor_id in pk_set:
            # Check if voucher already exists to avoid duplicates
            if not Voucher.objects.filter(event=instance, doctor_id=doctor_id).exists():
                Voucher.objects.create(
                    event=instance,
                    doctor_id=doctor_id,
                    initial_value=instance.voucher_value,
                    current_balance=instance.voucher_value,
                    # expiry_date will be calculated by Voucher.save()
                )

@receiver(post_save, sender=Voucher)
def send_voucher_notification(sender, instance, created, **kwargs):
    if created:
        doctor = instance.doctor

        # ── 1. إنشاء إشعار داخلي للإدارة ──
        try:
            from core.models import Notification
            from accounts.models import User
            company_name = "غير محددة"
            if instance.company:
                company_name = instance.company.name
            elif instance.event and instance.event.company:
                company_name = instance.event.company.name

            admin_users = User.objects.filter(is_staff=True, is_active=True)
            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    message=f"تم إصدار قسيمة جديدة بقيمة {instance.initial_value} ج.م للدكتور {doctor.name} من شركة {company_name}.",
                    notification_type='VOUCHER',
                    link='/custom-events/'
                )
        except Exception as e:
            logger.error(f"Failed to create voucher notification: {e}")

        # ── 2. إرسال إيميل HTML احترافي للطبيب (غير متزامن) ──
        if not doctor.email:
            return

        company_name = "غير محددة"
        if instance.company:
            company_name = instance.company.name
        elif instance.event and instance.event.company:
            company_name = instance.event.company.name

        event_name = instance.event.name if instance.event else None
        validity_days = (instance.expiry_date - instance.issue_date).days

        try:
            from core.services import send_email_async
            send_email_async(
                subject="تم إضافة قسيمة شراء جديدة - نظام حضرموت",
                template_name="emails/voucher_notification.html",
                context={
                    'doctor_name': doctor.name,
                    'voucher_value': instance.initial_value,
                    'company_name': company_name,
                    'event_name': event_name,
                    'issue_date': instance.issue_date,
                    'expiry_date': instance.expiry_date,
                    'validity_days': validity_days,
                },
                recipient_email=doctor.email,
            )
        except Exception as e:
            logger.error(f"Failed to send voucher email to {doctor.email}: {e}")

