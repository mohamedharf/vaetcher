from django.shortcuts import render
from django.contrib import messages
from core.services import send_email_async
from unfold.decorators import action
import string
import random

class EmailActionsMixin:
    actions = ['resend_credentials_action', 'send_custom_email_action']

    @action(description="إعادة تعيين وإرسال بيانات الدخول")
    def resend_credentials_action(self, request, queryset):
        count = 0
        for obj in queryset:
            # Try to get the User object (obj might be User, Doctor, Vendor, etc.)
            user = obj if hasattr(obj, 'set_password') else getattr(obj, 'user', None)
            
            if not user or not getattr(user, 'email', None):
                name = getattr(obj, 'username', getattr(obj, 'name', str(obj)))
                messages.warning(request, f"لا يوجد حساب أو بريد إلكتروني مرتبط بـ {name}")
                continue
                
            new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            user.set_password(new_password)
            user.save()
            
            site_url = request.build_absolute_uri('/')
            send_email_async(
                subject='تم إعادة تعيين بيانات حسابك في نظام حضرموت',
                template_name='emails/account_credentials.html',
                context={
                    'full_name': user.get_full_name() or user.username,
                    'username': user.username,
                    'email': user.email,
                    'phone': user.phone,
                    'password': new_password,
                    'site_url': site_url,
                },
                recipient_email=user.email,
            )
            count += 1
            
        if count > 0:
            messages.success(request, f"تم إعادة تعيين وإرسال كلمة مرور جديدة لـ {count} مستخدم.")

    @action(description="إرسال إيميل مخصص للمحددين")
    def send_custom_email_action(self, request, queryset):
        if 'send_email_btn' in request.POST:
            subject = request.POST.get('subject')
            message = request.POST.get('message')
            
            count = 0
            for obj in queryset:
                user = obj if hasattr(obj, 'set_password') else getattr(obj, 'user', None)
                if user and getattr(user, 'email', None):
                    send_email_async(
                        subject=subject,
                        template_name='emails/custom_message_email.html',
                        context={
                            'subject': subject,
                            'message': message,
                            'user_name': user.get_full_name() or user.username
                        },
                        recipient_email=user.email,
                    )
                    count += 1
            
            messages.success(request, f"تم إرسال الإيميل المخصص لـ {count} مستخدم.")
            return None # Returns to changelist

        return render(request, 'admin/send_custom_email.html', context={
            'queryset': queryset,
            'action_name': 'send_custom_email_action',
            'opts': self.model._meta
        })
