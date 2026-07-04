import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction as db_transaction
from django.db.models import Sum, F
from django.db.models.signals import post_save

from accounts.models import User, Specialty, Delegate, Doctor, Vendor
from core.models import (
    PharmaceuticalCompany, CompanySettlement, DelegateSettlement, 
    VendorSettlement, Transaction, Notification
)
from events.models import Event, Voucher, VoucherTransfer, EventRequest, EventRequestDoctor
from events.signals import send_voucher_notification
from core.services import process_transaction


# ─── Arabic Data Lists ───────────────────────────────────────────────

FIRST_NAMES = [
    'أحمد', 'محمد', 'علي', 'عمر', 'خالد', 'يوسف', 'إبراهيم', 'حسن', 'حسين', 'سعيد',
    'عبدالله', 'عبدالرحمن', 'طارق', 'ياسر', 'مصطفى', 'كريم', 'سامي', 'رامي', 'هشام', 'وليد',
    'ماجد', 'فهد', 'سلطان', 'ناصر', 'بدر', 'فيصل', 'تركي', 'سعود', 'منصور', 'راشد',
    'نبيل', 'أنور', 'جمال', 'صالح', 'زياد', 'عادل', 'حمزة', 'بلال', 'أيمن', 'شريف',
    'هاني', 'باسم', 'ثامر', 'مروان', 'عمار', 'حاتم', 'غسان', 'وسام', 'معاذ', 'أسامة',
    'محمود', 'سليمان', 'رائد', 'حازم', 'طارق', 'مفيد', 'أمين', 'مجد', 'عاصم', 'بهاء'
]

LAST_NAMES = [
    'الأحمد', 'المحمد', 'العلي', 'الحسن', 'العمري', 'الشريف', 'البكري', 'الغامدي', 'القحطاني', 'الحربي',
    'الدوسري', 'العتيبي', 'المطيري', 'الشهري', 'الزهراني', 'السبيعي', 'البلوي', 'السلمي', 'الثقفي', 'الحارثي',
    'المالكي', 'الجهني', 'العنزي', 'الشمري', 'الرشيدي', 'الخالدي', 'السعدي', 'الهاشمي', 'العباسي', 'النعيمي',
    'الكندي', 'اليافعي', 'الحضرمي', 'الباعبود', 'بن محفوظ', 'المهري', 'السقاف', 'العطاس', 'باحارث', 'الكثيري',
    'الحداد', 'العمودي', 'باوزير', 'التميمي', 'البار', 'الجفري', 'باجابر', 'باخشوين', 'بازرعة', 'باصريح'
]

SPECIALTIES = [
    'طب القلب', 'طب العيون', 'جراحة عامة', 'طب الأطفال', 'طب النساء والتوليد',
    'طب الأسنان', 'الأمراض الجلدية', 'الطب الباطني', 'العظام', 'المسالك البولية',
    'الأنف والأذن والحنجرة', 'الأعصاب', 'الطب النفسي', 'التخدير', 'الأشعة',
    'طب الطوارئ', 'أمراض الدم', 'الغدد الصماء', 'الروماتيزم', 'طب الأسرة',
    'الكلى', 'الكبد والجهاز الهضمي', 'المناعة والحساسية', 'الأورام'
]

PHARMA_PREFIXES = [
    'أستر', 'فارما', 'نوفو', 'ميدي', 'جلوبال', 'أبيكس', 'إيفا', 'ساندوز', 'نوفارتس', 'أمون',
    'سيبلا', 'سانوفي', 'بايونير', 'ألفا', 'سبيماكو', 'الجزيرة', 'الحضارة', 'الريادة', 'الشفاء', 'الهدى',
    'المستقبل', 'النخبة', 'رويال', 'النيل', 'العربية', 'المتحدة', 'الحكمة', 'سيجما', 'ابن سينا', 'الرازي'
]

PHARMA_SUFFIXES = [
    'جروب', 'فارماسوتيكالز', 'للأدوية', 'الدوائية', 'مصر', 'الشرق الأوسط', 'العالمية', 'الحديثة', 'العربية', 'المتحدة'
]

VENDOR_PREFIXES = [
    'سوبرماركت', 'ميني ماركت', 'هايبر ماركت', 'مطعم', 'صيدلية', 'مخبز', 'حلويات', 'كافيه',
    'عصائر', 'جزارة', 'أسماك', 'بقالة', 'متجر', 'سوق', 'بيتزا', 'شاورما'
]

VENDOR_ADJECTIVES = [
    'الخير', 'النور', 'البركة', 'الأمل', 'السعادة', 'الوفاء', 'الشرق', 'السلطان', 'الفردوس', 'الشفاء',
    'الحياة', 'الأمان', 'الدواء', 'الذهبي', 'الأصالة', 'النجمة', 'الأمير', 'الريف', 'الديوان', 'المساء',
    'الجزيرة', 'اليمن', 'حضرموت', 'الوطن', 'السلام', 'العائلة', 'الفرسان', 'الياسمين', 'الأصدقاء', 'الشباب'
]

VENDOR_CATEGORIES = [
    'سوبرماركت', 'مطعم', 'صيدلية', 'مخبز', 'حلويات',
    'جزارة', 'أسماك', 'بقالة', 'كافيه', 'عصائر'
]

EVENT_NAMES = [
    'مؤتمر القلب السنوي', 'ملتقى أطباء العيون', 'ندوة طب الأطفال', 'ورشة عمل جراحية',
    'مؤتمر الطب الباطني', 'ملتقى أطباء الأسنان', 'ندوة الأمراض الجلدية', 'مؤتمر العظام الدولي',
    'ملتقى المسالك البولية', 'ندوة الأعصاب', 'مؤتمر الطب النفسي', 'ملتقى التخدير',
    'ندوة الأشعة', 'مؤتمر طب الطوارئ', 'ملتقى أمراض الدم', 'ندوة الغدد الصماء',
    'مؤتمر الروماتيزم', 'ملتقى طب الأسرة', 'مؤتمر الأنف والأذن', 'ندوة طب النساء'
]

CITIES = [
    'المكلا', 'سيئون', 'الشحر', 'عدن', 'صنعاء', 'تعز', 'الحديدة', 'تريم', 'القطن', 'غيل باوزير'
]

ITEMS_DESCRIPTIONS = [
    'مواد غذائية متنوعة', 'لحوم ودواجن طازجة', 'خضار وفواكه', 'مشروبات وعصائر',
    'وجبة غداء كاملة', 'وجبة عشاء عائلية', 'مستلزمات طبية', 'أدوية ومكملات',
    'حلويات ومعجنات', 'مخبوزات طازجة', 'قهوة ومشروبات ساخنة', 'مشويات',
    'أسماك طازجة', 'بهارات وتوابل', 'عسل طبيعي وتمور', 'فطائر ومعجنات'
]


class Command(BaseCommand):
    help = 'Seeds the database with at least 100 accounts of each type and their corresponding dummy transactions'

    def handle(self, *args, **options):
        # 1. Disconnect email/notification signals to keep database seeding ultra-fast and avoid thread issues
        self.stdout.write(self.style.WARNING('🔌 Disconnecting email/notification signals during seeding...'))
        post_save.disconnect(send_voucher_notification, sender=Voucher)

        self.stdout.write(self.style.WARNING('🗑️ Clearing existing non-staff data...'))
        self._clear_data()

        self.stdout.write(self.style.SUCCESS('🌱 Starting database seeding...'))
        self.stdout.write('')

        # Step 2: Create Specialties
        specialties = self._create_specialties()

        # Step 3: Create Pharmaceutical Companies (at least 105)
        companies = self._create_companies(105, specialties)

        # Step 4: Create Delegates (at least 105)
        delegates = self._create_delegates(105, companies, specialties)

        # Step 5: Create Doctors (at least 105)
        doctors = self._create_doctors(105, specialties)

        # Step 6: Create Vendors (at least 105, including cashiers)
        vendors = self._create_vendors(105)

        # Step 7: Create Events (60) and assign Doctors (auto-creates Vouchers via signals)
        events = self._create_events(60, companies, doctors, delegates, specialties)

        # Step 8: Update all vouchers to copy company link
        self.stdout.write('🔗 Linking company field to vouchers...')
        vouchers_to_update = []
        for voucher in Voucher.objects.filter(company__isnull=True, event__isnull=False).select_related('event'):
            voucher.company = voucher.event.company
            vouchers_to_update.append(voucher)
        if vouchers_to_update:
            Voucher.objects.bulk_update(vouchers_to_update, ['company'])

        # Step 9: Create Transactions (1000) using process_transaction service
        self._create_transactions(1000, doctors, vendors)

        # Step 10: Create Voucher Transfers (60)
        self._create_transfers(60, doctors)

        # Step 11: Create Event Requests (40)
        self._create_event_requests(40, companies, delegates, doctors, specialties)

        # Step 12: Create Settlements (Company, Delegate, Vendor)
        self._create_company_settlements(companies)
        self._create_delegate_settlements(delegates)
        self._create_vendor_settlements(vendors)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('✅ Seeding complete! All accounts set to password: 123456'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self._print_summary()

    def _clear_data(self):
        """Clear all records except staff and superuser User accounts to respect integrity"""
        # Deleting models in correct topological order
        EventRequestDoctor.objects.all().delete()
        EventRequest.objects.all().delete()
        VoucherTransfer.objects.all().delete()
        Transaction.objects.all().delete()
        Voucher.objects.all().delete()
        Event.objects.all().delete()
        
        CompanySettlement.objects.all().delete()
        DelegateSettlement.objects.all().delete()
        VendorSettlement.objects.all().delete()
        
        Doctor.objects.all().delete()
        Delegate.objects.all().delete()
        Vendor.objects.all().delete()
        PharmaceuticalCompany.objects.all().delete()
        
        Notification.objects.all().delete()
        
        # Keep superusers and staff accounts
        User.objects.filter(is_superuser=False, is_staff=False).delete()
        
        self.stdout.write(self.style.SUCCESS('  ✓ Existing dummy data cleared successfully.'))

    def _create_specialties(self):
        self.stdout.write('🧬 Creating specialties...')
        specialties = []
        for name in SPECIALTIES:
            sp, _ = Specialty.objects.get_or_create(name=name)
            specialties.append(sp)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(specialties)} specialties ready'))
        return specialties

    def _create_companies(self, count, specialties):
        self.stdout.write(f'🏢 Creating {count} Pharmaceutical Companies...')
        companies = []
        
        # Generate unique names
        unique_names = set()
        while len(unique_names) < count:
            name = f"{random.choice(PHARMA_PREFIXES)} {random.choice(PHARMA_SUFFIXES)}"
            unique_names.add(name)
        
        unique_names = list(unique_names)
        
        for i, name in enumerate(unique_names):
            username = f'company_{i+1}'
            email = f'company{i+1}@hadramout.com'
            phone = f'053{i+1:07d}'
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password='123456',
                type='COMPANY',
                phone=phone
            )
            
            company = PharmaceuticalCompany.objects.create(
                user=user,
                name=name,
                contact_person=f'{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}',
                phone=phone,
                email=email,
                address=f'{random.choice(CITIES)} - شارع {random.randint(1, 50)}',
            )
            
            # Attach 1-3 random specialties
            company.specialties.add(*random.sample(specialties, random.randint(1, 3)))
            companies.append(company)
            
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(companies)} companies created'))
        return companies

    def _create_delegates(self, count, companies, specialties):
        self.stdout.write(f'💼 Creating {count} Delegates...')
        delegates = []
        
        for i in range(count):
            username = f'delegate_{i+1}'
            email = f'delegate{i+1}@hadramout.com'
            phone = f'054{i+1:07d}'
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password='123456',
                type='DELEGATE',
                phone=phone
            )
            
            delegate = Delegate.objects.create(
                user=user,
                name=f'{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}',
                phone=phone,
            )
            
            # Attach 2-5 random companies and 2-4 random specialties
            delegate.companies.add(*random.sample(companies, random.randint(2, 5)))
            delegate.specialties.add(*random.sample(specialties, random.randint(2, 4)))
            delegates.append(delegate)
            
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(delegates)} delegates created'))
        return delegates

    def _create_doctors(self, count, specialties):
        self.stdout.write(f'👨‍⚕️ Creating {count} Doctors...')
        doctors = []
        
        for i in range(count):
            username = f'doctor_{i+1}'
            email = f'doctor{i+1}@hadramout.com'
            phone = f'055{i+1:07d}'
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password='123456',
                type='DOCTOR',
                phone=phone
            )
            
            doctor = Doctor.objects.create(
                user=user,
                name=f'د. {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}',
                phone=phone,
                email=email,
                specialty=random.choice(specialties),
            )
            doctors.append(doctor)
            
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(doctors)} doctors created'))
        return doctors

    def _create_vendors(self, count):
        self.stdout.write(f'🏪 Creating {count} Vendors (including Cashiers)...')
        vendors = []
        
        # Generate unique names
        unique_names = set()
        while len(unique_names) < count:
            name = f"{random.choice(VENDOR_PREFIXES)} {random.choice(VENDOR_ADJECTIVES)} {random.randint(1, 1000)}"
            unique_names.add(name)
            
        unique_names = list(unique_names)
        admin_vendors = []
        
        for i, name in enumerate(unique_names):
            username = f'vendor_{i+1}'
            email = f'vendor{i+1}@hadramout.com'
            phone = f'056{i+1:07d}'
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password='123456',
                type='VENDOR',
                phone=phone
            )
            
            # Determine if ADMIN or CASHIER (approx 10% cashier)
            is_cashier = (i >= 95)
            role = 'CASHIER' if is_cashier else 'ADMIN'
            parent = random.choice(admin_vendors) if is_cashier and admin_vendors else None
            
            vendor = Vendor.objects.create(
                user=user,
                name=name,
                contact_person=f'{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}',
                phone=phone,
                email=email,
                address=f'{random.choice(CITIES)} - حي {random.randint(1, 10)}',
                category=random.choice(VENDOR_CATEGORIES),
                role=role,
                parent_vendor=parent,
                management_fee_percentage=Decimal('25.00'),
                has_management_fee=True,
                is_active=True
            )
            
            vendors.append(vendor)
            if role == 'ADMIN':
                admin_vendors.append(vendor)
            
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(vendors)} vendors created'))
        return vendors

    def _create_events(self, count, companies, doctors, delegates, specialties):
        self.stdout.write(f'🎉 Creating {count} events and assigning doctors/delegates...')
        events = []
        today = date.today()
        
        for i in range(count):
            event_date = today - timedelta(days=random.randint(0, 180))
            voucher_value = Decimal(str(random.choice([200, 300, 500, 1000, 1500, 2000, 3000])))
            max_budget = voucher_value * Decimal(str(random.randint(20, 50)))
            
            event_name = f"{random.choice(EVENT_NAMES)} - {random.choice(CITIES)} {i+1}"
            company = random.choice(companies)
            
            event = Event.objects.create(
                name=event_name,
                date=event_date,
                company=company,
                voucher_value=voucher_value,
                voucher_expiry_days=random.choice([60, 90, 120]),
                max_budget=max_budget,
                notes=f"فعالية طبية لشركة {company.name} لمناقشة أحدث المستجدات الطبية."
            )
            
            # Select 1-3 random specialties linked to this company
            company_specs = list(company.specialties.all())
            selected_specs = company_specs if company_specs else list(specialties)
            event.specialties.add(*random.sample(selected_specs, min(len(selected_specs), random.randint(1, 3))))
            
            # Select 1-2 delegates linked to this company
            company_delegates = list(company.delegates.all())
            selected_delegates = company_delegates if company_delegates else list(delegates)
            event.delegates.add(*random.sample(selected_delegates, min(len(selected_delegates), random.randint(1, 2))))
            
            # Select 5-15 doctors matching the specialties
            matching_doctors = list(Doctor.objects.filter(specialty__in=event.specialties.all()))
            if not matching_doctors:
                matching_doctors = list(doctors)
            
            selected_doctors = random.sample(matching_doctors, min(len(matching_doctors), random.randint(5, 15)))
            
            # This triggers the Voucher creation signal
            event.doctors.add(*selected_doctors)
            events.append(event)
            
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(events)} events created with automatically distributed vouchers'))
        return events

    def _create_transactions(self, target_count, doctors, vendors):
        self.stdout.write(f'📄 Processing {target_count} dummy transactions...')
        
        # Get all doctors with active vouchers
        doctors_with_vouchers = list(Doctor.objects.filter(vouchers__is_active=True, vouchers__current_balance__gt=0).distinct())
        if not doctors_with_vouchers:
            self.stdout.write(self.style.ERROR('  ✗ No doctors with active vouchers found!'))
            return
            
        created = 0
        failed = 0
        
        for _ in range(target_count * 2): # limit iterations in case balance run out
            if created >= target_count or not doctors_with_vouchers:
                break
                
            doctor = random.choice(doctors_with_vouchers)
            active_vouchers = Voucher.objects.filter(doctor=doctor, is_active=True, current_balance__gt=0)
            total_balance = sum(v.current_balance for v in active_vouchers)
            
            # Management fee is 25%, so total deduction is 1.25 * amount_spent
            max_spendable = float(total_balance) / 1.25
            if max_spendable < 10:
                doctors_with_vouchers.remove(doctor)
                continue
                
            amount_spent = round(random.uniform(10, min(300, max_spendable)), 2)
            vendor = random.choice(vendors)
            
            try:
                with db_transaction.atomic():
                    process_transaction(
                        vendor=vendor,
                        doctor=doctor,
                        amount_spent=Decimal(str(amount_spent)),
                        items_description=random.choice(ITEMS_DESCRIPTIONS),
                        created_by=doctor.user
                    )
                created += 1
                if created % 200 == 0:
                    self.stdout.write(f'  ... processed {created}/{target_count} transactions')
            except Exception as e:
                failed += 1
                
        self.stdout.write(self.style.SUCCESS(f'  ✓ {created} transactions completed successfully ({failed} failed/skipped)'))

    def _create_transfers(self, count, doctors):
        self.stdout.write(f'🔄 Generating {count} voucher transfers between doctors...')
        transfers_created = 0
        
        for _ in range(count * 2):
            if transfers_created >= count:
                break
                
            # Find a doctor with at least one active voucher
            from_doc = random.choice(doctors)
            voucher = Voucher.objects.filter(doctor=from_doc, is_active=True, current_balance__gt=0).first()
            if not voucher:
                continue
                
            # Select target doctor
            to_doc = random.choice(doctors)
            if from_doc.id == to_doc.id:
                continue
                
            # Perform transfer
            with db_transaction.atomic():
                VoucherTransfer.objects.create(
                    from_doctor=from_doc,
                    to_doctor=to_doc,
                    voucher=voucher
                )
                
                transfer_note = f"تم التحويل من د. {from_doc.name} إلى د. {to_doc.name}"
                if voucher.notes:
                    voucher.notes += f"\n{transfer_note}"
                else:
                    voucher.notes = transfer_note
                
                voucher.doctor = to_doc
                voucher.save()
                
            transfers_created += 1
            
        self.stdout.write(self.style.SUCCESS(f'  ✓ {transfers_created} transfers recorded'))

    def _create_event_requests(self, count, companies, delegates, doctors, specialties):
        self.stdout.write(f'📝 Generating {count} Event Requests...')
        requests_created = 0
        
        for i in range(count):
            requester_type = random.choice(['COMPANY', 'DELEGATE'])
            company = random.choice(companies)
            delegate = random.choice(list(company.delegates.all())) if company.delegates.exists() else random.choice(delegates)
            
            requester_user = company.user if requester_type == 'COMPANY' else delegate.user
            
            event_name = f"طلب تنظيم: {random.choice(EVENT_NAMES)} {i+1}"
            voucher_val = Decimal(str(random.choice([200, 300, 500, 1000])))
            max_budget = voucher_val * Decimal(str(random.randint(15, 30)))
            
            # Status: PENDING, APPROVED, REJECTED
            status = random.choice(['PENDING', 'APPROVED', 'REJECTED'])
            
            req = EventRequest.objects.create(
                requester_user=requester_user,
                company=company,
                delegate=delegate,
                name=event_name,
                date=date.today() + timedelta(days=random.randint(10, 60)),
                voucher_value=voucher_val,
                max_budget=max_budget,
                notes=f"طلب تنظيم فعالية طبية لترويج المستحضرات الجديدة.",
                status=status
            )
            
            # Create requested doctors
            num_docs = random.randint(3, 8)
            selected_docs = random.sample(doctors, num_docs)
            for d in selected_docs:
                # 70% existing doctor, 30% new doctor
                if random.random() < 0.7:
                    EventRequestDoctor.objects.create(
                        event_request=req,
                        existing_doctor=d,
                        is_created=True
                    )
                else:
                    fn = random.choice(FIRST_NAMES)
                    ln = random.choice(LAST_NAMES)
                    EventRequestDoctor.objects.create(
                        event_request=req,
                        name=f"د. {fn} {ln}",
                        phone=f"059{random.randint(1000000, 9999999)}",
                        email=f"new_doc_{random.randint(1, 10000)}@hadramout.com",
                        specialty_name=random.choice(SPECIALTIES),
                        is_created=False
                    )
            
            requests_created += 1
            
        self.stdout.write(self.style.SUCCESS(f'  ✓ {requests_created} event requests generated'))

    def _create_company_settlements(self, companies):
        self.stdout.write('💵 Generating Company Settlements...')
        settlements_count = 0
        
        for company in companies[:40]: # Settle budget for 40 companies
            # Get events and vouchers
            events = company.events.all()
            if not events:
                continue
                
            total_budget = Decimal('0')
            total_distributed = Decimal('0')
            total_spent = Decimal('0')
            
            for event in events:
                total_budget += event.max_budget
                vouchers = event.vouchers.all()
                total_distributed += sum(v.initial_value for v in vouchers)
                for v in vouchers:
                    total_spent += v.consumed_amount
            
            if total_budget == 0:
                continue
                
            # Settle a random amount
            settlement_amount = total_spent * Decimal(str(round(random.uniform(0.7, 1.0), 2)))
            
            CompanySettlement.objects.create(
                company=company,
                total_budget_allocated=total_budget,
                total_vouchers_distributed=total_distributed,
                total_amount_spent=total_spent,
                settlement_amount=settlement_amount,
                settlement_date=date.today() - timedelta(days=random.randint(1, 10)),
                settlement_status=random.choice(['PENDING', 'PARTIAL', 'COMPLETED']),
                notes=f"تسوية مالية للميزانيات المستهلكة في الفعاليات لشركة {company.name}."
            )
            settlements_count += 1
            
        self.stdout.write(self.style.SUCCESS(f'  ✓ {settlements_count} company settlements generated'))

    def _create_delegate_settlements(self, delegates):
        self.stdout.write('💵 Generating Delegate Settlements...')
        settlements_count = 0
        
        for delegate in delegates[:40]: # Settle for 40 delegates
            companies = list(delegate.companies.all())
            if not companies:
                continue
                
            company = random.choice(companies)
            events_count = delegate.events.filter(company=company).count()
            if events_count == 0:
                continue
                
            # commission calculations
            commission_rate = Decimal('10.00')
            total_commission = Decimal(str(events_count * 350.00))
            
            DelegateSettlement.objects.create(
                delegate=delegate,
                company=company,
                events_assigned=events_count,
                doctors_registered=events_count * random.randint(5, 10),
                commission_rate=commission_rate,
                total_commission=total_commission,
                settlement_date=date.today() - timedelta(days=random.randint(1, 10)),
                settlement_status=random.choice(['PENDING', 'COMPLETED', 'DISPUTED']),
                notes=f"تسوية العمولات للمندوب {delegate.name} عن الفعاليات المشرف عليها لشركة {company.name}."
            )
            settlements_count += 1
            
        self.stdout.write(self.style.SUCCESS(f'  ✓ {settlements_count} delegate settlements generated'))

    def _create_vendor_settlements(self, vendors):
        self.stdout.write('💵 Generating Vendor Settlements...')
        settlements_count = 0
        
        for vendor in vendors:
            # Settle only for ADMIN role vendors
            if vendor.role != 'ADMIN':
                continue
                
            # Get all child cashiers to sum their transactions too
            vendors_pool = [vendor] + list(vendor.cashiers_list.all())
            
            # Find unsettled transactions
            unsettled_tx = Transaction.objects.filter(vendor__in=vendors_pool, settlement__isnull=True)
            if not unsettled_tx.exists():
                continue
                
            total_sales = unsettled_tx.aggregate(
                total_deducted=Sum('total_deducted'),
                amount_spent=Sum('amount_spent'),
                fee=Sum('management_fee_amount')
            )
            
            deducted = total_sales['total_deducted'] or Decimal('0.00')
            spent = total_sales['amount_spent'] or Decimal('0.00')
            fee = total_sales['fee'] or Decimal('0.00')
            
            if deducted == 0:
                continue
                
            # Settle the full outstanding amount
            settlement = VendorSettlement.objects.create(
                vendor=vendor,
                amount_settled=deducted,
                admin_commission_amount=fee,
                net_amount_to_vendor=spent,
                settlement_date=date.today() - timedelta(days=random.randint(1, 15)),
                settlement_status='COMPLETED',
                payment_method='CASH',
                notes=f"تسوية المبيعات المستحقة للتاجر {vendor.name} بعد خصم الرسوم الإدارية."
            )
            
            # Link transactions
            transactions_list = list(unsettled_tx)
            settlement.transactions.set(transactions_list)
            
            # Update legacy settlement field on Transaction
            unsettled_tx.update(settlement=settlement)
            settlements_count += 1
            
        self.stdout.write(self.style.SUCCESS(f'  ✓ {settlements_count} vendor settlements completed'))

    def _print_summary(self):
        self.stdout.write(f'📊 Seeding Summary:')
        self.stdout.write(f'   - Users:               {User.objects.count()}')
        self.stdout.write(f'   - Specialties:         {Specialty.objects.count()}')
        self.stdout.write(f'   - Companies:           {PharmaceuticalCompany.objects.count()}')
        self.stdout.write(f'   - Delegates:           {Delegate.objects.count()}')
        self.stdout.write(f'   - Doctors:             {Doctor.objects.count()}')
        self.stdout.write(f'   - Vendors:             {Vendor.objects.count()}')
        self.stdout.write(f'   - Events:              {Event.objects.count()}')
        self.stdout.write(f'   - Vouchers:            {Voucher.objects.count()}')
        self.stdout.write(f'   - Transactions:        {Transaction.objects.count()}')
        self.stdout.write(f'   - Voucher Transfers:   {VoucherTransfer.objects.count()}')
        self.stdout.write(f'   - Event Requests:      {EventRequest.objects.count()}')
        self.stdout.write(f'   - Company Settlements: {CompanySettlement.objects.count()}')
        self.stdout.write(f'   - Delegate Settlements:{DelegateSettlement.objects.count()}')
        self.stdout.write(f'   - Vendor Settlements:  {VendorSettlement.objects.count()}')
        self.stdout.write(f'   - Notifications:       {Notification.objects.count()}')
