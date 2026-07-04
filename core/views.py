from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.views.generic import TemplateView, View, DetailView, CreateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q, Q, Count
from accounts.models import Doctor, Vendor, User, Delegate, Specialty
from accounts.utils import generate_doctor_card_pdf
from core.models import Transaction, VendorSettlement, PharmaceuticalCompany
from core.services import process_transaction, generate_otp, send_otp_email, verify_otp
from events.models import Voucher, VoucherTransfer, Event, EventRequest, EventRequestDoctor
from django.core.exceptions import ValidationError, PermissionDenied
from django.urls import reverse_lazy, reverse
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.hashers import make_password
from decimal import Decimal
import re
import uuid
import datetime
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

class AdminCompanyDelegatesView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        company_id = request.GET.get('company_id')
        delegates = Delegate.objects.all().prefetch_related('companies')
        
        data = []
        for d in delegates:
            is_general = d.companies.count() == 0
            is_company = False
            if company_id and str(company_id).isdigit():
                is_company = d.companies.filter(id=company_id).exists()
            
            cat = 'من شركات أخرى'
            if is_company:
                cat = 'تابع للشركة'
            elif is_general:
                cat = 'عام (بدون شركة)'
                
            data.append({
                'id': d.id,
                'name': f"{d.name} [{cat}]",
                'is_company': is_company,
                'is_general': is_general
            })
            
        return JsonResponse({'delegates': data})

class AdminDelegateSpecialtiesView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        delegate_ids = request.GET.getlist('delegate_ids[]')
        if not delegate_ids:
            return JsonResponse({'specialty_ids': []})
            
        specialties = Specialty.objects.filter(delegates__id__in=delegate_ids).distinct()
        data = [s.id for s in specialties]
        return JsonResponse({'specialty_ids': data})

class AdminCompanyDelegatesView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        company_id = request.GET.get('company_id')
        term = request.GET.get('term', '')
        
        delegates = Delegate.objects.all().prefetch_related('companies')
        if term:
            delegates = delegates.filter(Q(name__icontains=term) | Q(phone__icontains=term))
            
        delegates = delegates[:50]
        
        company_delegates = []
        general_delegates = []
        other_delegates = []
        
        for d in delegates:
            is_general = d.companies.count() == 0
            is_company = False
            if company_id and str(company_id).isdigit():
                is_company = d.companies.filter(id=company_id).exists()
            
            item = {'id': str(d.id), 'text': d.name}
            
            if is_company:
                company_delegates.append(item)
            elif is_general:
                general_delegates.append(item)
            else:
                other_delegates.append(item)
                
        results = []
        if company_delegates:
            results.append({
                'text': 'تابع للشركة',
                'children': company_delegates
            })
        if general_delegates:
            results.append({
                'text': 'عام (بدون شركة)',
                'children': general_delegates
            })
        if other_delegates:
            results.append({
                'text': 'من شركات أخرى',
                'children': other_delegates
            })
            
        return JsonResponse({
            'results': results,
            'pagination': {'more': False}
        })

class AdminDelegateSpecialtiesView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        delegate_ids = request.GET.getlist('delegate_ids[]')
        if not delegate_ids:
            return JsonResponse({'specialties': []})
            
        specialties = Specialty.objects.filter(delegates__id__in=delegate_ids).distinct()
        data = [{'id': s.id, 'text': s.name} for s in specialties]
        return JsonResponse({'specialties': data})

class HomeView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        
        user = request.user
        if user.is_superuser or user.is_staff:
            return redirect('custom_dashboard')
        elif user.type == 'VENDOR' or hasattr(user, 'vendor_profile'):
            return redirect('custom_vendor_portal')
        elif user.type == 'DOCTOR' or hasattr(user, 'doctor_profile'):
            return redirect('custom_doctor_portal')
        elif user.type == 'COMPANY' or hasattr(user, 'company_profile'):
            return redirect('custom_company_portal')
        elif user.type == 'DELEGATE' or hasattr(user, 'delegate_profile'):
            return redirect('custom_delegate_portal')
        
        return redirect('/admin/')


class CompanyPortalRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('custom_login')
        if not hasattr(request.user, 'company_profile'):
            messages.error(request, _("هذه الصفحة مخصصة للشركات الراعية فقط."))
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


class DelegatePortalRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('custom_login')
        if not hasattr(request.user, 'delegate_profile'):
            messages.error(request, _("هذه الصفحة مخصصة للمناديب التنفيذيين فقط."))
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


class CustomCompanyPortalView(CompanyPortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/company_portal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add notifications data
        if user.is_authenticated:
            from core.models import Notification
            unread_notifications = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')
            recent_notifications = Notification.objects.filter(user=user).order_by('-created_at')[:5]
            
            context['unread_notifications_count'] = unread_notifications.count()
            context['recent_notifications'] = recent_notifications
        
        # Get company profile linked to the user
        company_profile = getattr(user, 'company_profile', None)
        
        if company_profile:
            # Fetch events sponsored by this company
            events = Event.objects.filter(company=company_profile).order_by('-date')
            
            # Fetch vouchers sponsored by this company
            vouchers = Voucher.objects.filter(company=company_profile).select_related('doctor', 'event').order_by('-issue_date')
            
            # Calculate stats
            total_budget = Decimal('0.00')
            total_distributed = Decimal('0.00')
            total_balance = Decimal('0.00')
            
            for event in events:
                total_budget += event.max_budget
                
                # Stats per event
                v_stats = Voucher.objects.filter(event=event).aggregate(
                    initial=Sum('initial_value'),
                    balance=Sum('current_balance'),
                    count=Count('id')
                )
                event.total_vouchers = v_stats['count'] or 0
                event.total_initial = v_stats['initial'] or Decimal('0.00')
                total_bal = v_stats['balance'] or Decimal('0.00')
                event.total_spent = event.total_initial - total_bal
                
                total_distributed += event.total_initial
                total_balance += total_bal
                
                if event.max_budget and event.max_budget > 0:
                    event.progress_percentage = min(int((float(event.total_initial) / float(event.max_budget)) * 100), 100)
                else:
                    event.progress_percentage = 0
            
            total_spent = total_distributed - total_balance
            total_remaining = total_budget - total_distributed
            
            from core.models import CompanySettlement
            company_settlements = CompanySettlement.objects.filter(company=company_profile).order_by('-settlement_date')
            total_paid = company_settlements.filter(settlement_status='COMPLETED').aggregate(total=Sum('settlement_amount'))['total'] or Decimal('0.00')
            financial_debt = total_budget - total_paid
            
            event_requests = EventRequest.objects.filter(company=company_profile).order_by('-created_at')

            context.update({
                'company_profile': company_profile,
                'events_list': events,
                'vouchers_list': vouchers,
                'event_requests': event_requests,
                'company_settlements': company_settlements,
                'total_budget': total_budget,
                'total_distributed': total_distributed,
                'total_remaining': total_remaining,
                'total_spent': total_spent,
                'total_paid': total_paid,
                'financial_debt': financial_debt,
            })
        else:
            context.update({
                'company_profile': None,
                'events_list': [],
                'vouchers_list': [],
                'event_requests': [],
                'total_budget': 0,
                'total_distributed': 0,
                'total_remaining': 0,
                'total_spent': 0,
            })
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        from django.contrib import messages
        from core.models import CompanySettlement
        from decimal import Decimal
        import datetime
        
        company_profile = getattr(request.user, 'company_profile', None)
        if not company_profile:
            messages.error(request, "لا يوجد ملف شركة مرتبط بهذا الحساب.")
            return self.get(request, *args, **kwargs)
            
        if action == 'request_settlement':
            amount = request.POST.get('amount')
            date_str = request.POST.get('date', datetime.date.today())
            notes = request.POST.get('notes', '')
            try:
                image = request.FILES.get('receipt_image')
                CompanySettlement.objects.create(
                    company=company_profile,
                    settlement_amount=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    settlement_status='PENDING',
                    created_by=request.user,
                    receipt_image=image
                )
                messages.success(request, "تم تقديم طلب التسوية للإدارة بنجاح وجاري المراجعة.")
            except Exception as e:
                messages.error(request, f"حدث خطأ أثناء التقديم: {e}")
                
        return self.get(request, *args, **kwargs)

class CompanyDelegatesDoctorsView(CompanyPortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/company_delegates_doctors.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add notifications data
        if user.is_authenticated:
            from core.models import Notification
            unread_notifications = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')
            recent_notifications = Notification.objects.filter(user=user).order_by('-created_at')[:5]
            
            context['unread_notifications_count'] = unread_notifications.count()
            context['recent_notifications'] = recent_notifications
        
        # Get company profile
        company_profile = getattr(user, 'company_profile', None)
        
        if company_profile:
            # Get delegates linked to this company
            delegates = Delegate.objects.filter(companies=company_profile, is_deleted=False).prefetch_related('specialties').order_by('name')
            
            # Get doctors linked to this company's events
            from events.models import Event
            company_events = Event.objects.filter(company=company_profile)
            doctors = Doctor.objects.filter(events__in=company_events, is_deleted=False).prefetch_related('specialty').distinct().order_by('name')
            event_requests = EventRequest.objects.filter(company=company_profile).order_by('-created_at')
            
            context.update({
                'company_profile': company_profile,
                'delegates_list': delegates,
                'doctors_list': doctors,
                'event_requests': event_requests,
            })
        else:
            context.update({
                'company_profile': None,
                'delegates_list': [],
                'doctors_list': [],
            })
        
        return context

class CustomDelegatePortalView(DelegatePortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/delegate_portal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add notifications data
        if user.is_authenticated:
            from core.models import Notification
            unread_notifications = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')
            recent_notifications = Notification.objects.filter(user=user).order_by('-created_at')[:5]
            
            context['unread_notifications_count'] = unread_notifications.count()
            context['recent_notifications'] = recent_notifications
        
        # Get delegate profile linked to the user
        delegate_profile = getattr(user, 'delegate_profile', None)
        
        if delegate_profile:
            # Fetch events assigned to this delegate
            events = Event.objects.filter(delegates=delegate_profile).order_by('-date')
            
            # Fetch vouchers generated under delegate's events
            vouchers = Voucher.objects.filter(event__delegates=delegate_profile).select_related('doctor', 'event').order_by('-issue_date')
            
            # Calculate stats
            total_events = events.count()
            total_vouchers = vouchers.count()
            total_distributed = vouchers.aggregate(sum=Sum('initial_value'))['sum'] or Decimal('0.00')
            total_balance = vouchers.aggregate(sum=Sum('current_balance'))['sum'] or Decimal('0.00')
            total_spent = total_distributed - total_balance
            
            for event in events:
                # Stats per event
                v_stats = Voucher.objects.filter(event=event).aggregate(
                    initial=Sum('initial_value'),
                    balance=Sum('current_balance'),
                    count=Count('id')
                )
                event.total_vouchers = v_stats['count'] or 0
                event.total_initial = v_stats['initial'] or Decimal('0.00')
                total_bal = v_stats['balance'] or Decimal('0.00')
                event.total_spent = event.total_initial - total_bal
                
                if event.max_budget and event.max_budget > 0:
                    event.progress_percentage = min(int((float(event.total_initial) / float(event.max_budget)) * 100), 100)
                else:
                    event.progress_percentage = 0
            
            event_requests = EventRequest.objects.filter(delegate=delegate_profile).order_by('-created_at')

            context.update({
                'delegate_profile': delegate_profile,
                'events_list': events,
                'vouchers_list': vouchers,
                'event_requests': event_requests,
                'total_events_count': total_events,
                'total_vouchers_count': total_vouchers,
                'total_distributed': total_distributed,
                'total_spent': total_spent,
            })
        else:
            context.update({
                'delegate_profile': None,
                'events_list': [],
                'vouchers_list': [],
                'event_requests': [],
                'total_events_count': 0,
                'total_vouchers_count': 0,
                'total_distributed': 0,
                'total_spent': 0,
            })
        return context

class DelegateDoctorsView(DelegatePortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/delegate_doctors.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add notifications data
        if user.is_authenticated:
            from core.models import Notification
            unread_notifications = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')
            recent_notifications = Notification.objects.filter(user=user).order_by('-created_at')[:5]
            
            context['unread_notifications_count'] = unread_notifications.count()
            context['recent_notifications'] = recent_notifications
        
        # Get delegate profile
        delegate_profile = getattr(user, 'delegate_profile', None)
        
        if delegate_profile:
            # Get doctors linked to this delegate's events
            from events.models import Event
            delegate_events = Event.objects.filter(delegates=delegate_profile)
            doctors = Doctor.objects.filter(events__in=delegate_events, is_deleted=False).prefetch_related('specialty').distinct().order_by('name')
            
            # Get companies linked to this delegate
            companies = PharmaceuticalCompany.objects.filter(events__delegates=delegate_profile, is_deleted=False).distinct().order_by('name')
            
            # Add shared events count for each company
            for company in companies:
                company.shared_events_count = company.events.filter(delegates=delegate_profile).count()
            
            event_requests = EventRequest.objects.filter(delegate=delegate_profile).order_by('-created_at')
            
            context.update({
                'delegate_profile': delegate_profile,
                'doctors_list': doctors,
                'companies_list': companies,
                'event_requests': event_requests,
            })
        else:
            context.update({
                'delegate_profile': None,
                'doctors_list': [],
                'companies_list': [],
            })
        
        return context

class VendorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.type == 'VENDOR' or user.type == 'DOCTOR' or user.is_superuser or user.is_staff)

class VendorOwnerRequiredMixin(UserPassesTestMixin):
    """View only for Vendor Admins/Owners or System Staff."""
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        if user.type == 'VENDOR':
            vendor = getattr(user, 'vendor_profile', None)
            if vendor and vendor.role == 'ADMIN':
                return True
        return False

class VendorAdminRequiredMixin(UserPassesTestMixin):
    """View for both Vendor Admins and Cashiers."""
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        if user.type == 'VENDOR':
            vendor = getattr(user, 'vendor_profile', None)
            if vendor and (vendor.role == 'ADMIN' or vendor.role == 'CASHIER'):
                return True
        return False

class VendorDashboardView(LoginRequiredMixin, VendorAdminRequiredMixin, TemplateView):
    template_name = 'core/vendor_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendor = getattr(self.request.user, 'vendor_profile', None)
        
        if not vendor:
             raise PermissionDenied("لم يتم العثور على ملف بائع لهذا الحساب.")
        
        all_transactions = Transaction.objects.filter(vendor=vendor).order_by('-transaction_date')
        total_earned = all_transactions.aggregate(Sum('amount_spent'))['amount_spent__sum'] or Decimal('0.00')
        total_paid = VendorSettlement.objects.filter(vendor=vendor).aggregate(Sum('amount_settled'))['amount_settled__sum'] or Decimal('0.00')
        total_pending = total_earned - total_paid

        context['vendor'] = vendor
        context['total_sales'] = total_earned
        context['total_paid'] = total_paid
        context['total_pending'] = total_pending
        context['total_transactions'] = all_transactions.count()
        context['recent_transactions'] = all_transactions[:20]
        context['settlements'] = VendorSettlement.objects.filter(vendor=vendor).order_by('-settlement_date')[:10]
        
        return context

class SendOTPView(LoginRequiredMixin, VendorRequiredMixin, View):
    """View to generate and send OTP to doctor's email."""
    def post(self, request):
        doctor_id = request.POST.get('doctor_id')
        amount = request.POST.get('amount')
        
        if not doctor_id or not amount:
            return JsonResponse({'success': False, 'error': 'بيانات ناقصة.'}, status=400)
            
        try:
            doctor = Doctor.objects.get(id=doctor_id)
            vendor = request.user.vendor_profile
            
            otp = generate_otp()
            token = send_otp_email(doctor, otp, amount, vendor.name)
            if token:
                return JsonResponse({
                    'success': True, 
                    'message': f'تم إرسال رمز التأكيد إلى بريد الطبيب: {doctor.email}',
                    'transaction_token': token,
                    'doctor_email': doctor.email
                })
            else:
                return JsonResponse({'success': False, 'error': 'فشل إرسال البريد الإلكتروني. تأكد من إعدادات السيرفر.'}, status=500)
                
        except Doctor.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'طبيب غير موجود.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

class TransactionCreateView(LoginRequiredMixin, VendorRequiredMixin, View):
    template_name = 'core/transaction_form.html'

    def get(self, request):
        vendor = getattr(request.user, 'vendor_profile', None)
        if not vendor:
            raise PermissionDenied("يجب أن يكون لديك ملف بائع لإجراء هذه العملية.")
        
        effective_vendor = vendor
        if vendor.role == 'CASHIER' and vendor.parent_vendor:
            effective_vendor = vendor.parent_vendor

        context = {
            'is_cashier': vendor.role == 'CASHIER',
            'vendor': vendor,
            'has_management_fee': effective_vendor.has_management_fee,
        }
        
        doctor_id = request.GET.get('doctor_id')
        if doctor_id:
            try:
                doctor = Doctor.objects.get(id=doctor_id)
                balance = doctor.vouchers.filter(is_active=True).aggregate(Sum('current_balance'))['current_balance__sum'] or Decimal('0.00')
                context['prefill_doctor'] = {
                    'id': doctor.id,
                    'name': doctor.name,
                    'phone': doctor.phone,
                    'balance': float(balance),
                }
            except Doctor.DoesNotExist:
                pass
        return render(request, self.template_name, context)

    def post(self, request):
        token = request.POST.get('transaction_token')
        otp_code = request.POST.get('otp_code')

        vendor = getattr(request.user, 'vendor_profile', None)
        if not vendor:
            raise PermissionDenied("يجب أن يكون لديك ملف بائع لإجراء هذه العملية.")

        # Verify OTP first
        is_valid, result = verify_otp(token, otp_code)
        if not is_valid:
            error = result # Error message from verify_otp
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error}, status=400)
            messages.error(request, error)
            return self.get(request)

        # OTP is valid, result contains the stored data (doctor_id, amount)
        doctor_id = result['doctor_id']
        amount = result['amount']
        description = request.POST.get('description', '')
        
        # Check for manual management fee override
        has_fee = request.POST.get('has_management_fee') == 'true'

        try:
            doctor = Doctor.objects.get(id=doctor_id)
            trx = process_transaction(
                vendor, doctor, amount, description, 
                created_by=request.user,
                has_management_fee=has_fee
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'invoice': {
                        'invoice_number': trx.invoice_number,
                        'doctor_name': doctor.name,
                        'vendor_name': trx.vendor.name,
                        'amount_spent': float(trx.amount_spent),
                        'management_fee': float(trx.management_fee_amount),
                        'total_deducted': float(trx.total_deducted),
                        'date': trx.transaction_date.strftime('%Y-%m-%d %H:%M'),
                        'description': trx.items_description,
                    }
                })
            
            messages.success(request, f"تمت العملية بنجاح! رقم الفاتورة: {trx.invoice_number}")
            if vendor.role == 'CASHIER':
                return redirect('transaction_create')
            return redirect('vendor_dashboard')
            
        except Doctor.DoesNotExist:
            error = "طبيب غير موجود."
        except ValidationError as e:
            error = e.messages[0] if hasattr(e, 'messages') else str(e)
            if "Insufficient balance" in error:
                match = re.search(r"Available: ([\d\.]+), Required: ([\d\.]+)", error)
                if match:
                    avail, req = match.groups()
                    error = f"عذراً، الرصيد المتاح غير كافٍ. المتاح: {avail} ج.م، المطلوب: {req} ج.م"
        except Exception as e:
            error = f"خطأ غير متوقع: {str(e)}"

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error}, status=400)
        
        messages.error(request, error)
        return self.get(request)

class DoctorLookupView(LoginRequiredMixin, VendorRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        user = request.user
        
        # Base filter for doctors
        q_filter = Q(phone__icontains=query) | Q(email__icontains=query) | Q(qr_code__iexact=query)
        if query.isdigit():
            q_filter |= Q(id=query)
            
        # Multi-word search for names (e.g., "محمد مهري" matches "محمد المهري")
        name_filter = Q()
        for term in query.split():
            name_filter &= Q(name__icontains=term)
        
        q_filter |= name_filter
            
        doctors = Doctor.objects.filter(q_filter).distinct()
        
        results = []
        
        # 1. Doctors Results (Always included)
        for doc in doctors[:15]:
            balance = doc.vouchers.filter(is_active=True).aggregate(Sum('current_balance'))['current_balance__sum'] or Decimal('0.00')
            results.append({
                'id': doc.id,
                'name': doc.name,
                'type': 'doctor',
                'phone': doc.phone,
                'specialty': doc.specialty.name if doc.specialty else '',
                'balance': float(balance),
                'avatar_url': doc.get_avatar_url(),
                'qr_code': doc.qr_code
            })
            
        # 2. Staff-only results (Vouchers and Invoices)
        if user.is_staff or user.is_superuser:
            # Search Vouchers
            v_filter = Q()
            for term in query.split():
                v_filter &= Q(doctor__name__icontains=term)
            if query.isdigit():
                v_filter |= Q(id=query)
            vouchers = Voucher.objects.filter(v_filter)[:3]
            for v in vouchers:
                results.append({
                    'id': v.id,
                    'name': f"قسيمة رقم: {v.id}",
                    'type': 'voucher',
                    'url': f"/admin/events/voucher/{v.id}/change/",
                    'detail': f"د. {v.doctor.name if v.doctor else 'غير محدد'} - {v.current_balance} ج.م"
                })
            
            # Search Transactions (Invoices)
            t_filter = Q(invoice_number__icontains=query)
            transactions = Transaction.objects.filter(t_filter)[:3]
            for t in transactions:
                results.append({
                    'id': t.id,
                    'name': f"فاتورة: {t.invoice_number}",
                    'type': 'transaction',
                    'url': f"/admin/core/transaction/{t.id}/change/",
                    'detail': f"مورد: {t.vendor.name} - {t.amount_spent} ج.م"
                })
                
        return JsonResponse({'results': results})

class DoctorProfileView(LoginRequiredMixin, DetailView):
    model = Doctor
    template_name = 'core/doctor_profile.html'
    context_object_name = 'doctor'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        doctor_to_view = self.get_object()
        
        if user.is_superuser or user.is_staff:
            return super().dispatch(request, *args, **kwargs)
        
        if user.type == 'VENDOR':
            vendor = getattr(user, 'vendor_profile', None)
            if vendor and vendor.role == 'ADMIN':
                return super().dispatch(request, *args, **kwargs)
            raise PermissionDenied("ليس لديك صلاحية لعرض الملف الكامل للطبيب.")
        
        if user.type == 'DOCTOR':
            if hasattr(user, 'doctor_profile') and user.doctor_profile == doctor_to_view:
                return super().dispatch(request, *args, **kwargs)
        
        raise PermissionDenied("ليس لديك صلاحية لعرض هذا الملف.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vouchers = self.object.vouchers.all().order_by('-expiry_date')
        active_vouchers = vouchers.filter(is_active=True)
        
        context['vouchers'] = vouchers
        context['total_balance'] = active_vouchers.aggregate(Sum('current_balance'))['current_balance__sum'] or Decimal('0.00')
        context['active_vouchers_count'] = active_vouchers.count()
        context['expired_vouchers_count'] = vouchers.filter(is_active=False).count()
        context['transactions'] = Transaction.objects.filter(doctor=self.object).order_by('-transaction_date')
        context['total_spent'] = Transaction.objects.filter(doctor=self.object).aggregate(
            total=Sum('total_deducted'))['total'] or Decimal('0.00')
        context['transfers_made'] = self.object.transfers_made.all().order_by('-transfer_date')
        context['doctor_qr_url'] = self.request.build_absolute_uri(self.object.get_qr_code_url())
        return context

class VoucherTransferView(LoginRequiredMixin, View):
    def post(self, request, pk):
        voucher = get_object_or_404(Voucher, pk=pk)
        user = request.user
        print("start transfer to : " + request.POST.get('target_search', ''))
        
        # Ensure only the owning doctor can transfer
        if user.type != 'DOCTOR' or not hasattr(user, 'doctor_profile') or voucher.doctor != user.doctor_profile:
            messages.error(request, _("لا تملك صلاحية تحويل هذه القسيمة."))
            # If they are not a doctor but somehow got here, redirect home.
            if hasattr(user, 'doctor_profile'):
                return redirect('custom_doctor_profile', pk=user.doctor_profile.pk)
                
            return redirect('home')

        if not voucher.is_active:
            messages.error(request, _("لا يمكن تحويل قسيمة غير نشطة."))
            return redirect('custom_doctor_profile', pk=user.doctor_profile.pk)

        target_search = request.POST.get('target_search', '').strip()
        otp_code = request.POST.get('otp_code', '').strip()
        transfer_token = request.POST.get('transfer_token', '').strip()

        if not otp_code or not transfer_token:
            messages.error(request, _("يرجى توفير رمز التحقق."))
            return redirect('custom_doctor_vouchers')

        # Verify OTP using the token
        cache_key = f"transfer_otp_{transfer_token}"
        data = cache.get(cache_key)

        if not data:
            messages.error(request, _("انتهت صلاحية رمز التحقق أو أنه غير صالح."))
            return redirect('custom_doctor_vouchers')

        if data['otp'] != otp_code:
            messages.error(request, _("رمز التحقق غير صحيح."))
            return redirect('custom_doctor_vouchers')
        
        # Verify voucher and doctors match cache data
        if data['voucher_id'] != voucher.id or data['from_doctor_id'] != user.doctor_profile.id:
            messages.error(request, _("بيانات العملية غير متطابقة."))
            return redirect('custom_doctor_vouchers')

        target_doctor = get_object_or_404(Doctor, id=data['to_doctor_id'])
        
        old_doctor = voucher.doctor
        old_doctor_name = old_doctor.name
        
        # Perform transfer
        voucher.doctor = target_doctor
        transfer_note = f"تم التحويل من د. {old_doctor_name}"
        if voucher.notes:
            voucher.notes += f"\n{transfer_note}"
        else:
            voucher.notes = transfer_note
        voucher.save()

        # Log transfer history
        VoucherTransfer.objects.create(
            from_doctor=old_doctor,
            to_doctor=target_doctor,
            voucher=voucher
        )

        # Clear cache
        cache.delete(cache_key)

        messages.success(request, f"تم تحويل القسيمة بنجاح إلى د. {target_doctor.name}.")
        return redirect('custom_doctor_vouchers')

class DoctorPortalRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('custom_login')
            
        # 1. Check if Admin/Staff
        if request.user.is_staff or request.user.is_superuser:
            return redirect('custom_dashboard')
            
        # 2. Check if Vendor
        if hasattr(request.user, 'vendor_profile'):
            return redirect('custom_vendor_portal')
            
        # 3. Check if Doctor
        if not hasattr(request.user, 'doctor_profile'):
            # If they are none of the above, redirect home or login
            messages.error(request, _("هذه الصفحة مخصصة للأطباء فقط."))
            return redirect('home')
            
        return super().dispatch(request, *args, **kwargs)

class SendTransferOTPView(DoctorPortalRequiredMixin, View):
    def post(self, request):
        import json
        from .services import generate_otp, send_transfer_otp_email
        from events.models import Voucher
        
        try:
            data = json.loads(request.body)
            voucher_id = data.get('voucher_id')
            target_search = data.get('target_search', '').strip()
            
            if not voucher_id or not target_search:
                return JsonResponse({'success': False, 'error': 'بيانات غير مكتملة.'}, status=400)
                
            voucher = get_object_or_404(Voucher, id=voucher_id, doctor=request.user.doctor_profile)
            
            # Find target doctor by phone, QR, name, or email
            target_doctor = Doctor.objects.filter(
                Q(phone=target_search) | 
                Q(qr_code__iexact=target_search) |
                Q(name__icontains=target_search) |
                Q(email__iexact=target_search)
            ).first()
            
            if not target_doctor:
                return JsonResponse({'success': False, 'error': 'لم يتم العثور على الطبيب المستلم.'}, status=404)
                
            if target_doctor == request.user.doctor_profile:
                return JsonResponse({'success': False, 'error': 'لا يمكنك التحويل لنفسك.'}, status=400)
            
            otp = generate_otp()
            token = send_transfer_otp_email(request.user.doctor_profile, target_doctor, voucher, otp)
            
            if token:
                return JsonResponse({'success': True, 'token': token, 'recipient_name': target_doctor.name})
            else:
                return JsonResponse({'success': False, 'error': 'فشل إرسال الرمز، يرجى المحاولة لاحقاً.'}, status=500)
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

class CashierCreateView(LoginRequiredMixin, VendorOwnerRequiredMixin, CreateView):
    model = User
    template_name = 'core/cashier_form.html'
    fields = ['username', 'password', 'first_name', 'last_name', 'email']
    success_url = reverse_lazy('vendor_dashboard')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.type = 'VENDOR'
        user.set_password(form.cleaned_data['password'])
        user.phone = self.request.POST.get('phone', '')
        user.save()
        
        parent_vendor = self.request.user.vendor_profile
        
        # Ensure unique name for cashier vendor
        cashier_name = f"{user.first_name} {user.last_name}".strip() or user.username
        if Vendor.objects.filter(name=cashier_name).exists():
            cashier_name = f"{cashier_name} ({user.username})"

        Vendor.objects.create(
            user=user,
            name=cashier_name,
            parent_vendor=parent_vendor,
            role='CASHIER',
            phone=self.request.POST.get('phone', ''),
            email=user.email or f"{user.username}@hadramout.com"
        )
        messages.success(self.request, f"تم إنشاء حساب الكاشير '{cashier_name}' بنجاح.")
        
        # ── إشعار للإدارة عند إنشاء كاشير جديد ──
        try:
            from core.models import Notification
            from accounts.models import User as UserModel
            admin_users = UserModel.objects.filter(is_staff=True, is_active=True)
            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    message=f"تم إنشاء حساب كاشير جديد '{cashier_name}' تابع لمتجر {parent_vendor.name}.",
                    notification_type='ACCOUNT',
                    link='/custom-vendors/'
                )
        except Exception:
            pass

        # Redirect back to where we came from
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return redirect(next_url)
        if self.request.user.is_staff:
            return redirect('custom_vendor_portal')
        return redirect('vendor_dashboard')

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return redirect(self.request.META.get('HTTP_REFERER', 'custom_vendor_portal'))

class CashierDeleteView(LoginRequiredMixin, VendorOwnerRequiredMixin, View):
    def post(self, request, pk):
        parent_vendor = request.user.vendor_profile
        cashier_vendor = get_object_or_404(Vendor, id=pk, parent_vendor=parent_vendor, role='CASHIER')
        user = cashier_vendor.user
        cashier_vendor.delete()
        user.delete()
        messages.success(request, _("تم حذف حساب الكاشير بنجاح."))
        return redirect(request.META.get('HTTP_REFERER', 'custom_vendor_portal'))

class CustomPOSView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'custom_admin/vendor_portal.html'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        # 1. Auto-create or get Vendor profile for Admin
        user = self.request.user
        vendor, created = Vendor.objects.get_or_create(
            user=user,
            defaults={
                'name': f"إدارة: {user.username}",
                'contact_person': user.get_full_name() or user.username,
                'phone': user.phone or '01000000000',
                'email': user.email or 'admin@hadramout.com',
                'address': 'المقر الرئيسي',
                'category': 'إدارة عامة',
                'role': 'ADMIN'
            }
        )
        
        # 2. Call CustomVendorPortalView logic via context helper (or duplicate logic for speed/safety)
        # We'll use the logic from CustomVendorPortalView here
        view_instance = CustomVendorPortalView()
        view_instance.request = self.request
        context = view_instance.get_context_data(**kwargs)
        
        # 3. Add flag for Top-Bar layout
        context['is_admin_view'] = True
        return context

class CustomManagerDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'custom_admin/manager_dashboard.html'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # KPI Data
        now = timezone.now()
        last_7_days = now - timedelta(days=7)
        prev_7_days = last_7_days - timedelta(days=7)
        
        total_revenue = Transaction.objects.aggregate(total=Sum('amount_spent'))['total'] or Decimal('0.00')
        total_fees = Transaction.objects.aggregate(total=Sum('management_fee_amount'))['total'] or Decimal('0.00')
        revenue_7d = Transaction.objects.filter(transaction_date__gte=last_7_days).aggregate(total=Sum('amount_spent'))['total'] or Decimal('0.00')
        revenue_prev_7d = Transaction.objects.filter(transaction_date__gte=prev_7_days, transaction_date__lt=last_7_days).aggregate(total=Sum('amount_spent'))['total'] or Decimal('0.00')
        
        revenue_growth = 0
        if revenue_prev_7d > 0:
            revenue_growth = ((revenue_7d - revenue_prev_7d) / revenue_prev_7d) * 100
        elif revenue_7d > 0:
            revenue_growth = 100

        # Counts - excluding deleted/inactive records
        active_vouchers_count = Voucher.objects.filter(is_active=True, current_balance__gt=0).count()
        exhausted_vouchers_count = Voucher.objects.filter(current_balance=0).count()
        expired_vouchers_count = Voucher.objects.filter(is_active=False).count()
        
        total_doctors = Doctor.objects.filter(is_deleted=False).count()
        total_vendors = Vendor.objects.filter(is_deleted=False, is_active=True, parent_vendor__isnull=True).count()
        total_transactions = Transaction.objects.count()
        total_companies = PharmaceuticalCompany.objects.filter(is_deleted=False).count()
        from accounts.models import Delegate
        total_delegates = Delegate.objects.filter(is_deleted=False).count()
        today = now.date()
        first_of_month = today.replace(day=1)
        revenue_this_month = Transaction.objects.filter(
            transaction_date__date__gte=first_of_month
        ).aggregate(total=Sum('amount_spent'))['total'] or Decimal('0.00')
        
        # Pending Settlements (Total Sales - Total Settled)
        total_sales_all = Transaction.objects.aggregate(total=Sum('total_deducted'))['total'] or Decimal('0.00')
        total_settled_all = VendorSettlement.objects.filter(settlement_status='COMPLETED').aggregate(total=Sum('amount_settled'))['total'] or Decimal('0.00')
        pending_settlements_total = max(total_sales_all - total_settled_all, Decimal('0.00'))

        # Specialty Distribution (Top 5)
        specialty_data = Specialty.objects.annotate(
            count=Count('doctor', filter=Q(doctor__is_deleted=False))
        ).filter(count__gt=0).order_by('-count')[:5]

        # Top Events (by Transaction Count)
        top_events = Event.objects.annotate(
            trx_count=Count('vouchers__transactions')
        ).filter(trx_count__gt=0).order_by('-trx_count')[:5]

        # Recent Activity
        recent_transactions = Transaction.objects.select_related('vendor', 'doctor').order_by('-transaction_date')[:8]
        
        # Recent new doctors
        recent_doctors = Doctor.objects.filter(is_deleted=False).select_related('specialty').order_by('-id')[:5]
        
        # Top Vendors (excluding deleted)
        top_vendors = Vendor.objects.filter(is_deleted=False).annotate(
            total_sales=Sum('transaction__amount_spent')
        ).filter(total_sales__gt=0).order_by('-total_sales')[:5]

        # 30-day consumption chart calculation
        chart_labels = []
        chart_data = []
        last_30_days_dt = now - timedelta(days=29)
        from django.db.models.functions import TruncDate
        daily_sales_qs = (
            Transaction.objects
            .filter(transaction_date__gte=last_30_days_dt)
            .annotate(day=TruncDate('transaction_date'))
            .values('day')
            .annotate(total=Sum('amount_spent'))
            .order_by('day')
        )
        daily_sales_map = {entry['day']: float(entry['total']) for entry in daily_sales_qs}
        for i in range(30):
            day = (last_30_days_dt + timedelta(days=i)).date()
            chart_labels.append(day.strftime('%d/%m'))
            chart_data.append(daily_sales_map.get(day, 0.0))

        context.update({
            'total_revenue': total_revenue,
            'total_fees': total_fees,
            'revenue_growth': round(float(revenue_growth), 1),
            'revenue_this_month': revenue_this_month,
            'active_vouchers_count': active_vouchers_count,
            'exhausted_vouchers_count': exhausted_vouchers_count,
            'expired_vouchers_count': expired_vouchers_count,
            'total_doctors': total_doctors,
            'total_vendors': total_vendors,
            'total_transactions': total_transactions,
            'total_companies': total_companies,
            'total_delegates': total_delegates,
            'pending_settlements_total': pending_settlements_total,
            'specialty_data': specialty_data,
            'top_events': top_events,
            'recent_transactions': recent_transactions,
            'recent_doctors': recent_doctors,
            'top_vendors': top_vendors,
            'chart_labels': chart_labels,
            'chart_data': chart_data,
            'today': today,
        })
        return context

class CustomDoctorsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'custom_admin/doctors_directory.html'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        specialty_id = self.request.GET.get('specialty', '')
        status_filter = self.request.GET.get('status', '')
        balance_filter = self.request.GET.get('balance', '')
        voucher_filter = self.request.GET.get('voucher', '')
        company_filter = self.request.GET.get('company', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        
        # Get doctors with their specialties and prefetch active vouchers
        base_qs = Doctor.objects.select_related('specialty').order_by('-id')
        
        if query:
            name_filter = Q()
            for term in query.split():
                name_filter &= Q(name__icontains=term)
            base_qs = base_qs.filter(
                name_filter | Q(phone__icontains=query)
            )
            
        if specialty_id:
            base_qs = base_qs.filter(specialty_id=specialty_id)
            
        if status_filter == 'active':
            base_qs = base_qs.filter(user__is_active=True)
        elif status_filter == 'inactive':
            base_qs = base_qs.filter(user__is_active=False)

        if company_filter:
            base_qs = base_qs.filter(vouchers__company_id=company_filter, vouchers__is_active=True).distinct()

        if date_from:
            base_qs = base_qs.filter(created_at__date__gte=date_from)
        if date_to:
            base_qs = base_qs.filter(created_at__date__lte=date_to)
            
        doctors_annotated = base_qs.annotate(
            total_balance=Sum('vouchers__current_balance', filter=Q(vouchers__is_active=True)),
            active_vouchers_count=Count('vouchers', filter=Q(vouchers__is_active=True, vouchers__current_balance__gt=0))
        )

        # Filter by balance
        if balance_filter == 'has_balance':
            doctors_annotated = doctors_annotated.filter(total_balance__gt=0)
        elif balance_filter == 'no_balance':
            doctors_annotated = doctors_annotated.filter(
                Q(total_balance__isnull=True) | Q(total_balance__lte=0)
            )

        # Filter by active vouchers
        if voucher_filter == 'has_voucher':
            doctors_annotated = doctors_annotated.filter(active_vouchers_count__gt=0)
        elif voucher_filter == 'no_voucher':
            doctors_annotated = doctors_annotated.filter(active_vouchers_count=0)
        
        # Split into active and archived
        doctors_qs = doctors_annotated.filter(is_deleted=False)
        archived_qs = doctors_annotated.filter(is_deleted=True)
        
        # Pagination: 100 per page for active doctors
        paginator = Paginator(doctors_qs, 100)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context.update({
            'doctors': page_obj,
            'archived_doctors': archived_qs,
            'page_obj': page_obj,
            'query': query,
            'current_specialty': specialty_id,
            'current_status': status_filter,
            'current_balance': balance_filter,
            'current_voucher': voucher_filter,
            'current_company': company_filter,
            'date_from': date_from,
            'date_to': date_to,
            'specialties': Specialty.objects.annotate(doctors_count=Count('doctor', filter=Q(doctor__is_deleted=False))),
            'companies_list': PharmaceuticalCompany.objects.all(),
        })
        
        # Check if there's a duplicate doctor in session
        if 'duplicate_doc_id' in self.request.session:
            context['duplicate_doc_id'] = self.request.session.pop('duplicate_doc_id')
            context['duplicate_doc_name'] = self.request.session.pop('duplicate_doc_name')
            
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        
        if action == "add_doctor":
            name = request.POST.get("name")
            phone = request.POST.get("phone")
            email = request.POST.get("email")
            specialty_id = request.POST.get("specialty")
            username = request.POST.get("username")
            password = request.POST.get("password")

            if not all([name, phone, username, password]):
                messages.error(request, _("يرجى تعبئة الحقول المطلوبة."))
                return redirect('custom_doctors')
            
            # Check for duplicates across all entities in the system
            duplicate_user = User.objects.filter(username=username).first()
            duplicate = None
            duplicate_type = None
            
            if duplicate_user:
                if hasattr(duplicate_user, 'doctor_profile'):
                    duplicate = duplicate_user.doctor_profile
                    duplicate_type = 'doctor'
                elif hasattr(duplicate_user, 'company_profile'):
                    duplicate = duplicate_user.company_profile
                    duplicate_type = 'company'
                elif hasattr(duplicate_user, 'delegate_profile'):
                    duplicate = duplicate_user.delegate_profile
                    duplicate_type = 'delegate'
            
            if not duplicate:
                duplicate_doc = Doctor.objects.filter(Q(phone=phone) | (Q(email=email) if email else Q(pk__isnull=True))).filter(is_deleted=False).first()
                if duplicate_doc:
                    duplicate = duplicate_doc
                    duplicate_type = 'doctor'
            
            if not duplicate:
                # Check in PharmaceuticalCompany
                duplicate_comp = PharmaceuticalCompany.objects.filter(Q(phone=phone) | (Q(email=email) if email else Q(pk__isnull=True))).filter(is_deleted=False).first()
                if duplicate_comp:
                    duplicate = duplicate_comp
                    duplicate_type = 'company'
                    
            if not duplicate:
                # Check in Delegate
                duplicate_del = Delegate.objects.filter(phone=phone).filter(is_deleted=False).first()
                if duplicate_del:
                    duplicate = duplicate_del
                    duplicate_type = 'delegate'

            if duplicate and not getattr(duplicate, 'is_deleted', False):
                if duplicate_type == 'doctor':
                    request.session['duplicate_doc_id'] = duplicate.id
                    request.session['duplicate_doc_name'] = duplicate.name
                    messages.error(request, f"البيانات مسجلة مسبقاً باسم الطبيب: {duplicate.name}")
                else:
                    type_label = 'الشركة' if duplicate_type == 'company' else 'المندوب'
                    messages.error(request, f"خطأ: البيانات المدخلة مسجلة مسبقاً باسم {type_label}: {duplicate.name}")
                return redirect('custom_doctors')
                
            if duplicate_user:
                messages.error(request, _('اسم المستخدم (Login) مسجل مسبقاً لمستخدم آخر في النظام.'))
                return redirect('custom_doctors')
                
            try:
                user = User.objects.create_user(username=username, password=password, email=email, first_name=name)
                user.type = User.Types.DOCTOR
                user.save()
                specialty = Specialty.objects.get(id=specialty_id) if specialty_id else None
                Doctor.objects.create(user=user, name=name, phone=phone, email=email, specialty=specialty)
                messages.success(request, f"تم إضافة الطبيب {name} بنجاح.")
            except Exception as e:
                messages.error(request, f"حدث خطأ أثناء الإضافة: {str(e)}")
            return redirect('custom_doctors')

        elif action == "add_specialty":
            name = request.POST.get("name")
            if name:
                name = name.strip()
                if Specialty.objects.filter(name__iexact=name).exists():
                    messages.error(request, f"خطأ: التخصص '{name}' موجود بالفعل.")
                else:
                    Specialty.objects.create(name=name)
                    messages.success(request, f"تم إضافة التخصص '{name}' بنجاح.")
            else:
                messages.error(request, _("يرجى إدخال اسم التخصص."))
            return redirect('custom_doctors')

        elif action == "edit_specialty":
            specialty_id = request.POST.get("specialty_id")
            name = request.POST.get("name")
            if specialty_id and name:
                name = name.strip()
                try:
                    spec = Specialty.objects.get(id=specialty_id)
                    if Specialty.objects.filter(name__iexact=name).exclude(id=specialty_id).exists():
                        messages.error(request, f"خطأ: يوجد تخصص آخر يحمل اسم '{name}'.")
                    else:
                        old_name = spec.name
                        spec.name = name
                        spec.save()
                        messages.success(request, f"تم تعديل التخصص من '{old_name}' إلى '{name}' بنجاح.")
                except Specialty.DoesNotExist:
                    messages.error(request, _("التخصص غير موجود."))
            else:
                messages.error(request, _("بيانات غير مكتملة لتعديل التخصص."))
            return redirect('custom_doctors')

        elif action == "delete_specialty":
            specialty_id = request.POST.get("specialty_id")
            if specialty_id:
                try:
                    spec = Specialty.objects.get(id=specialty_id)
                    name = spec.name
                    spec.delete()
                    messages.success(request, f"تم حذف التخصص '{name}' بنجاح.")
                except Specialty.DoesNotExist:
                    messages.error(request, _("التخصص غير موجود."))
                except Exception as e:
                    messages.error(request, f"خطأ أثناء حذف التخصص: {str(e)}")
            else:
                messages.error(request, _("معرف التخصص غير صالح."))
            return redirect('custom_doctors')

        doctor_ids = request.POST.getlist("doctor_ids")
        if action and doctor_ids:
            doctors = Doctor.objects.filter(id__in=doctor_ids)
            
            if action == "bulk_add_voucher":
                initial_value = request.POST.get('initial_value')
                company_id = request.POST.get('company')
                expiry_date_str = request.POST.get('expiry_date')
                notes = request.POST.get('notes')
                
                if not initial_value or not expiry_date_str:
                    messages.error(request, _("يرجى تعبئة الحقول المطلوبة للقسيمة."))
                    return redirect('custom_doctors')
                
                from datetime import datetime
                try:
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                    company = PharmaceuticalCompany.objects.get(id=company_id) if company_id else None
                    
                    count = 0
                    for doc in doctors:
                        Voucher.objects.create(
                            doctor=doc,
                            initial_value=initial_value,
                            current_balance=initial_value,
                            company=company,
                            expiry_date=expiry_date,
                            notes=notes,
                            is_active=True
                        )
                        count += 1
                    messages.success(request, f"تم إضافة القسائم لعدد {count} طبيب بنجاح.")
                except Exception as e:
                    messages.error(request, f"حدث خطأ: {str(e)}")

            elif action == "bulk_activate":
                users = User.objects.filter(doctor_profile__id__in=doctor_ids)
                count = users.update(is_active=True)
                messages.success(request, f"تم تفعيل عدد {count} حساب بنجاح.")

            elif action == "bulk_deactivate":
                users = User.objects.filter(doctor_profile__id__in=doctor_ids)
                count = users.update(is_active=False)
                messages.success(request, f"تم تعطيل عدد {count} حساب بنجاح.")

            elif action == "bulk_delete":
                # Soft delete and rename unique fields to allow re-registration
                count = 0
                for doc in doctors:
                    if not doc.is_deleted:
                        doc.is_deleted = True
                        doc.phone = f"{doc.phone}_del_{doc.id}"
                        doc.email = f"del_{doc.id}_{doc.email}"
                        doc.save()
                        
                        user = doc.user
                        user.is_active = False
                        user.username = f"{user.username}_del_{user.id}"
                        user.email = doc.email
                        user.save()
                        count += 1
                messages.success(request, f"تم أرشفة وإيقاف عدد {count} طبيب بنجاح (مع الاحتفاظ بالسجلات المالية).")

            elif action == "bulk_print_cards":
                ids_str = ",".join(map(str, doctor_ids))
                return redirect(reverse('bulk_print_doctors') + f'?ids={ids_str}')

        return redirect('custom_doctors')

class BulkPrintDoctorsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'custom_admin/bulk_print_cards.html'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ids_str = self.request.GET.get('ids', '')
        if ids_str:
            ids = ids_str.split(',')
            context['doctors'] = Doctor.objects.filter(id__in=ids).select_related('specialty')
        else:
            context['doctors'] = []
        return context


        # Fallback to single doctor addition (Old logic)
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        specialty_id = request.POST.get('specialty')
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not all([name, phone, email, username, password]):
            messages.error(request, _("يرجى ملء جميع البيانات المطلوبة."))
            return redirect('custom_doctors')

        try:
            # 1. Create User
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                type='DOCTOR'
            )
            
            # 2. Create Doctor Profile
            specialty = get_object_or_404(Specialty, id=specialty_id) if specialty_id else None
            Doctor.objects.create(
                user=user,
                name=name,
                phone=phone,
                email=email,
                specialty=specialty
            )
            messages.success(request, f"تمت إضافة الطبيب {name} بنجاح.")
        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء الإضافة: {str(e)}")
            
        return redirect('custom_doctors')

class CustomDoctorProfileView(LoginRequiredMixin, VendorAdminRequiredMixin, DetailView):
    model = Doctor
    template_name = 'custom_admin/doctor_profile.html'
    context_object_name = 'doctor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.object
        
        # Imports for Aggregation
        from django.db.models import Sum, Q
        from django.db.models.functions import TruncMonth
        
        # Financial Summary
        context['total_balance'] = doctor.vouchers.filter(is_active=True).aggregate(total=Sum('current_balance'))['total'] or 0
        
        # Vouchers List
        context['vouchers_list'] = doctor.vouchers.all().select_related('company').order_by('-issue_date')
        
        # Transactions List (Purchases)
        context['transactions_list'] = Transaction.objects.filter(doctor=doctor).select_related('vendor', 'created_by').order_by('-transaction_date')
        
        # Transfers List
        context['transfers_out'] = VoucherTransfer.objects.filter(from_doctor=doctor).select_related('to_doctor', 'voucher').order_by('-transfer_date')
        context['transfers_in'] = VoucherTransfer.objects.filter(to_doctor=doctor).select_related('from_doctor', 'voucher').order_by('-transfer_date')
        
        # Financial Analytics
        # Monthly spending data for chart
        monthly_spending = Transaction.objects.filter(doctor=doctor)\
            .annotate(month=TruncMonth('transaction_date'))\
            .values('month')\
            .annotate(total=Sum('total_deducted'))\
            .order_by('month')
            
        chart_labels = [m['month'].strftime('%b %Y') for m in monthly_spending]
        chart_data = [float(m['total']) for m in monthly_spending]
        
        context['chart_labels'] = chart_labels
        context['chart_data'] = chart_data
        
        # Lifetime stats
        context['lifetime_charged'] = Voucher.objects.filter(doctor=doctor).aggregate(Sum('initial_value'))['initial_value__sum'] or 0
        context['lifetime_spent'] = Transaction.objects.filter(doctor=doctor).aggregate(Sum('total_deducted'))['total_deducted__sum'] or 0
        
        # Lookups
        context['companies_list'] = PharmaceuticalCompany.objects.all()
        context['specialties_list'] = Specialty.objects.all()
        context['today'] = timezone.now().date()
        
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        doctor = self.object
        action = request.POST.get('action')
        
        if action == 'add_voucher':
            initial_value = request.POST.get('initial_value')
            company_id = request.POST.get('company')
            expiry_date_str = request.POST.get('expiry_date')
            notes = request.POST.get('notes')
            
            try:
                from datetime import datetime
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                company = PharmaceuticalCompany.objects.get(id=company_id) if company_id else None
                
                Voucher.objects.create(
                    doctor=doctor,
                    initial_value=initial_value,
                    current_balance=initial_value,
                    company=company,
                    expiry_date=expiry_date,
                    notes=notes,
                    is_active=True
                )
                messages.success(request, f"تم إضافة قسيمة بقيمة {initial_value} بنجاح.")
            except Exception as e:
                messages.error(request, f"حدث خطأ: {str(e)}")
                
        elif action == 'toggle_voucher_status':
            voucher_id = request.POST.get('voucher_id')
            voucher = get_object_or_404(Voucher, id=voucher_id, doctor=doctor)
            voucher.is_active = not voucher.is_active
            voucher.save()
            status = "تنشيط" if voucher.is_active else "إيقاف"
            messages.success(request, f"تم {status} القسيمة بنجاح.")

        elif action == 'update_voucher':
            voucher_id = request.POST.get('voucher_id')
            voucher = get_object_or_404(Voucher, id=voucher_id, doctor=doctor)
            
            new_balance = request.POST.get('current_balance')
            new_expiry = request.POST.get('expiry_date')
            
            try:
                if new_balance:
                    voucher.current_balance = new_balance
                if new_expiry:
                    from datetime import datetime
                    voucher.expiry_date = datetime.strptime(new_expiry, '%Y-%m-%d').date()
                voucher.save()
                messages.success(request, _("تم تحديث بيانات القسيمة بنجاح."))
            except Exception as e:
                messages.error(request, f"خطأ في التحديث: {str(e)}")

        elif action == 'delete_voucher':
            voucher_id = request.POST.get('voucher_id')
            voucher = get_object_or_404(Voucher, id=voucher_id, doctor=doctor)
            if voucher.transactions.exists():
                messages.error(request, _("لا يمكن حذف قسيمة تحتوي على عمليات مالية مسجلة. يمكنك تعطيلها بدلاً من ذلك."))
            else:
                voucher.delete()
                messages.success(request, _("تم حذف القسيمة بنجاح."))

        elif action == 'delete_transaction':
            from core.models import Transaction
            trx_id = request.POST.get('transaction_id')
            trx = get_object_or_404(Transaction, id=trx_id, doctor=doctor)
            
            # Refund the amount to the voucher if it exists
            if trx.voucher:
                trx.voucher.current_balance += trx.total_deducted
                trx.voucher.save()
            
            trx.delete()
            messages.success(request, _("تم إلغاء العملية المالية وإعادة المبلغ لرصيد القسيمة بنجاح."))

        elif action == 'cancel_transfer':
            transfer_id = request.POST.get('transfer_id')
            from events.models import VoucherTransfer
            transfer = get_object_or_404(VoucherTransfer, id=transfer_id)
            
            # Revert voucher ownership
            voucher = transfer.voucher
            voucher.doctor = transfer.from_doctor
            voucher.save()
            
            # Delete the transfer record
            transfer.delete()
            messages.success(request, _("تم إلغاء التحويل وإعادة القسيمة للطبيب الأصلي بنجاح."))

        elif action == 'toggle_status':
            doctor.user.is_active = not doctor.user.is_active
            doctor.user.save()
            status = "تفعيل" if doctor.user.is_active else "تعطيل"
            messages.success(request, f"تم {status} حساب الطبيب بنجاح.")
            
        elif action == 'reset_password':
            new_password = request.POST.get('new_password')
            if new_password:
                doctor.user.set_password(new_password)
                doctor.user.save()
                messages.success(request, _("تم تغيير كلمة المرور بنجاح."))
                
        elif action == 'update_profile':
            doctor.name = request.POST.get('name', doctor.name)
            doctor.phone = request.POST.get('phone', doctor.phone)
            doctor.email = request.POST.get('email', doctor.email)
            spec_id = request.POST.get('specialty')
            if spec_id:
                doctor.specialty = Specialty.objects.get(id=spec_id)
            
            if 'profile_picture' in request.FILES:
                doctor.profile_picture = request.FILES['profile_picture']
                
            doctor.save()
            messages.success(request, _("تم تحديث بيانات الطبيب بنجاح."))

        return redirect('custom_doctor_profile', pk=doctor.pk)

class CustomVendorSettlementsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'custom_admin/vendor_settlements.html'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.models import VendorSettlement, CompanySettlement, DelegateSettlement, Transaction
        from accounts.models import Vendor
        from django.db.models import Sum, Q
        from decimal import Decimal
        
        # Vendor Metrics
        total_sales_all = Transaction.objects.aggregate(total=Sum('total_deducted'))['total'] or Decimal('0.00')
        total_settled_all = VendorSettlement.objects.filter(settlement_status='COMPLETED').aggregate(total=Sum('amount_settled'))['total'] or Decimal('0.00')
        context['pending_vendor_debts'] = total_sales_all - total_settled_all
        context['expected_admin_fees'] = Transaction.objects.aggregate(total=Sum('management_fee_amount'))['total'] or Decimal('0.00')
        
        # Lists
        context['vendor_settlements'] = VendorSettlement.objects.all().order_by('-settlement_date')
        # Combine Company and Delegate Settlements for Companies History
        all_company_related_settlements = []
        for st in CompanySettlement.objects.all():
            all_company_related_settlements.append({
                'type': 'company',
                'obj': st,
                'company': st.company,
                'amount': st.settlement_amount,
                'date': st.settlement_date,
                'status': st.settlement_status,
                'receipt': st.receipt_image,
                'notes': st.notes,
                'id': st.id,
                'other': None
            })
        for st in DelegateSettlement.objects.all():
            all_company_related_settlements.append({
                'type': 'delegate',
                'obj': st,
                'company': st.company,
                'amount': st.settlement_amount,
                'date': st.settlement_date,
                'status': st.settlement_status,
                'receipt': st.receipt_image,
                'notes': st.notes,
                'id': st.id,
                'other': st.delegate
            })
        # Sort combined list by date descending
        all_company_related_settlements.sort(key=lambda x: x['date'], reverse=True)
        context['company_settlements'] = CompanySettlement.objects.all().order_by('-settlement_date')
        context['all_company_related_settlements'] = all_company_related_settlements
        context['delegate_settlements'] = DelegateSettlement.objects.all().order_by('-settlement_date')
        
        # We need pending vendors list with their stats
        vendors = Vendor.objects.filter(parent_vendor__isnull=True)
        pending_vendors = []
        all_vendors_list = []
        for v in vendors:
            # aggregate transactions and settlements for v and its branches
            v_family = Vendor.objects.filter(Q(id=v.id) | Q(parent_vendor=v))
            v_sales = Transaction.objects.filter(vendor__in=v_family).aggregate(t=Sum('total_deducted'))['t'] or Decimal('0.00')
            v_settled = VendorSettlement.objects.filter(vendor__in=v_family, settlement_status='COMPLETED').aggregate(t=Sum('amount_settled'))['t'] or Decimal('0.00')
            v_invoices = Transaction.objects.filter(vendor__in=v_family).count()
            v_debt = v_sales - v_settled
            
            vendor_data = {
                'vendor': v,
                'debt': v_debt,
                'invoices_count': v_invoices
            }
            all_vendors_list.append(vendor_data)
            
            if v_debt > 0:
                pending_vendors.append(vendor_data)
                
        context['pending_vendors'] = pending_vendors
        context['all_vendors_list'] = all_vendors_list
        
        # Dropdowns for company and delegate settlement forms
        from accounts.models import Delegate
        context['companies_list'] = PharmaceuticalCompany.objects.filter(is_deleted=False).order_by('name')
        context['delegates_list'] = Delegate.objects.filter(is_deleted=False).order_by('name')
        
        # Pending Companies with due balances
        from events.models import Voucher
        companies = PharmaceuticalCompany.objects.filter(is_deleted=False)
        pending_companies = []
        all_companies_list = []
        for company in companies:
            company_vouchers = Voucher.objects.filter(company=company)
            total_issued = company_vouchers.aggregate(t=Sum('initial_value'))['t'] or Decimal('0.00')
            total_consumed = sum((v.initial_value - v.current_balance) for v in company_vouchers)
            total_settled_company = CompanySettlement.objects.filter(
                company=company, settlement_status='COMPLETED'
            ).aggregate(t=Sum('settlement_amount'))['t'] or Decimal('0.00')
            total_settled_delegates = DelegateSettlement.objects.filter(
                company=company, settlement_status='COMPLETED'
            ).aggregate(t=Sum('settlement_amount'))['t'] or Decimal('0.00')
            total_settled = total_settled_company + total_settled_delegates
            due_balance = total_consumed - total_settled
            events_count = company_vouchers.values('event').distinct().count()
            vouchers_count = company_vouchers.count()
            company_data = {
                'company': company,
                'total_issued': total_issued,
                'total_consumed': total_consumed,
                'total_settled': total_settled,
                'due_balance': due_balance,
                'events_count': events_count,
                'vouchers_count': vouchers_count,
            }
            all_companies_list.append(company_data)
            if due_balance > Decimal('0.00'):
                pending_companies.append(company_data)
        context['pending_companies'] = pending_companies
        context['all_companies_list'] = all_companies_list

        # Pending Delegates with due balances — broken down per company
        from events.models import Event
        delegates = Delegate.objects.filter(is_deleted=False)
        pending_delegates = []
        all_delegates_list = []
        for delegate in delegates:
            # Find companies this delegate worked with via events
            delegate_companies = PharmaceuticalCompany.objects.filter(
                is_deleted=False,
                events__delegates=delegate
            ).distinct()
            
            delegate_total_issued = Decimal('0.00')
            delegate_total_consumed = Decimal('0.00')
            delegate_total_settled = Decimal('0.00')
            delegate_companies_detail = []
            
            for company in delegate_companies:
                # Vouchers for this delegate in this company's events
                d_c_vouchers = Voucher.objects.filter(
                    event__delegates=delegate,
                    company=company
                )
                c_issued = d_c_vouchers.aggregate(t=Sum('initial_value'))['t'] or Decimal('0.00')
                c_consumed = sum((v.initial_value - v.current_balance) for v in d_c_vouchers)
                c_settled = DelegateSettlement.objects.filter(
                    delegate=delegate,
                    company=company,
                    settlement_status='COMPLETED'
                ).aggregate(t=Sum('settlement_amount'))['t'] or Decimal('0.00')
                c_due = c_consumed - c_settled
                c_events = d_c_vouchers.values('event').distinct().count()
                c_doctors = d_c_vouchers.values('doctor').distinct().count()
                
                delegate_total_issued += c_issued
                delegate_total_consumed += Decimal(str(c_consumed))
                delegate_total_settled += c_settled
                
                if c_due > Decimal('0.00'):
                    delegate_companies_detail.append({
                        'company': company,
                        'consumed': c_consumed,
                        'settled': c_settled,
                        'due': c_due,
                        'events_count': c_events,
                        'doctors_count': c_doctors,
                    })

            # If no company relationships, fall back to all vouchers
            if not delegate_companies.exists():
                delegate_vouchers = Voucher.objects.filter(event__delegates=delegate)
                delegate_total_issued = delegate_vouchers.aggregate(t=Sum('initial_value'))['t'] or Decimal('0.00')
                delegate_total_consumed = Decimal(str(sum(
                    (v.initial_value - v.current_balance) for v in delegate_vouchers
                )))
                delegate_total_settled = DelegateSettlement.objects.filter(
                    delegate=delegate, settlement_status='COMPLETED'
                ).aggregate(t=Sum('settlement_amount'))['t'] or Decimal('0.00')

            due_balance = delegate_total_consumed - delegate_total_settled
            events_count = Voucher.objects.filter(event__delegates=delegate).values('event').distinct().count()
            doctors_count = Voucher.objects.filter(event__delegates=delegate).values('doctor').distinct().count()
            
            delegate_data = {
                'delegate': delegate,
                'total_issued': delegate_total_issued,
                'total_consumed': delegate_total_consumed,
                'total_settled': delegate_total_settled,
                'due_balance': due_balance,
                'events_count': events_count,
                'doctors_count': doctors_count,
                'companies_detail': delegate_companies_detail,  # per-company breakdown
            }
            all_delegates_list.append(delegate_data)
            if due_balance > Decimal('0.00'):
                pending_delegates.append(delegate_data)
        context['pending_delegates'] = pending_delegates
        context['all_delegates_list'] = all_delegates_list
        
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
                from django.core.exceptions import ValidationError
                image = request.FILES.get('receipt_image')
                settlement = VendorSettlement(
                    vendor_id=vendor_id,
                    amount_settled=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    payment_method=method,
                    settlement_status='COMPLETED',
                    receipt_image=image
                )
                settlement.full_clean()
                settlement.save()
                messages.success(request, _("تم إصدار تسوية المورد بنجاح."))
            except ValidationError as e:
                # Get the first error message if exists
                err_msg = e.messages[0] if hasattr(e, 'messages') and e.messages else str(e)
                messages.error(request, f"خطأ في التسوية: {err_msg}")
            except Exception as e:
                messages.error(request, f"حدث خطأ: {e}")
                
        elif action == 'company_settlement':
            company_id = request.POST.get('company_id')
            amount = request.POST.get('amount')
            date_str = request.POST.get('date', datetime.date.today())
            notes = request.POST.get('notes', '')
            try:
                image = request.FILES.get('receipt_image')
                CompanySettlement.objects.create(
                    company_id=company_id,
                    settlement_amount=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    settlement_status='COMPLETED',
                    created_by=request.user,
                    receipt_image=image
                )
                messages.success(request, _("تم إصدار تسوية الشركة بنجاح."))
            except Exception as e:
                messages.error(request, f"حدث خطأ: {e}")
                
        elif action == 'update_company_settlement':
            settlement_id = request.POST.get('settlement_id')
            new_status = request.POST.get('status')
            try:
                settlement = CompanySettlement.objects.get(id=settlement_id)
                if new_status == 'COMPLETED':
                    settlement.settlement_status = 'COMPLETED'
                    settlement.save()
                    messages.success(request, _("تمت الموافقة على تسوية الشركة بنجاح."))
                elif new_status == 'REJECTED':
                    settlement.delete()
                    messages.success(request, _("تم رفض وحذف طلب التسوية."))
            except CompanySettlement.DoesNotExist:
                messages.error(request, _("طلب التسوية غير موجود."))
            except Exception as e:
                messages.error(request, f"حدث خطأ: {e}")
                
        elif action == 'delegate_settlement':
            delegate_id = request.POST.get('delegate_id')
            company_id = request.POST.get('company_id')
            amount = request.POST.get('amount')
            date_str = request.POST.get('date', datetime.date.today())
            notes = request.POST.get('notes', '')
            
            # Validation
            if not delegate_id:
                messages.error(request, _("يرجى تحديد المندوب."))
                return self.get(request, *args, **kwargs)
            if not company_id:
                messages.error(request, _("يرجى تحديد الشركة الدوائية المرتبطة بالمندوب."))
                return self.get(request, *args, **kwargs)
            if not amount or Decimal(amount) <= 0:
                messages.error(request, _("يرجى إدخال مبلغ صحيح."))
                return self.get(request, *args, **kwargs)
            
            try:
                image = request.FILES.get('receipt_image')
                DelegateSettlement.objects.create(
                    delegate_id=delegate_id,
                    company_id=company_id,
                    settlement_amount=Decimal(amount),
                    settlement_date=date_str,
                    notes=notes,
                    settlement_status='COMPLETED',
                    created_by=request.user,
                    receipt_image=image
                )
                messages.success(request, _("تم إصدار تسوية المندوب بنجاح."))
            except Exception as e:
                messages.error(request, f"حدث خطأ: {e}")

        elif action == 'delegate_settlement_all':
            # Settle ALL pending companies for this delegate in one go
            delegate_id = request.POST.get('delegate_id')
            date_str = request.POST.get('date', datetime.date.today())
            notes = request.POST.get('notes', '')
            image = request.FILES.get('receipt_image')

            if not delegate_id:
                messages.error(request, _("يرجى تحديد المندوب."))
                return self.get(request, *args, **kwargs)

            try:
                from events.models import Voucher as VoucherModel
                delegate_companies = PharmaceuticalCompany.objects.filter(
                    is_deleted=False,
                    events__delegates=delegate_id
                ).distinct()

                created_count = 0
                for company in delegate_companies:
                    d_c_vouchers = VoucherModel.objects.filter(
                        event__delegates=delegate_id,
                        company=company
                    )
                    c_consumed = sum((v.initial_value - v.current_balance) for v in d_c_vouchers)
                    c_settled = DelegateSettlement.objects.filter(
                        delegate_id=delegate_id,
                        company=company,
                        settlement_status='COMPLETED'
                    ).aggregate(t=Sum('settlement_amount'))['t'] or Decimal('0.00')
                    c_due = Decimal(str(c_consumed)) - c_settled

                    if c_due > Decimal('0.00'):
                        DelegateSettlement.objects.create(
                            delegate_id=delegate_id,
                            company=company,
                            settlement_amount=c_due,
                            settlement_date=date_str,
                            notes=notes,
                            settlement_status='COMPLETED',
                            created_by=request.user,
                            receipt_image=image if created_count == 0 else None
                        )
                        created_count += 1

                if created_count > 0:
                    messages.success(request, _(f"تم إصدار {created_count} تسوية للمندوب (جميع الشركات) بنجاح."))
                else:
                    messages.info(request, _("لا توجد مستحقات معلقة لهذا المندوب."))
            except Exception as e:
                messages.error(request, f"حدث خطأ في تسوية جميع الشركات: {e}")

        return self.get(request, *args, **kwargs)

from decimal import Decimal
from django.db.models import Sum, Q, Count
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages

class CustomEventsWizardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'custom_admin/events_wizard.html'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        import json
        
        from django.core.paginator import Paginator
        
        # Fetch events
        events_qs = Event.objects.select_related('company').prefetch_related('doctors', 'delegates').order_by('-date')
        
        # Pagination
        paginator = Paginator(events_qs, 10)  # Show 10 events per page
        page_number = self.request.GET.get('page')
        events_list = paginator.get_page(page_number)
        
        # Map event_id to a list of doctor_ids who already have a voucher for this event
        event_vouchers_map = {}
        
        # Calculate dynamic budget stats for each event
        for event in events_list:
            vouchers_stats = Voucher.objects.filter(event=event).aggregate(
                total_vouchers=Count('id'),
                total_initial=Sum('initial_value'),
                total_balance=Sum('current_balance')
            )
            event.total_vouchers = vouchers_stats['total_vouchers'] or 0
            event.total_initial = vouchers_stats['total_initial'] or Decimal('0.00')
            total_balance = vouchers_stats['total_balance'] or Decimal('0.00')
            event.total_spent = event.total_initial - total_balance
            
            # Save existing doctor IDs who already have a voucher for this event
            event_vouchers_map[event.id] = list(Voucher.objects.filter(event=event).values_list('doctor_id', flat=True))
            
            # Progress bar represents total vouchers distributed vs maximum budget
            if event.max_budget and event.max_budget > 0:
                event.progress_percentage = min(int((float(event.total_initial) / float(event.max_budget)) * 100), 100)
            else:
                event.progress_percentage = 0
            
            # Status badge
            event.is_active_campaign = event.date >= today

        # Fetch active direct (quick) vouchers (without an event and not expired)
        direct_vouchers = Voucher.objects.filter(event__isnull=True, expiry_date__gte=today).select_related('doctor', 'company').order_by('-issue_date')
        
        # Fetch expired vouchers
        expired_vouchers = Voucher.objects.filter(expiry_date__lt=today).select_related('doctor', 'event', 'company').order_by('-expiry_date')

        context.update({
            'events_list': events_list,
            'direct_vouchers': direct_vouchers,
            'expired_vouchers': expired_vouchers,
            'today': today,
            'companies_list': PharmaceuticalCompany.objects.filter(is_deleted=False).order_by('name'),
            'doctors_list': Doctor.objects.filter(is_deleted=False).order_by('name'),
            'delegates_list': Delegate.objects.filter(is_deleted=False).order_by('name'),
            'specialties_list': Specialty.objects.all().order_by('name'),
            'event_vouchers_json': json.dumps(event_vouchers_map),
        })
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'create_event':
            name = request.POST.get('name')
            date_str = request.POST.get('date')
            company_id = request.POST.get('company_id')
            max_budget_val = request.POST.get('max_budget', '0')
            voucher_val = request.POST.get('voucher_value', '0')
            voucher_expiry_days_val = request.POST.get('voucher_expiry_days', '90')
            payment_type = request.POST.get('payment_type', 'DEFERRED')
            notes = request.POST.get('notes', '')
            
            selected_specialties = request.POST.getlist('specialties')
            selected_delegates = request.POST.getlist('delegates')

            try:
                company = None
                if company_id:
                    company = PharmaceuticalCompany.objects.get(id=company_id, is_deleted=False)
                
                event = Event.objects.create(
                    name=name,
                    date=date_str,
                    company=company,
                    max_budget=Decimal(max_budget_val),
                    voucher_value=Decimal(voucher_val),
                    voucher_expiry_days=int(voucher_expiry_days_val),
                    payment_type=payment_type,
                    notes=notes
                )
                
                if selected_specialties:
                    event.specialties.set(selected_specialties)
                if selected_delegates:
                    event.delegates.set(selected_delegates)
                    
                messages.success(request, f"تم إطلاق الفعالية '{name}' بنجاح.")
            except Exception as e:
                messages.error(request, f"خطأ أثناء إنشاء الفعالية: {str(e)}")
                
        elif action == 'generate_vouchers':
            event_id = request.POST.get('event_id')
            doctor_ids = request.POST.getlist('doctor_ids')
            voucher_value_val = request.POST.get('voucher_value', '0')
            expiry_date_str = request.POST.get('expiry_date')
            company_id = request.POST.get('company_id')
            notes = request.POST.get('notes', '')

            from datetime import datetime
            expiry_date = None
            if expiry_date_str:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()

            try:
                voucher_value = Decimal(voucher_value_val)
                total_new_vouchers = voucher_value * len(doctor_ids)
                
                event = None
                company = None

                if event_id:
                    event = Event.objects.get(id=event_id)
                    company = event.company
                    # Check event maximum budget
                    if event.max_budget > 0:
                        current_distributed = Voucher.objects.filter(event=event).aggregate(sum=Sum('initial_value'))['sum'] or Decimal('0.00')
                        remaining_budget = event.max_budget - current_distributed
                        
                        if total_new_vouchers > remaining_budget:
                            messages.error(request, f"فشل شحن القسائم: الميزانية المتبقية للفعالية غير كافية! المتبقي: {remaining_budget} ج.م، القيمة المطلوبة: {total_new_vouchers} ج.م.")
                            return redirect('custom_events')
                elif company_id:
                    company = PharmaceuticalCompany.objects.get(id=company_id)

                created_count = 0
                for doc_id in doctor_ids:
                    # Avoid duplicate voucher for same doctor in same event
                    if event and Voucher.objects.filter(event=event, doctor_id=doc_id).exists():
                        continue
                        
                    Voucher.objects.create(
                        doctor_id=doc_id,
                        event=event,
                        company=company,
                        initial_value=voucher_value,
                        current_balance=voucher_value,
                        expiry_date=expiry_date,
                        notes=notes
                    )
                    
                    if event:
                        event.doctors.add(doc_id)
                    created_count += 1
                        
                if created_count > 0:
                    messages.success(request, f"تم بنجاح شحن قسائم لعدد {created_count} طبيب بقيمة {voucher_value} ج.م لكل طبيب.")
                else:
                    messages.info(request, _("لم يتم إنشاء أي قسائم جديدة، ربما تم شحن قسائم لهؤلاء الأطباء مسبقاً في هذه الفعالية."))
            except Exception as e:
                messages.error(request, f"خطأ أثناء توليد القسائم: {str(e)}")

        return redirect('custom_events')




class CustomDoctorPortalView(DoctorPortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/doctor_portal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = getattr(self.request.user, 'doctor_profile', None)
        
        # Initialize default values
        total_balance = Decimal('0.00')
        monthly_spending = Decimal('0.00')
        active_vouchers_count = 0
        recent_transactions = []
        active_vouchers = []

        if doctor:
            # Logic for Real Data Integration
            today = timezone.now().date()
            active_vouchers_qs = Voucher.objects.filter(
                doctor=doctor, 
                is_active=True, 
                expiry_date__gte=today
            )
            
            # 1. Total Balance
            total_balance = active_vouchers_qs.aggregate(Sum('current_balance'))['current_balance__sum'] or Decimal('0.00')
            
            # 2. Monthly Spending
            thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
            monthly_spending = Transaction.objects.filter(
                doctor=doctor, 
                transaction_date__gte=thirty_days_ago
            ).aggregate(Sum('amount_spent'))['amount_spent__sum'] or Decimal('0.00')
            
            # 3. Active Vouchers Count
            active_vouchers_count = active_vouchers_qs.count()
            
            # 4. Recent Transactions
            recent_transactions = Transaction.objects.filter(
                doctor=doctor
            ).select_related('vendor').order_by('-transaction_date')[:5]

            # 5. Recent Transfers
            from events.models import VoucherTransfer
            recent_transfers = VoucherTransfer.objects.filter(
                Q(from_doctor=doctor) | Q(to_doctor=doctor)
            ).select_related('from_doctor', 'to_doctor', 'voucher').order_by('-transfer_date')[:5]
            
            active_vouchers = active_vouchers_qs

        context.update({
            'doctor': doctor,
            'total_balance': total_balance,
            'monthly_spending': monthly_spending,
            'active_vouchers_count': active_vouchers_count,
            'recent_transactions': recent_transactions,
            'recent_transfers': recent_transfers,
            'active_vouchers': active_vouchers,
        })
        return context

class CustomDoctorVouchersView(DoctorPortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/doctor_vouchers.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = getattr(self.request.user, 'doctor_profile', None)
        
        today = timezone.now().date()
        active_vouchers = Voucher.objects.filter(
            doctor=doctor, 
            is_active=True, 
            expiry_date__gte=today
        ).order_by('-created_at')
        
        expired_vouchers = Voucher.objects.filter(
            Q(doctor=doctor) & (Q(is_active=False) | Q(expiry_date__lt=today))
        ).order_by('-created_at')

        # Get vouchers transferred by this doctor
        from events.models import VoucherTransfer
        transfers_made = VoucherTransfer.objects.filter(
            from_doctor=doctor
        ).select_related('to_doctor', 'voucher', 'voucher__event').order_by('-transfer_date')

        context.update({
            'doctor': doctor,
            'active_vouchers': active_vouchers,
            'expired_vouchers': expired_vouchers,
            'transfers_made': transfers_made,
        })
        return context

class CustomDoctorTransactionsView(DoctorPortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/doctor_transactions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = getattr(self.request.user, 'doctor_profile', None)
        
        all_transactions = Transaction.objects.filter(
            doctor=doctor
        ).select_related('vendor', 'created_by').order_by('-transaction_date')

        context.update({
            'doctor': doctor,
            'all_transactions': all_transactions,
        })
        return context

class CustomDoctorTransfersView(DoctorPortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/doctor_transfers.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = getattr(self.request.user, 'doctor_profile', None)
        
        # Transfers Made (Sent)
        transfers_made = doctor.transfers_made.all().select_related('to_doctor', 'voucher', 'voucher__event').order_by('-transfer_date')
        
        # Transfers Received (Received)
        transfers_received = doctor.transfers_received.all().select_related('from_doctor', 'voucher', 'voucher__event').order_by('-transfer_date')

        context.update({
            'doctor': doctor,
            'transfers_made': transfers_made,
            'transfers_received': transfers_received,
        })
        return context

class CustomDoctorSettingsView(DoctorPortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/doctor_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctor'] = getattr(self.request.user, 'doctor_profile', None)
        return context

    def post(self, request, *args, **kwargs):
        doctor = getattr(request.user, 'doctor_profile', None)
        if not doctor:
            return redirect('login')

        action = request.POST.get('action')

        if action == 'update_profile':
            doctor.name = request.POST.get('name', doctor.name)
            doctor.phone = request.POST.get('phone', doctor.phone)
            doctor.email = request.POST.get('email', doctor.email)
            if 'profile_picture' in request.FILES:
                doctor.profile_picture = request.FILES['profile_picture']
            doctor.save()
            messages.success(request, _("تم تحديث البيانات الشخصية بنجاح."))

        elif action == 'change_password':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if new_password != confirm_password:
                messages.error(request, _("كلمتا المرور غير متطابقتين."))
            elif len(new_password) < 6:
                messages.error(request, _("كلمة المرور يجب أن تكون 6 أحرف على الأقل."))
            else:
                request.user.set_password(new_password)
                request.user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                messages.success(request, _("تم تغيير كلمة المرور بنجاح."))
        
        return redirect("custom_doctor_settings")

class CustomDoctorCardView(DoctorPortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/doctor_card.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = getattr(self.request.user, 'doctor_profile', None)
        context['doctor'] = doctor
        if doctor:
            context['qr_url'] = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={doctor.qr_code}&color=005353"
        return context

class SendTransferOTPView(LoginRequiredMixin, View):
    def post(self, request):
        import json
        try:
            data = json.loads(request.body)
        except:
            data = request.POST
            
        voucher_id = data.get('voucher_id')
        target_search = data.get('target_search')
        
        if not voucher_id or not target_search:
            return JsonResponse({'success': False, 'error': 'بيانات ناقصة.'}, status=400)
            
        try:
            voucher = Voucher.objects.get(id=voucher_id)
            from_doctor = getattr(request.user, 'doctor_profile', None)
            
            if not from_doctor or voucher.doctor != from_doctor:
                return JsonResponse({'success': False, 'error': 'لا تملك صلاحية تحويل هذه القسيمة.'}, status=403)
            
            # Lookup target doctor
            q_filter = Q(phone=target_search) | Q(name__icontains=target_search) | Q(qr_code=target_search)
            to_doctor = Doctor.objects.filter(q_filter).first()
            
            if not to_doctor:
                return JsonResponse({'success': False, 'error': 'الطبيب المستلم غير موجود.'}, status=404)
            
            if to_doctor == from_doctor:
                return JsonResponse({'success': False, 'error': 'لا يمكن تحويل القسيمة لنفسك.'}, status=400)

            from core.services import generate_otp, send_transfer_otp_email
            otp = generate_otp()
            token = send_transfer_otp_email(from_doctor, to_doctor, voucher, otp)
            
            if token:
                return JsonResponse({
                    'success': True,
                    'token': token,
                    'recipient_name': to_doctor.name
                })
            else:
                return JsonResponse({'success': False, 'error': 'فشل إرسال الرمز. تأكد من إعدادات البريد.'}, status=500)
                
        except Voucher.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'القسيمة غير موجودة.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class CustomVendorPortalView(LoginRequiredMixin, VendorAdminRequiredMixin, TemplateView):
    template_name = "custom_admin/vendor_portal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        vendor = getattr(user, "vendor_profile", None)
        if not vendor:
             if user.is_staff or user.is_superuser:
                vendor, created = Vendor.objects.get_or_create(
                    user=user,
                    defaults={
                        "name": f"إدارة: {user.username}",
                        "contact_person": user.get_full_name() or user.username,
                        "phone": user.phone or "01000000000",
                        "email": user.email or "admin@hadramout.com",
                        "address": "المقر الرئيسي",
                        "category": "إدارة عامة",
                        "role": "ADMIN"
                    }
                )
             else:
                raise PermissionDenied("لم يتم العثور على ملف بائع لهذا الحساب.")
        
        from django.db.models import Q, Sum
        from decimal import Decimal
        
        if vendor.role == "ADMIN":
            all_transactions = Transaction.objects.filter(
                Q(vendor=vendor) | Q(vendor__parent_vendor=vendor)
            ).order_by("-transaction_date")
            
            all_settlements = VendorSettlement.objects.filter(
                Q(vendor=vendor) | Q(vendor__parent_vendor=vendor)
            ).order_by("-settlement_date")
        else:
            all_transactions = Transaction.objects.filter(
                created_by=user
            ).order_by("-transaction_date")
            all_settlements = VendorSettlement.objects.none()

        from django.utils import timezone
        import datetime
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        total_earned = all_transactions.aggregate(Sum("total_deducted"))["total_deducted__sum"] or Decimal("0.00")
        total_paid = all_settlements.aggregate(Sum("amount_settled"))["amount_settled__sum"] or Decimal("0.00")
        total_pending = total_earned - total_paid

        context["vendor"] = vendor
        context["total_sales"] = total_earned
        context["total_paid"] = total_paid
        context["total_pending"] = total_pending
        total_transactions_count = all_transactions.count()
        context["total_transactions_count"] = total_transactions_count
        context["avg_transaction_value"] = total_earned / total_transactions_count if total_transactions_count > 0 else Decimal("0.00")
        
        context["recent_transactions"] = all_transactions[:10]
        context["today_transactions"] = all_transactions.filter(transaction_date__gte=today_start)[:10]
        context["all_invoices"] = all_transactions[:100]
        context["all_settlements"] = all_settlements
        
        if vendor.role == "ADMIN":
            context["cashiers"] = vendor.cashiers_list.all().select_related("user")
        else:
            context["cashiers"] = []
            
        from django.db.models.functions import TruncDate
        import json
        
        today = timezone.now().date()
        last_7_days = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
        
        sales_by_date = all_transactions.filter(
            transaction_date__gte=timezone.now() - datetime.timedelta(days=6)
        ).annotate(
            date=TruncDate("transaction_date")
        ).values("date").annotate(
            total=Sum("amount_spent")
        ).order_by("date")
        
        sales_dict = {item["date"]: item["total"] for item in sales_by_date}
        
        chart_labels = [date.strftime("%b %d") for date in last_7_days]
        chart_data = [float(sales_dict.get(date, 0)) for date in last_7_days]
        
        context["chart_labels_json"] = json.dumps(chart_labels, ensure_ascii=False)
        context["chart_data_json"] = json.dumps(chart_data)
        
        if user.is_staff:
            context["is_admin_view"] = True
            
        return context

class VendorActionView(LoginRequiredMixin, VendorAdminRequiredMixin, View):
    """Handle various vendor actions like updating settings or managing cashiers."""
    def post(self, request):
        action = request.POST.get('action')
        vendor = request.user.vendor_profile

        if action == 'update_financial':
            if vendor.role != 'ADMIN':
                 return JsonResponse({'success': False, 'error': 'غير مسموح للكاشير بتعديل البيانات المالية.'}, status=403)
            vendor.bank_info = request.POST.get('bank_info', '')
            vendor.wallet_info = request.POST.get('wallet_info', '')
            vendor.other_info = request.POST.get('other_info', '')
            vendor.save()
            messages.success(request, _("تم تحديث البيانات المالية بنجاح."))
            return JsonResponse({'success': True})

        elif action == 'change_cashier_password':
            # This is okay for admin only (Mixin handles view access, but we check role inside for safety)
            if vendor.role != 'ADMIN':
                 return JsonResponse({'success': False, 'error': 'غير مسموح للكاشير بتعديل كلمات مرور الموظفين.'}, status=403)
            cashier_id = request.POST.get('cashier_id')
            new_password = request.POST.get('new_password')
            if not new_password or len(new_password) < 6:
                return JsonResponse({'success': False, 'error': 'كلمة المرور يجب أن تكون 6 أحرف على الأقل.'}, status=400)
            
            cashier_vendor = get_object_or_404(Vendor, id=cashier_id, parent_vendor=vendor, role='CASHIER')
            user = cashier_vendor.user
            user.password = make_password(new_password)
            user.save()
            return JsonResponse({'success': True, 'message': 'تم تغيير كلمة المرور بنجاح.'})

        elif action == 'update_profile':
            if vendor.role != 'ADMIN':
                 return JsonResponse({'success': False, 'error': 'غير مسموح للكاشير بتعديل ملف المؤسسة.'}, status=403)
            vendor.name = request.POST.get('name', vendor.name)
            vendor.contact_person = request.POST.get('contact_person', vendor.contact_person)
            vendor.phone = request.POST.get('phone', vendor.phone)
            vendor.email = request.POST.get('email', vendor.email)
            vendor.address = request.POST.get('address', vendor.address)
            vendor.category = request.POST.get('category', vendor.category)
            
            if 'logo' in request.FILES:
                vendor.logo = request.FILES['logo']
            
            vendor.save()
            messages.success(request, _("تم تحديث الملف الشخصي بنجاح."))
            return JsonResponse({'success': True})

        elif action == 'change_admin_password':
            if vendor.role != 'ADMIN':
                 return JsonResponse({'success': False, 'error': 'غير مسموح للكاشير بتغيير كلمة سر الإدارة.'}, status=403)
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not request.user.check_password(current_password):
                return JsonResponse({'success': False, 'error': 'كلمة المرور الحالية غير صحيحة.'}, status=400)
            
            if new_password != confirm_password:
                return JsonResponse({'success': False, 'error': 'كلمتا المرور الجديدتان غير متطابقتين.'}, status=400)
            
            if len(new_password) < 6:
                return JsonResponse({'success': False, 'error': 'كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل.'}, status=400)
                
            from django.contrib.auth import update_session_auth_hash
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            return JsonResponse({'success': True, 'message': 'تم تغيير كلمة المرور بنجاح.'})

        return JsonResponse({'success': False, 'error': 'إجراء غير صالح.'}, status=400)

class CustomLoginGatewayView(TemplateView):
    template_name = 'custom_admin/login_gateway.html'

class CustomRegisterGatewayView(TemplateView):
    template_name = 'custom_admin/register_gateway.html'

class CustomSystemSettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'custom_admin/system_settings.html'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Staff Users
        staff_users = User.objects.filter(is_staff=True).order_by('username')
        context['staff_users'] = staff_users
        
        # 2. Vendors with fee settings
        from django.core.paginator import Paginator
        vendors_list = Vendor.objects.filter(role='ADMIN', is_deleted=False).order_by('-created_at')
        paginator = Paginator(vendors_list, 10) # Show 10 vendors per page
        page_number = self.request.GET.get('page')
        vendors = paginator.get_page(page_number)
        context['vendors'] = vendors
        
        # 3. Admin Vendor profile
        admin_vendor = getattr(self.request.user, "vendor_profile", None)
        context['admin_vendor'] = admin_vendor
        
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        admin_vendor = getattr(request.user, "vendor_profile", None)

        if action == 'update_vendor_fee':
            vendor_id = request.POST.get('vendor_id')
            fee_percentage = request.POST.get('fee_percentage')
            has_fee = request.POST.get('has_management_fee') == 'on'
            
            vendor = get_object_or_404(Vendor, id=vendor_id)
            if fee_percentage:
                vendor.management_fee_percentage = fee_percentage
            vendor.has_management_fee = has_fee
            vendor.save()
            messages.success(request, f"تم تحديث إعدادات {vendor.name} بنجاح.")
            return redirect('custom_settings')

        elif action == 'toggle_vendor_status':
            vendor_id = request.POST.get('vendor_id')
            vendor = get_object_or_404(Vendor, id=vendor_id)
            vendor.is_active = not vendor.is_active
            vendor.save()
            status_text = "تفعيل" if vendor.is_active else "إيقاف"
            messages.success(request, f"تم {status_text} حساب المورد {vendor.name} بنجاح.")
            return redirect('custom_settings')

        elif action == 'toggle_staff_status':
            user_id = request.POST.get('user_id')
            staff_user = get_object_or_404(User, id=user_id)
            if staff_user == request.user:
                messages.error(request, _("لا يمكنك إيقاف حسابك الخاص."))
            else:
                staff_user.is_active = not staff_user.is_active
                staff_user.save()
                status_text = "تفعيل" if staff_user.is_active else "إيقاف"
                messages.success(request, f"تم {status_text} حساب {staff_user.username} بنجاح.")
            return redirect('custom_settings')

        elif action == 'change_admin_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not request.user.check_password(current_password):
                messages.error(request, _('كلمة المرور الحالية غير صحيحة.'))
            elif new_password != confirm_password:
                messages.error(request, _('كلمتا المرور الجديدتان غير متطابقتين.'))
            elif len(new_password) < 6:
                messages.error(request, _('كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل.'))
            else:
                from django.contrib.auth import update_session_auth_hash
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, _('تم تغيير كلمة المرور بنجاح.'))
            return redirect('custom_settings')
            
        elif action == 'update_profile' and admin_vendor:
            admin_vendor.name = request.POST.get('name', admin_vendor.name)
            admin_vendor.contact_person = request.POST.get('contact_person', admin_vendor.contact_person)
            admin_vendor.phone = request.POST.get('phone', admin_vendor.phone)
            admin_vendor.email = request.POST.get('email', admin_vendor.email)
            admin_vendor.address = request.POST.get('address', admin_vendor.address)
            
            if 'logo' in request.FILES:
                admin_vendor.logo = request.FILES['logo']
            
            admin_vendor.save()
            messages.success(request, _("تم تحديث الملف الشخصي بنجاح."))
            return redirect('custom_settings')
            
        elif action == 'update_financial' and admin_vendor:
            admin_vendor.bank_info = request.POST.get('bank_info', '')
            admin_vendor.wallet_info = request.POST.get('wallet_info', '')
            admin_vendor.other_info = request.POST.get('other_info', '')
            admin_vendor.save()
            messages.success(request, _("تم تحديث البيانات المالية بنجاح."))
            return redirect('custom_settings')
            
        elif action == 'update_admin_user':
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            email = request.POST.get('email', '')
            
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.save()
            messages.success(request, _("تم تحديث بيانات حسابك الشخصي بنجاح."))
            return redirect('custom_settings')

        messages.error(request, _('إجراء غير صالح.'))
        return redirect('custom_settings')

class CustomCompaniesView(LoginRequiredMixin, VendorOwnerRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        specialty_id = request.GET.get('specialty')
        status_filter = request.GET.get('status')
        entity_type = request.GET.get('entity_type', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        
        from django.db.models import Sum, F, DecimalField, Case, When
        from django.db.models.functions import Coalesce

        companies = PharmaceuticalCompany.objects.filter(is_deleted=False).prefetch_related('delegates', 'specialties').order_by('-created_at')
        companies = companies.annotate(
            total_sponsored=Coalesce(Sum('voucher__initial_value'), 0.0, output_field=DecimalField()),
            total_current=Coalesce(Sum(Case(When(voucher__is_active=True, then=F('voucher__current_balance')), default=0.0, output_field=DecimalField())), 0.0, output_field=DecimalField()),
            total_settled=Coalesce(Sum('settlements__settlement_amount'), 0.0, output_field=DecimalField()),
        ).annotate(
            net_balance=F('total_sponsored') - F('total_current') - F('total_settled')
        )
        
        delegates = Delegate.objects.filter(is_deleted=False).prefetch_related('companies', 'specialties').order_by('name')
        delegates = delegates.annotate(
            net_balance=Coalesce(Sum(Case(When(events__vouchers__is_active=True, then=F('events__vouchers__current_balance')), default=0.0, output_field=DecimalField())), 0.0, output_field=DecimalField())
        )
        
        if query:
            companies = companies.filter(Q(name__icontains=query) | Q(contact_person__icontains=query) | Q(phone__icontains=query))
            delegates = delegates.filter(Q(name__icontains=query) | Q(phone__icontains=query))
            
        if specialty_id:
            companies = companies.filter(specialties__id=specialty_id).distinct()
            delegates = delegates.filter(specialties__id=specialty_id).distinct()
            
        if status_filter == 'active':
            companies = companies.filter(user__is_active=True)
            delegates = delegates.filter(user__is_active=True)
        elif status_filter == 'inactive':
            companies = companies.filter(Q(user__isnull=True) | Q(user__is_active=False))
            delegates = delegates.filter(Q(user__isnull=True) | Q(user__is_active=False))

        if date_from:
            companies = companies.filter(created_at__date__gte=date_from)
            delegates = delegates.filter(user__date_joined__date__gte=date_from)
        if date_to:
            companies = companies.filter(created_at__date__lte=date_to)
            delegates = delegates.filter(user__date_joined__date__lte=date_to)

        if entity_type == 'company':
            delegates = delegates.none()
        elif entity_type == 'delegate':
            companies = companies.none()
            
        archived_companies = PharmaceuticalCompany.objects.filter(is_deleted=True).order_by('-updated_at')
        archived_delegates = Delegate.objects.filter(is_deleted=True).order_by('name')

        specialties = Specialty.objects.all()
        
        # Pop duplicate info from session to pass to template
        duplicate_entity_id = request.session.pop('duplicate_entity_id', None)
        duplicate_entity_name = request.session.pop('duplicate_entity_name', None)
        duplicate_entity_type = request.session.pop('duplicate_entity_type', None)
        
        context = {
            'companies': companies,
            'delegates': delegates,
            'archived_companies': archived_companies,
            'archived_delegates': archived_delegates,
            'specialties': specialties,
            'query': query,
            'current_specialty': specialty_id,
            'current_status': status_filter,
            'current_entity_type': entity_type,
            'date_from': date_from,
            'date_to': date_to,
            'duplicate_entity_id': duplicate_entity_id,
            'duplicate_entity_name': duplicate_entity_name,
            'duplicate_entity_type': duplicate_entity_type,
        }
        return render(request, 'custom_admin/companies_directory.html', context)
        
    def post(self, request):
        action = request.POST.get('action')
        
        if action == 'add_company':
            name = request.POST.get('name')
            contact_person = request.POST.get('contact_person')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            # 1. Check if user already exists
            duplicate_user = User.objects.filter(username=username).first()
            duplicate = None
            duplicate_type = None
            
            if duplicate_user:
                if hasattr(duplicate_user, 'company_profile'):
                    duplicate = duplicate_user.company_profile
                    duplicate_type = 'company'
                elif hasattr(duplicate_user, 'delegate_profile'):
                    duplicate = duplicate_user.delegate_profile
                    duplicate_type = 'delegate'
                elif hasattr(duplicate_user, 'doctor_profile'):
                    duplicate = duplicate_user.doctor_profile
                    duplicate_type = 'doctor'
            
            # 2. Check by name, phone, or email in other entities if no duplicate found yet
            if not duplicate:
                # Check in PharmaceuticalCompany
                duplicate_comp = PharmaceuticalCompany.objects.filter(
                    Q(name__iexact=name) | Q(phone=phone) | Q(email=email)
                ).filter(is_deleted=False).first()
                if duplicate_comp:
                    duplicate = duplicate_comp
                    duplicate_type = 'company'
                    
            if not duplicate:
                # Check in Delegate
                delegate_qs = Delegate.objects.filter(
                    Q(phone=phone)
                ).filter(is_deleted=False)
                # Keep delegate phone unique, check by name too
                if name:
                    delegate_qs = delegate_qs | Delegate.objects.filter(name__iexact=name).filter(is_deleted=False)
                duplicate_del = delegate_qs.first()
                if duplicate_del:
                    duplicate = duplicate_del
                    duplicate_type = 'delegate'
                    
            if not duplicate:
                # Check in Doctor
                from accounts.models import Doctor
                duplicate_doc = Doctor.objects.filter(
                    Q(phone=phone) | Q(email=email)
                ).filter(is_deleted=False).first()
                if duplicate_doc:
                    duplicate = duplicate_doc
                    duplicate_type = 'doctor'
                    
            if duplicate and not getattr(duplicate, 'is_deleted', False):
                request.session['duplicate_entity_id'] = duplicate.id
                request.session['duplicate_entity_name'] = duplicate.name
                request.session['duplicate_entity_type'] = duplicate_type
                
                type_label = 'الشركة' if duplicate_type == 'company' else ('المندوب' if duplicate_type == 'delegate' else 'الطبيب')
                messages.error(request, f"البيانات مسجلة مسبقاً باسم {type_label}: {duplicate.name}")
                return redirect('custom_companies')
                
            if duplicate_user:
                messages.error(request, _('اسم المستخدم (Login) مسجل مسبقاً لمستخدم آخر في النظام.'))
                return redirect('custom_companies')
                
            try:
                user = User.objects.create_user(username=username, password=password, email=email, first_name=name)
                user.type = User.Types.COMPANY
                user.save()
                
                PharmaceuticalCompany.objects.create(
                    user=user,
                    name=name,
                    contact_person=contact_person,
                    email=email,
                    phone=phone,
                    address=address
                )
                messages.success(request, f'تم إضافة وتسجيل الشركة "{name}" بنجاح.')
                
                # ── إشعار للإدارة عند إضافة شركة جديدة ──
                try:
                    from core.models import Notification
                    admin_users = User.objects.filter(is_staff=True, is_active=True)
                    for admin_user in admin_users:
                        Notification.objects.create(
                            user=admin_user,
                            message=f"تم إضافة شركة جديدة: {name}",
                            notification_type='ACCOUNT',
                            link='/custom-companies/'
                        )
                except Exception:
                    pass
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء الإضافة: {str(e)}')
                
        elif action == 'add_delegate':
            name = request.POST.get('name')
            phone = request.POST.get('phone')
            username = request.POST.get('username')
            password = request.POST.get('password')
            company_ids = request.POST.getlist('company_ids')
            specialty_ids = request.POST.getlist('specialty_ids')
            
            # 1. Check if user already exists
            duplicate_user = User.objects.filter(username=username).first()
            duplicate = None
            duplicate_type = None
            
            if duplicate_user:
                if hasattr(duplicate_user, 'delegate_profile'):
                    duplicate = duplicate_user.delegate_profile
                    duplicate_type = 'delegate'
                elif hasattr(duplicate_user, 'company_profile'):
                    duplicate = duplicate_user.company_profile
                    duplicate_type = 'company'
                elif hasattr(duplicate_user, 'doctor_profile'):
                    duplicate = duplicate_user.doctor_profile
                    duplicate_type = 'doctor'
                    
            # 2. Check by name or phone in other entities if no duplicate found yet
            if not duplicate:
                # Check in Delegate
                delegate_qs = Delegate.objects.filter(
                    Q(phone=phone)
                ).filter(is_deleted=False)
                if name:
                    delegate_qs = delegate_qs | Delegate.objects.filter(name__iexact=name).filter(is_deleted=False)
                duplicate_del = delegate_qs.first()
                if duplicate_del:
                    duplicate = duplicate_del
                    duplicate_type = 'delegate'
                    
            if not duplicate:
                # Check in PharmaceuticalCompany
                duplicate_comp = PharmaceuticalCompany.objects.filter(
                    Q(phone=phone) | Q(name__iexact=name)
                ).filter(is_deleted=False).first()
                if duplicate_comp:
                    duplicate = duplicate_comp
                    duplicate_type = 'company'
                    
            if not duplicate:
                # Check in Doctor
                from accounts.models import Doctor
                duplicate_doc = Doctor.objects.filter(
                    Q(phone=phone)
                ).filter(is_deleted=False).first()
                if duplicate_doc:
                    duplicate = duplicate_doc
                    duplicate_type = 'doctor'
                    
            if duplicate and not getattr(duplicate, 'is_deleted', False):
                request.session['duplicate_entity_id'] = duplicate.id
                request.session['duplicate_entity_name'] = duplicate.name
                request.session['duplicate_entity_type'] = duplicate_type
                
                type_label = 'المندوب' if duplicate_type == 'delegate' else ('الشركة' if duplicate_type == 'company' else 'الطبيب')
                messages.error(request, f"البيانات مسجلة مسبقاً باسم {type_label}: {duplicate.name}")
                return redirect('custom_companies')
                
            if duplicate_user:
                messages.error(request, _('اسم المستخدم (Login) مسجل مسبقاً لمستخدم آخر في النظام.'))
                return redirect('custom_companies')
                
            try:
                user = User.objects.create_user(username=username, password=password, first_name=name)
                user.type = User.Types.DELEGATE
                user.save()
                
                delegate = Delegate.objects.create(
                    user=user,
                    name=name,
                    phone=phone
                )
                
                if company_ids:
                    delegate.companies.set(company_ids)
                if specialty_ids:
                    delegate.specialties.set(specialty_ids)
                    
                messages.success(request, f'تم إضافة وتسجيل المندوب "{name}" بنجاح.')
                
                # ── إشعار للإدارة عند إضافة مندوب جديد ──
                try:
                    from core.models import Notification
                    admin_users = User.objects.filter(is_staff=True, is_active=True)
                    for admin_user in admin_users:
                        Notification.objects.create(
                            user=admin_user,
                            message=f"تم إضافة مندوب جديد: {name}",
                            notification_type='ACCOUNT',
                            link='/custom-companies/'
                        )
                except Exception:
                    pass
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء الإضافة: {str(e)}')

        elif action == 'bulk_action':
            bulk_type = request.POST.get('bulk_action_type')
            entity_type = request.POST.get('entity_type')
            selected_ids = request.POST.get('selected_ids', '').split(',')
            selected_ids = [id for id in selected_ids if id.isdigit()]
            
            if selected_ids:
                if entity_type == 'company':
                    qs = PharmaceuticalCompany.objects.filter(id__in=selected_ids)
                elif entity_type == 'delegate':
                    qs = Delegate.objects.filter(id__in=selected_ids)
                else:
                    qs = None
                    
                if qs:
                    if bulk_type == 'activate':
                        users_ids = [obj.user.id for obj in qs if obj.user]
                        User.objects.filter(id__in=users_ids).update(is_active=True)
                        messages.success(request, _('تم تنشيط الحسابات المحددة بنجاح.'))
                    elif bulk_type == 'deactivate':
                        users_ids = [obj.user.id for obj in qs if obj.user]
                        User.objects.filter(id__in=users_ids).update(is_active=False)
                        messages.success(request, _('تم إيقاف الحسابات المحددة بنجاح.'))
                    elif bulk_type == 'delete':
                        from datetime import datetime
                        for obj in qs:
                            if not obj.is_deleted:
                                obj.is_deleted = True
                                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                                if entity_type == 'company':
                                    obj.name = f"{obj.name}_del_{timestamp}"
                                elif entity_type == 'delegate':
                                    obj.phone = f"{obj.phone}_del_{timestamp}"
                                
                                if obj.user:
                                    user = obj.user
                                    user.is_active = False
                                    user.username = f"del_{timestamp}_{user.username}"
                                    if user.email:
                                        user.email = f"del_{timestamp}_{user.email}"
                                    user.save()
                                obj.save()
                        messages.success(request, _('تم حذف العناصر المحددة بنجاح.'))
                        
        return redirect('custom_companies')

class CustomCompanyProfileView(LoginRequiredMixin, VendorOwnerRequiredMixin, DetailView):
    model = PharmaceuticalCompany
    template_name = 'custom_admin/company_profile.html'
    context_object_name = 'company'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_object()
        
        # Associated delegates
        context['delegates'] = company.delegates.all()
        context['all_delegates'] = Delegate.objects.filter(is_deleted=False)
        
        # Associated specialties
        context['specialties'] = company.specialties.all()
        from accounts.models import Specialty
        context['all_specialties'] = Specialty.objects.all()
        
        # Vouchers sponsored by this company
        vouchers = Voucher.objects.filter(company=company)
        context['vouchers'] = vouchers
        
        # Aggregate financial data
        context['total_sponsored_amount'] = vouchers.aggregate(total=Sum('initial_value'))['total'] or Decimal('0.00')
        context['total_current_balance'] = vouchers.filter(is_active=True).aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
        context['total_spent_amount'] = context['total_sponsored_amount'] - context['total_current_balance']
        
        # Settlements
        from core.models import CompanySettlement
        context['total_settled_amount'] = CompanySettlement.objects.filter(company=company).aggregate(total=Sum('settlement_amount'))['total'] or Decimal('0.00')
        context['net_due_balance'] = context['total_spent_amount'] - context['total_settled_amount']
        
        # Breakdown by Delegate vs Direct
        # Vouchers from events without any delegate (direct by company)
        direct_vouchers = vouchers.filter(event__delegates__isnull=True)
        direct_sponsored = direct_vouchers.aggregate(total=Sum('initial_value'))['total'] or Decimal('0.00')
        direct_current = direct_vouchers.filter(is_active=True).aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
        context['direct_spent_amount'] = direct_sponsored - direct_current
        
        # Breakdown per delegate
        delegate_breakdowns = []
        for delegate in context['delegates']:
            del_vouchers = vouchers.filter(event__delegates=delegate)
            del_sponsored = del_vouchers.aggregate(total=Sum('initial_value'))['total'] or Decimal('0.00')
            del_current = del_vouchers.filter(is_active=True).aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
            del_spent = del_sponsored - del_current
            if del_spent > 0:
                delegate_breakdowns.append({
                    'delegate': delegate,
                    'spent_amount': del_spent
                })
        context['delegate_breakdowns'] = delegate_breakdowns
        
        return context

    def post(self, request, *args, **kwargs):
        company = self.get_object()
        action = request.POST.get('action')
        
        if action == 'edit_profile':
            company.name = request.POST.get('name', company.name)
            company.contact_person = request.POST.get('contact_person', company.contact_person)
            company.email = request.POST.get('email', company.email)
            company.phone = request.POST.get('phone', company.phone)
            company.address = request.POST.get('address', company.address)
            company.save()
            
            # Optionally update user's name
            if company.user:
                company.user.first_name = company.name
                company.user.email = company.email
                company.user.save()
                
            messages.success(request, _('تم تحديث بيانات الشركة بنجاح.'))
            
        elif action == 'change_password':
            if company.user:
                new_password = request.POST.get('new_password')
                if new_password and len(new_password) >= 6:
                    company.user.set_password(new_password)
                    company.user.save()
                    messages.success(request, _('تم تحديث كلمة المرور بنجاح.'))
                else:
                    messages.error(request, _('كلمة المرور يجب أن تكون 6 أحرف على الأقل.'))
            else:
                messages.error(request, _('هذه الشركة لا تملك حساب دخول.'))
                
        elif action == 'toggle_status':
            if company.user:
                company.user.is_active = not company.user.is_active
                company.user.save()
                status = 'تنشيط' if company.user.is_active else 'إيقاف'
                messages.success(request, f'تم {status} حساب الشركة بنجاح.')
                
        elif action == 'manage_associations':
            delegate_ids = request.POST.getlist('delegate_ids')
            specialty_ids = request.POST.getlist('specialty_ids')
            
            # First remove company from all its current delegates
            for d in company.delegates.all():
                d.companies.remove(company)
            # Then add company to newly selected delegates
            if delegate_ids:
                selected_delegates = Delegate.objects.filter(id__in=delegate_ids)
                for d in selected_delegates:
                    d.companies.add(company)
                    
            # Update specialties
            company.specialties.set(specialty_ids)
            
            messages.success(request, _('تم تحديث الارتباطات (المناديب والتخصصات) بنجاح.'))
            
        return redirect('custom_company_profile', pk=company.pk)

class CustomDelegateProfileView(LoginRequiredMixin, VendorOwnerRequiredMixin, DetailView):
    model = Delegate
    template_name = 'custom_admin/delegate_profile.html'
    context_object_name = 'delegate'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        delegate = self.get_object()
        
        # Associated companies
        context['companies'] = delegate.companies.all()
        context['all_companies'] = PharmaceuticalCompany.objects.filter(is_deleted=False)
        # Target specialties
        context['specialties'] = delegate.specialties.all()
        context['all_specialties'] = Specialty.objects.all()
        
        # History data
        from events.models import EventRequest, Event
        from core.models import DelegateSettlement
        from django.db.models import Sum
        context['event_requests'] = EventRequest.objects.filter(delegate=delegate).order_by('-created_at')
        context['events'] = delegate.events.all().order_by('-date')
        context['settlements'] = DelegateSettlement.objects.filter(delegate=delegate).order_by('-created_at')
        
        # Calculate delegate's remaining events balance
        context['net_balance'] = delegate.events.filter(vouchers__is_active=True).aggregate(
            total=Sum('vouchers__current_balance')
        )['total'] or 0
        
        return context

    def post(self, request, *args, **kwargs):
        delegate = self.get_object()
        action = request.POST.get('action')
        
        if action == 'edit_profile':
            delegate.name = request.POST.get('name', delegate.name)
            delegate.phone = request.POST.get('phone', delegate.phone)
            delegate.save()
            
            # Optionally update user's name
            if delegate.user:
                delegate.user.first_name = delegate.name
                delegate.user.save()
                
            messages.success(request, _('تم تحديث بيانات المندوب بنجاح.'))
            
        elif action == 'change_password':
            if delegate.user:
                new_password = request.POST.get('new_password')
                if new_password and len(new_password) >= 6:
                    delegate.user.set_password(new_password)
                    delegate.user.save()
                    messages.success(request, _('تم تحديث كلمة المرور بنجاح.'))
                else:
                    messages.error(request, _('كلمة المرور يجب أن تكون 6 أحرف على الأقل.'))
            else:
                messages.error(request, _('هذا المندوب لا يملك حساب دخول.'))
                
        elif action == 'toggle_status':
            if delegate.user:
                delegate.user.is_active = not delegate.user.is_active
                delegate.user.save()
                status = 'تنشيط' if delegate.user.is_active else 'إيقاف'
                messages.success(request, f'تم {status} حساب المندوب بنجاح.')
                
        elif action == 'manage_associations':
            company_ids = request.POST.getlist('company_ids')
            specialty_ids = request.POST.getlist('specialty_ids')
            
            delegate.companies.set(company_ids)
            delegate.specialties.set(specialty_ids)
            
            messages.success(request, _('تم تحديث ارتباطات المندوب (الشركات والتخصصات) بنجاح.'))
            
        return redirect('custom_delegate_profile', pk=delegate.pk)

class CustomVendorsDirectoryView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'custom_admin/vendors_directory.html'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        category_filter = self.request.GET.get('category', '')
        status_filter = self.request.GET.get('status', '')
        has_fee_filter = self.request.GET.get('has_fee', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        
        # Base query: only vendor admins (main stores)
        base_qs = Vendor.objects.filter(role=Vendor.VendorRoles.ADMIN).order_by('-id')
        
        if query:
            base_qs = base_qs.filter(
                Q(name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query)
            )
            
        if category_filter:
            base_qs = base_qs.filter(category__iexact=category_filter)
            
        if status_filter == 'active':
            base_qs = base_qs.filter(is_active=True)
        elif status_filter == 'inactive':
            base_qs = base_qs.filter(is_active=False)

        if has_fee_filter == 'yes':
            base_qs = base_qs.filter(has_management_fee=True)
        elif has_fee_filter == 'no':
            base_qs = base_qs.filter(has_management_fee=False)

        if date_from:
            base_qs = base_qs.filter(created_at__date__gte=date_from)
        if date_to:
            base_qs = base_qs.filter(created_at__date__lte=date_to)
            
        # Annotate each vendor with cashier count, total sales, total settled, and outstanding balance
        from django.db.models import Subquery, OuterRef, DecimalField
        from core.models import VendorSettlement
        
        from django.db.models import ExpressionWrapper, F
        
        vendors_annotated = base_qs.annotate(
            cashiers_count=Count('cashiers_list', distinct=True),
            total_sales=Sum('transaction__total_deducted'),
            total_settled=Sum('vendorsettlement__amount_settled'),
        )
        
        # Split into active and archived
        vendors_qs = vendors_annotated.filter(is_deleted=False)
        archived_qs = vendors_annotated.filter(is_deleted=True)
        
        paginator = Paginator(vendors_qs, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Compute net outstanding balance per vendor (total_deducted - settled)
        for vendor in page_obj:
            sales = vendor.total_sales or 0
            settled = vendor.total_settled or 0
            vendor.net_outstanding = max(sales - settled, 0)
        
        # Get unique categories for the filter
        categories = Vendor.objects.filter(role=Vendor.VendorRoles.ADMIN).values_list('category', flat=True).distinct()
        categories = [c for c in categories if c] # Remove empty ones
        
        context.update({
            'vendors': page_obj,
            'archived_vendors': archived_qs,
            'page_obj': page_obj,
            'query': query,
            'current_category': category_filter,
            'current_status': status_filter,
            'current_has_fee': has_fee_filter,
            'date_from': date_from,
            'date_to': date_to,
            'categories': categories,
        })
        
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'add_vendor':
            name = request.POST.get('name')
            contact_person = request.POST.get('contact_person')
            phone = request.POST.get('phone')
            email = request.POST.get('email')
            address = request.POST.get('address')
            category = request.POST.get('category')
            username = request.POST.get('username')
            password = request.POST.get('password')
            management_fee = request.POST.get('management_fee_percentage', 25.0)
            
            if not all([name, phone, username, password]):
                messages.error(request, _("يرجى تعبئة الحقول الأساسية المطلوبة."))
                return redirect('custom_vendors_directory')
                
            duplicate_user = User.objects.filter(username=username).first()
            if duplicate_user:
                messages.error(request, _('اسم المستخدم مسجل مسبقاً لمستخدم آخر.'))
                return redirect('custom_vendors_directory')
                
            try:
                user = User.objects.create_user(username=username, password=password, email=email, first_name=name)
                user.type = User.Types.VENDOR
                user.save()
                
                Vendor.objects.create(
                    user=user,
                    name=name,
                    contact_person=contact_person,
                    phone=phone,
                    email=email,
                    address=address,
                    category=category,
                    role=Vendor.VendorRoles.ADMIN,
                    management_fee_percentage=management_fee,
                    has_management_fee=True,
                    is_active=True
                )
                messages.success(request, f'تم إضافة التاجر "{name}" بنجاح.')
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء إضافة التاجر: {str(e)}')
        elif action in ['bulk_activate', 'bulk_deactivate', 'bulk_delete']:
            vendor_ids = request.POST.getlist('vendor_ids')
            if vendor_ids:
                vendors = Vendor.objects.filter(id__in=vendor_ids, role=Vendor.VendorRoles.ADMIN)
                
                if action == 'bulk_delete':
                    count = 0
                    for vendor in vendors:
                        if not vendor.is_deleted:
                            vendor.is_deleted = True
                            vendor.is_active = False
                            vendor.phone = f"{vendor.phone}_del_{vendor.id}"
                            vendor.email = f"del_{vendor.id}_{vendor.email}"
                            vendor.name = f"{vendor.name}_del_{vendor.id}"
                            vendor.save()
                            
                            user = vendor.user
                            user.is_active = False
                            user.username = f"{user.username}_del_{user.id}"
                            user.email = vendor.email
                            user.save()
                            count += 1
                    messages.success(request, f'تم أرشفة وإيقاف عدد {count} تاجر بنجاح (مع الاحتفاظ بالسجلات المالية).')
                else:
                    is_active = True if action == 'bulk_activate' else False
                    vendors.update(is_active=is_active)
                    
                    # Also update users
                    user_ids = vendors.values_list('user_id', flat=True)
                    User.objects.filter(id__in=user_ids).update(is_active=is_active)
                    
                    status_text = "تنشيط" if is_active else "إيقاف"
                    messages.success(request, f'تم {status_text} {vendors.count()} متاجر بنجاح.')
            else:
                messages.error(request, _('يرجى تحديد تاجر واحد على الأقل.'))
                
        return redirect('custom_vendors_directory')

class CustomVendorProfileView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Vendor
    template_name = 'custom_admin/vendor_profile.html'
    context_object_name = 'vendor'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendor = self.get_object()
        
        # Get all cashiers
        context['cashiers'] = Vendor.objects.filter(parent_vendor=vendor, role=Vendor.VendorRoles.CASHIER).order_by('-created_at')
        
        # Transactions involving this vendor or its cashiers
        vendor_ids = [vendor.id] + list(context['cashiers'].values_list('id', flat=True))
        context['transactions_list'] = Transaction.objects.filter(vendor_id__in=vendor_ids).order_by('-transaction_date')
        
        # Financial Stats
        from django.db.models import Sum, Q
        total_sales = context['transactions_list'].aggregate(total=Sum('amount_spent'))['total'] or 0
        total_commissions = context['transactions_list'].aggregate(total=Sum('management_fee_amount'))['total'] or 0
        total_deducted = context['transactions_list'].aggregate(total=Sum('total_deducted'))['total'] or 0
        
        # Settlements
        context['settlements_list'] = VendorSettlement.objects.filter(vendor_id__in=vendor_ids).order_by('-settlement_date')
        total_settled = context['settlements_list'].aggregate(total=Sum('amount_settled'))['total'] or 0
        
        # Available balance to settle
        available_balance = total_deducted - total_settled
        
        # For the chart (monthly spending)
        import json
        from django.db.models.functions import TruncMonth
        
        monthly_stats = context['transactions_list'].annotate(month=TruncMonth('transaction_date')).values('month').annotate(total=Sum('total_deducted')).order_by('month')
        chart_labels = []
        chart_data = []
        for stat in monthly_stats:
            if stat['month']:
                chart_labels.append(stat['month'].strftime('%Y-%m'))
                chart_data.append(float(stat['total']))
                
        context.update({
            'total_sales': total_sales,
            'total_commissions': total_commissions,
            'total_deducted': total_deducted,
            'total_settled': total_settled,
            'available_balance': available_balance,
            'chart_labels': json.dumps(chart_labels),
            'chart_data': json.dumps(chart_data),
        })
        
        return context

    def post(self, request, *args, **kwargs):
        vendor = self.get_object()
        action = request.POST.get('action')
        
        if action == 'edit_profile':
            vendor.name = request.POST.get('name', vendor.name)
            vendor.contact_person = request.POST.get('contact_person', vendor.contact_person)
            vendor.phone = request.POST.get('phone', vendor.phone)
            vendor.email = request.POST.get('email', vendor.email)
            vendor.category = request.POST.get('category', vendor.category)
            vendor.address = request.POST.get('address', vendor.address)
            
            try:
                management_fee = request.POST.get('management_fee_percentage')
                if management_fee:
                    vendor.management_fee_percentage = float(management_fee)
            except ValueError:
                pass
                
            vendor.save()
            
            # Optionally update user's name
            if vendor.user:
                vendor.user.first_name = vendor.name
                vendor.user.save()
                
            messages.success(request, _('تم تحديث بيانات التاجر بنجاح.'))
            
        elif action == 'change_password':
            if vendor.user:
                new_password = request.POST.get('new_password')
                if new_password and len(new_password) >= 6:
                    vendor.user.set_password(new_password)
                    vendor.user.save()
                    messages.success(request, _('تم تحديث كلمة المرور بنجاح.'))
                else:
                    messages.error(request, _('كلمة المرور يجب أن تكون 6 أحرف على الأقل.'))
            else:
                messages.error(request, _('هذا التاجر لا يملك حساب دخول.'))
                
        elif action == 'toggle_status':
            vendor.is_active = not vendor.is_active
            vendor.save()
            
            if vendor.user:
                vendor.user.is_active = vendor.is_active
                vendor.user.save()
                
            status = 'تنشيط' if vendor.is_active else 'إيقاف'
            messages.success(request, f'تم {status} حساب التاجر بنجاح.')
            
        elif action == 'add_settlement':
            amount = request.POST.get('amount')
            notes = request.POST.get('notes', '')
            
            try:
                amount = float(amount)
                if amount > 0:
                    VendorSettlement.objects.create(
                        vendor=vendor,
                        amount_settled=amount,
                        settlement_date=timezone.now(),
                        notes=notes
                    )
                    messages.success(request, f'تم إضافة تسوية مالية بقيمة {amount} ج.م بنجاح.')
                else:
                    messages.error(request, _('يجب أن تكون قيمة التسوية أكبر من الصفر.'))
            except ValueError:
                messages.error(request, _('قيمة التسوية غير صالحة.'))

        elif action == 'add_cashier':
            name = request.POST.get('name')
            contact_person = request.POST.get('contact_person')
            phone = request.POST.get('phone')
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            duplicate_user = User.objects.filter(username=username).first()
            if duplicate_user:
                messages.error(request, _('اسم المستخدم مسجل مسبقاً.'))
            else:
                try:
                    user = User.objects.create_user(username=username, password=password, first_name=name)
                    user.type = User.Types.VENDOR
                    user.save()
                    
                    Vendor.objects.create(
                        user=user,
                        name=name,
                        contact_person=contact_person,
                        phone=phone,
                        email=f"{username}@vendor.local", # placeholder
                        address=vendor.address,
                        category=vendor.category,
                        role=Vendor.VendorRoles.CASHIER,
                        parent_vendor=vendor,
                        management_fee_percentage=vendor.management_fee_percentage,
                        is_active=True
                    )
                    messages.success(request, f'تم إضافة الكاشير "{name}" بنجاح.')
                except Exception as e:
                    messages.error(request, f'حدث خطأ: {str(e)}')
                    
        elif action == 'toggle_cashier_status':
            cashier_id = request.POST.get('cashier_id')
            cashier = Vendor.objects.filter(id=cashier_id, parent_vendor=vendor).first()
            if cashier:
                cashier.is_active = not cashier.is_active
                cashier.save()
                if cashier.user:
                    cashier.user.is_active = cashier.is_active
                    cashier.user.save()
                messages.success(request, _('تم تغيير حالة الكاشير بنجاح.'))

        return redirect('custom_vendor_profile', pk=vendor.pk)

class CustomEmailLogsView(LoginRequiredMixin, UserPassesTestMixin, View):
    """عرض سجل الإيميلات المرسلة من النظام مع فلترة ومتابعة"""
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request):
        from .models import EmailLog
        from accounts.models import Doctor, Vendor, Delegate
        
        status_filter = request.GET.get('status', '')
        query = request.GET.get('q', '').strip()
        template_filter = request.GET.get('template', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        
        logs = EmailLog.objects.all().order_by('-sent_at')
        
        if status_filter:
            logs = logs.filter(status=status_filter)
        if query:
            logs = logs.filter(
                Q(recipient__icontains=query) | Q(subject__icontains=query)
            )
        if template_filter:
            logs = logs.filter(template_used=template_filter)
        if date_from:
            logs = logs.filter(sent_at__date__gte=date_from)
        if date_to:
            logs = logs.filter(sent_at__date__lte=date_to)
        
        # Stats for the header cards
        from django.utils import timezone
        from datetime import timedelta
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        total_sent = EmailLog.objects.count()
        total_success = EmailLog.objects.filter(status='SUCCESS').count()
        total_failed = EmailLog.objects.filter(status='FAILED').count()
        recent_sent = EmailLog.objects.filter(sent_at__gte=seven_days_ago).count()
        
        # Paginate
        paginator = Paginator(logs, 100)  # Show 100 emails per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get all users for "send email" modal and resend credentials
        from accounts.models import User, Delegate
        from core.models import PharmaceuticalCompany
        all_users = User.objects.filter(is_active=True).exclude(email='').order_by('first_name', 'username')
        
        # Determine types for all_users to use in frontend filtering
        for u in all_users:
            if getattr(u, 'is_staff', False) or getattr(u, 'is_superuser', False):
                u.custom_type = 'admin'
            elif hasattr(u, 'type'):
                # Handle based on choices if available, otherwise lowercase string
                u.custom_type = str(u.type).lower()
            else:
                u.custom_type = 'unknown'
        
        # Get entities for bulk email
        doctors = Doctor.objects.filter(is_deleted=False).exclude(email='').order_by('name')
        vendors = Vendor.objects.filter(role='ADMIN', is_deleted=False).exclude(email='').order_by('name')
        companies = PharmaceuticalCompany.objects.filter(is_deleted=False).exclude(email='').order_by('name')
        delegates = Delegate.objects.filter(is_deleted=False).order_by('name')
        admins = User.objects.filter(is_staff=True, is_active=True).exclude(email='')
        
        # Get unique templates for filter dropdown
        unique_templates = EmailLog.objects.exclude(template_used='').values_list('template_used', flat=True).distinct()
        unique_templates = [t for t in unique_templates if t]
        
        context = {
            'logs': page_obj,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'total_sent': total_sent,
            'total_success': total_success,
            'total_failed': total_failed,
            'recent_sent': recent_sent,
            'current_status': status_filter,
            'current_template': template_filter,
            'date_from': date_from,
            'date_to': date_to,
            'query': query,
            'all_users': all_users,
            'doctors': doctors,
            'vendors': vendors,
            'companies': companies,
            'delegates': delegates,
            'admins': admins,
            'unique_templates': unique_templates,
            'active_page': 'email_logs',
        }
        return render(request, 'custom_admin/email_logs.html', context)


class CustomEmailActionsView(LoginRequiredMixin, UserPassesTestMixin, View):
    """إجراءات الإيميلات: إعادة إرسال بيانات الدخول، إرسال إيميل مخصص"""
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request):
        from .services import send_email_async
        from accounts.models import User
        import string, random
        
        action = request.POST.get('action')
        
        if action == 'resend_credentials':
            user_id = request.POST.get('user_id')
            try:
                user = User.objects.get(pk=user_id)
                if not user.email:
                    messages.error(request, f'المستخدم {user.username} لا يملك بريد إلكتروني مسجل.')
                    return redirect('custom_email_logs')
                
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
                        'phone': getattr(user, 'phone', ''),
                        'password': new_password,
                        'site_url': site_url,
                    },
                    recipient_email=user.email,
                )
                messages.success(request, f'✅ تم إعادة تعيين كلمة المرور وإرسالها إلى {user.email}')
            except User.DoesNotExist:
                messages.error(request, _('المستخدم غير موجود.'))
                
        elif action == 'send_custom_email':
            subject = request.POST.get('subject', '').strip()
            message_body = request.POST.get('message', '').strip()
            recipient_type = request.POST.get('recipient_type', 'specific')
            
            if not subject or not message_body:
                messages.error(request, _('يرجى تعبئة عنوان الرسالة ومحتواها.'))
                return redirect('custom_email_logs')
            
            recipients = []
            
            if recipient_type == 'specific':
                user_ids = request.POST.getlist('user_ids')
                recipients = list(User.objects.filter(id__in=user_ids, is_active=True).exclude(email=''))
            elif recipient_type == 'all_doctors':
                from accounts.models import Doctor
                doctors = Doctor.objects.filter(is_deleted=False).exclude(email='').select_related('user')
                for doc in doctors:
                    if doc.user and doc.user.email:
                        recipients.append(doc.user)
                    elif doc.email:
                        # Create a fake user-like object
                        class FakeUser:
                            def __init__(self, name, email, username):
                                self.email = email
                                self.username = username
                                def get_full_name(self): return name
                            get_full_name = lambda self: name
                        fu = FakeUser(doc.name, doc.email, doc.name)
                        recipients.append(fu)
            elif recipient_type == 'all_vendors':
                from accounts.models import Vendor
                vendors = Vendor.objects.filter(role='ADMIN', is_deleted=False).exclude(email='')
                for v in vendors:
                    if v.user and v.user.email:
                        recipients.append(v.user)
            elif recipient_type == 'all_companies':
                from core.models import PharmaceuticalCompany
                companies = PharmaceuticalCompany.objects.filter(is_deleted=False).exclude(email='')
                for c in companies:
                    if c.user and c.user.email:
                        recipients.append(c.user)
            elif recipient_type == 'all_delegates':
                from accounts.models import Delegate
                delegates = Delegate.objects.filter(is_deleted=False)
                for d in delegates:
                    if d.user and d.user.email:
                        recipients.append(d.user)
            elif recipient_type == 'all_admins':
                recipients = list(User.objects.filter(is_staff=True, is_active=True).exclude(email=''))
            elif recipient_type == 'all_active':
                recipients = list(User.objects.filter(is_active=True).exclude(email=''))
            
            sent_count = 0
            for user in recipients:
                try:
                    send_email_async(
                        subject=subject,
                        template_name='emails/custom_message_email.html',
                        context={
                            'subject': subject,
                            'message': message_body,
                            'user_name': user.get_full_name() or user.username,
                        },
                        recipient_email=user.email,
                    )
                    sent_count += 1
                except Exception:
                    pass
            
            messages.success(request, f'✅ تم إرسال الرسالة إلى {sent_count} مستخدم بنجاح.')
            
        elif action == 'retry_failed':
            # Retry all failed emails from the last 24 hours (just re-triggers the same info)
            from .models import EmailLog
            from django.utils import timezone
            from datetime import timedelta
            failed_logs = EmailLog.objects.filter(
                status='FAILED',
                sent_at__gte=timezone.now() - timedelta(hours=24)
            )
            messages.info(request, f'يوجد {failed_logs.count()} إيميل فاشل في آخر 24 ساعة. يرجى إعادة إرسالها يدوياً باستخدام "إعادة إرسال بيانات الدخول".')

        return redirect('custom_email_logs')


def handler404(request, exception):

    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)

def handler403(request, exception):
    return render(request, '403.html', status=403)


from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Notification
from django.http import JsonResponse

@login_required
@require_POST
def mark_notification_as_read(request, pk):
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

import json

class CustomEventRequestCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'custom_admin/event_request_form.html')

    def post(self, request):
        user = request.user
        company_profile = getattr(user, 'company_profile', None)
        delegate_profile = getattr(user, 'delegate_profile', None)

        if not company_profile and not delegate_profile:
            messages.error(request, _('عذراً، ليس لديك الصلاحية لإنشاء طلب فعالية.'))
            return redirect('custom_dashboard')

        name = request.POST.get('name')
        date = request.POST.get('date')
        voucher_value = request.POST.get('voucher_value')
        max_budget = request.POST.get('max_budget')
        notes = request.POST.get('notes')
        doctors_data_str = request.POST.get('doctors_data', '[]')

        try:
            doctors_data = json.loads(doctors_data_str)
        except json.JSONDecodeError:
            doctors_data = []

        if not name or not date or not voucher_value or not max_budget:
            messages.error(request, _('الرجاء تعبئة جميع الحقول الأساسية المطلوبة.'))
            return redirect('custom_event_request_create')

        event_req = EventRequest.objects.create(
            requester_user=user,
            company=company_profile,
            delegate=delegate_profile,
            name=name,
            date=date,
            voucher_value=voucher_value,
            max_budget=max_budget,
            notes=notes,
            status=EventRequest.StatusChoices.PENDING
        )

        for d in doctors_data:
            if d.get('type') == 'existing' and d.get('id'):
                try:
                    doc = Doctor.objects.get(id=d['id'])
                    EventRequestDoctor.objects.create(
                        event_request=event_req,
                        existing_doctor=doc,
                        name=doc.name,
                        phone=doc.phone,
                        email=doc.email,
                        specialty_name=doc.specialty.name if doc.specialty else ''
                    )
                except Doctor.DoesNotExist:
                    pass
            elif d.get('type') == 'new':
                EventRequestDoctor.objects.create(
                    event_request=event_req,
                    name=d.get('name', ''),
                    phone=d.get('phone', ''),
                    email=d.get('email', ''),
                    specialty_name=d.get('specialty', '')
                )

        # Notify admin users of the new event request
        from core.models import Notification
        requester_name = company_profile.clean_name if company_profile else (delegate_profile.name if delegate_profile else user.username)
        for admin_user in User.objects.filter(is_staff=True):
            Notification.objects.create(
                user=admin_user,
                message=_(f'طلب فعالية جديد من "{requester_name}": {name}'),
                notification_type='SYSTEM',
                link=f'/admin-event-requests/{event_req.id}/'
            )

        messages.success(request, _('تم إرسال طلب الفعالية بنجاح، وهو الآن قيد المراجعة من الإدارة.'))
        if company_profile:
            return redirect('custom_company_portal')
        else:
            return redirect('custom_delegate_portal')

from django.views.generic import ListView
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string

class AdminEventRequestsView(UserPassesTestMixin, ListView):
    model = EventRequest
    template_name = 'custom_admin/event_requests_list.html'
    paginate_by = 20
    ordering = ['-created_at']

    def test_func(self):
        return self.request.user.is_staff or getattr(self.request.user, 'type', '') == 'ADMIN'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_page'] = 'event_requests'
        return context

class AdminEventRequestDetailView(UserPassesTestMixin, DetailView):
    model = EventRequest
    template_name = 'custom_admin/event_request_detail.html'

    def test_func(self):
        return self.request.user.is_staff or getattr(self.request.user, 'type', '') == 'ADMIN'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctors'] = self.object.requested_doctors.all()
        context['active_page'] = 'event_requests'
        return context

class AdminCreateRequestedDoctorView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff or getattr(self.request.user, 'type', '') == 'ADMIN'

    def post(self, request, pk):
        try:
            req_doc = EventRequestDoctor.objects.get(id=pk)
            if req_doc.is_created or req_doc.existing_doctor:
                return JsonResponse({'success': False, 'error': 'Account already exists'})
                
            password = get_random_string(length=8)
            username = req_doc.phone
            
            user = User.objects.create_user(
                username=username,
                password=password,
                email=req_doc.email if req_doc.email else None,
                first_name=req_doc.name
            )
            
            user.type = 'DOCTOR'
            user.phone = req_doc.phone
            user.save()
            
            from accounts.models import Specialty
            spec, _ = Specialty.objects.get_or_create(name=req_doc.specialty_name) if req_doc.specialty_name else (None, False)
            
            # Use a guaranteed-unique fallback email if none provided
            fallback_email = f"{username}_{uuid.uuid4().hex[:6]}@noemail.system"
            doctor = Doctor.objects.create(
                user=user,
                name=req_doc.name,
                phone=req_doc.phone,
                email=req_doc.email if req_doc.email else fallback_email,
                specialty=spec
            )
            
            req_doc.is_created = True
            req_doc.existing_doctor = doctor
            req_doc.save()
            
            if user.email:
                try:
                    send_mail(
                        'بيانات الدخول لحسابك',
                        f'مرحباً د. {req_doc.name}\nتم إنشاء حسابك بنجاح.\nاسم المستخدم: {username}\nكلمة المرور: {password}',
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    pass

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class AdminApproveEventRequestView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff or getattr(self.request.user, 'type', '') == 'ADMIN'

    def post(self, request, pk):
        req = get_object_or_404(EventRequest, id=pk)
        
        if req.status != 'PENDING':
            messages.error(request, _('هذا الطلب تم التعامل معه مسبقاً.'))
            return redirect('admin_event_request_detail', pk=pk)
            
        event = Event.objects.create(
            name=req.name,
            date=req.date,
            company=req.company,
            voucher_value=req.voucher_value,
            max_budget=req.max_budget,
            notes=req.notes
        )
        if req.delegate:
            event.delegates.add(req.delegate)
            
        for d in req.requested_doctors.all():
            if d.existing_doctor:
                event.doctors.add(d.existing_doctor)
                Voucher.objects.create(
                    doctor=d.existing_doctor,
                    event=event,
                    company=req.company,
                    initial_value=req.voucher_value,
                    current_balance=req.voucher_value
                )
                
        req.status = 'APPROVED'
        req.save()
        
        messages.success(request, _('تم اعتماد الفعالية بنجاح وإصدار القسائم للأطباء المرتبطين.'))
        return redirect('admin_event_request_detail', pk=pk)

class AdminRejectEventRequestView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff or getattr(self.request.user, 'type', '') == 'ADMIN'

    def post(self, request, pk):
        req = get_object_or_404(EventRequest, id=pk)
        
        if req.status != 'PENDING':
            messages.error(request, _('هذا الطلب تم التعامل معه مسبقاً.'))
            return redirect('admin_event_request_detail', pk=pk)
            
        req.status = 'REJECTED'
        req.save()
        
        messages.success(request, _('تم رفض طلب الفعالية بنجاح.'))
        return redirect('admin_event_request_detail', pk=pk)

class PortalDoctorSearchView(LoginRequiredMixin, View):
    """AJAX endpoint for company/delegate portals to search doctors by phone or name."""
    def get(self, request):
        phone = request.GET.get('phone', '').strip()
        name = request.GET.get('name', '').strip()
        query = request.GET.get('q', '').strip()

        search_term = query or phone or name

        if not search_term:
            return JsonResponse({'exists': False, 'results': []})

        user = request.user
        company_profile = getattr(user, 'company_profile', None)
        delegate_profile = getattr(user, 'delegate_profile', None)

        qs = Doctor.objects.filter(is_deleted=False)
        results = []
        seen_phones = set()

        # 1. Search Global Doctors
        name_filter = Q()
        for term in search_term.split():
            name_filter &= Q(name__icontains=term)
            
        matches = qs.filter(
            name_filter | Q(phone__icontains=search_term)
        ).select_related('specialty')[:10]

        for doctor in matches:
            results.append({
                'id': doctor.id,
                'name': doctor.name,
                'phone': doctor.clean_phone,
                'email': doctor.clean_email,
                'specialty': doctor.specialty.name if doctor.specialty else '',
            })
            seen_phones.add(doctor.clean_phone)

        # 2. Search unapproved doctors from the user's past EventRequests
        if company_profile:
            past_req_docs = EventRequestDoctor.objects.filter(event_request__company=company_profile, existing_doctor__isnull=True)
        elif delegate_profile:
            past_req_docs = EventRequestDoctor.objects.filter(event_request__delegate=delegate_profile, existing_doctor__isnull=True)
        else:
            past_req_docs = EventRequestDoctor.objects.none()

        past_matches = past_req_docs.filter(
            name_filter | Q(phone__icontains=search_term)
        ).values('name', 'phone', 'email', 'specialty_name').distinct()[:10]

        for doc in past_matches:
            if doc['phone'] not in seen_phones:
                results.append({
                    'id': None,  # Not a global doctor yet
                    'name': doc['name'],
                    'phone': doc['phone'],
                    'email': doc['email'] or '',
                    'specialty': doc['specialty_name'] or '',
                })
                seen_phones.add(doc['phone'])

        return JsonResponse({
            'exists': len(results) > 0,
            'results': results,
            'doctor': results[0] if len(results) == 1 else None
        })


class CustomCompanySettingsView(CompanyPortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/company_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_profile'] = getattr(self.request.user, 'company_profile', None)
        return context

    def post(self, request, *args, **kwargs):
        company_profile = getattr(request.user, 'company_profile', None)
        if not company_profile:
            return redirect('custom_login')

        action = request.POST.get('action')

        if action == 'update_profile':
            contact_person = request.POST.get('contact_person', '').strip()
            phone = request.POST.get('phone', '').strip()
            email = request.POST.get('email', '').strip()
            address = request.POST.get('address', '').strip()

            # Validate phone/email uniqueness in User model if they changed
            user = request.user
            if phone and phone != user.phone:
                if User.objects.filter(phone=phone).exclude(pk=user.pk).exists():
                    messages.error(request, _("رقم الهاتف مسجل بالفعل لمستخدم آخر."))
                    return redirect("company_portal_settings")
                user.phone = phone
            
            if email and email != user.email:
                if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                    messages.error(request, _("البريد الإلكتروني مسجل بالفعل لمستخدم آخر."))
                    return redirect("company_portal_settings")
                user.email = email

            try:
                user.save()
                company_profile.contact_person = contact_person
                company_profile.phone = phone
                company_profile.email = email
                company_profile.address = address
                company_profile.save()
                messages.success(request, _("تم تحديث البيانات الشخصية بنجاح."))
            except Exception as e:
                messages.error(request, _("حدث خطأ أثناء حفظ البيانات: ") + str(e))

        elif action == 'change_password':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if new_password != confirm_password:
                messages.error(request, _("كلمتا المرور غير متطابقتين."))
            elif len(new_password) < 6:
                messages.error(request, _("كلمة المرور يجب أن تكون 6 أحرف على الأقل."))
            else:
                request.user.set_password(new_password)
                request.user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                messages.success(request, _("تم تغيير كلمة المرور بنجاح."))
        
        return redirect("company_portal_settings")


class CustomDelegateSettingsView(DelegatePortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/delegate_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delegate_profile'] = getattr(self.request.user, 'delegate_profile', None)
        return context

    def post(self, request, *args, **kwargs):
        delegate_profile = getattr(request.user, 'delegate_profile', None)
        if not delegate_profile:
            return redirect('custom_login')

        action = request.POST.get('action')

        if action == 'update_profile':
            name = request.POST.get('name', '').strip()
            phone = request.POST.get('phone', '').strip()

            # Validate phone uniqueness in User model if changed
            user = request.user
            if phone and phone != user.phone:
                if User.objects.filter(phone=phone).exclude(pk=user.pk).exists():
                    messages.error(request, _("رقم الهاتف مسجل بالفعل لمستخدم آخر."))
                    return redirect("delegate_portal_settings")
                user.phone = phone

            try:
                user.save()
                delegate_profile.name = name
                delegate_profile.phone = phone
                delegate_profile.save()
                messages.success(request, _("تم تحديث البيانات الشخصية بنجاح."))
            except Exception as e:
                messages.error(request, _("حدث خطأ أثناء حفظ البيانات: ") + str(e))

        elif action == 'change_password':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if new_password != confirm_password:
                messages.error(request, _("كلمتا المرور غير متطابقتين."))
            elif len(new_password) < 6:
                messages.error(request, _("كلمة المرور يجب أن تكون 6 أحرف على الأقل."))
            else:
                request.user.set_password(new_password)
                request.user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                messages.success(request, _("تم تغيير كلمة المرور بنجاح."))
        
        return redirect("delegate_portal_settings")

class AdminCompanyDelegateHistoryView(LoginRequiredMixin, VendorOwnerRequiredMixin, View):
    def get(self, request, company_id, delegate_id):
        from django.shortcuts import get_object_or_404, render
        from core.models import PharmaceuticalCompany, Transaction, DelegateSettlement
        from events.models import Event, Voucher
        from accounts.models import Delegate
        from django.db.models import Sum
        
        company = get_object_or_404(PharmaceuticalCompany, id=company_id)
        delegate = get_object_or_404(Delegate, id=delegate_id)
        
        # Events assigned to this delegate by this company
        events = Event.objects.filter(company=company, delegates=delegate).order_by('-created_at')
        
        # Vouchers linked to these events
        vouchers = Voucher.objects.filter(event__in=events)
        v_agg = vouchers.aggregate(
            t_initial=Sum('initial_value'),
            t_current=Sum('current_balance')
        )
        total_vouchers_value = v_agg['t_initial'] or 0
        total_vouchers_current = v_agg['t_current'] or 0
        total_vouchers_consumed = total_vouchers_value - total_vouchers_current
        
        # Transactions linked to these vouchers
        transactions = Transaction.objects.filter(vouchers__in=vouchers).distinct().order_by('-transaction_date')
        total_transactions_value = transactions.aggregate(total=Sum('amount_spent'))['total'] or 0
        
        # Settlements
        settlements = DelegateSettlement.objects.filter(company=company, delegate=delegate).order_by('-settlement_date')
        total_commission_paid = settlements.filter(settlement_status='COMPLETED').aggregate(total=Sum('settlement_amount'))['total'] or 0
        
        context = {
            'company': company,
            'delegate': delegate,
            'events': events,
            'vouchers': vouchers,
            'transactions': transactions,
            'total_vouchers_value': total_vouchers_value,
            'total_vouchers_consumed': total_vouchers_consumed,
            'total_transactions_value': total_transactions_value,
            'total_commission_paid': total_commission_paid,
            'settlements': settlements
        }
        
        return render(request, 'custom_admin/company_delegate_history.html', context)

class CustomNotificationsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'custom_admin/notifications.html'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.models import Notification
        from django.core.paginator import Paginator
        
        all_notifs = Notification.objects.filter(user=self.request.user).order_by('-created_at')
        
        paginator = Paginator(all_notifs, 50)
        page_number = self.request.GET.get('page')
        context['notifications_page'] = paginator.get_page(page_number)
        context['active_page'] = 'notifications'
        
        return context
