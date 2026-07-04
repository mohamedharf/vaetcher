import os
import django
import random
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from accounts.models import User, Doctor, Delegate, Vendor, Specialty
from core.models import PharmaceuticalCompany, Transaction, VendorSettlement, CompanySettlement, DelegateSettlement
from events.models import EventRequest, EventRequestDoctor, Event, Voucher
from faker import Faker

fake = Faker('ar_SA')

def run():
    print("Starting Dummy Data Generation...")
    
    # Check if we have basic entities
    companies = list(PharmaceuticalCompany.objects.filter(is_deleted=False))
    delegates = list(Delegate.objects.filter(is_deleted=False))
    doctors = list(Doctor.objects.filter(is_deleted=False))
    vendors = list(Vendor.objects.filter(is_deleted=False))
    
    if not all([companies, delegates, doctors, vendors]):
        print("Please ensure you have at least 1 Company, 1 Delegate, 1 Doctor, and 1 Vendor in the database.")
        return

    # 1. Create a few Event Requests
    for _ in range(5):
        company = random.choice(companies)
        delegate = random.choice(delegates) if random.random() > 0.5 else None
        
        req = EventRequest.objects.create(
            requester_user=company.user if company.user else User.objects.first(),
            company=company,
            delegate=delegate,
            name=f"ندوة {fake.company()} الطبية",
            date=timezone.now().date() + timedelta(days=random.randint(1, 30)),
            voucher_value=Decimal(random.choice(['50.00', '100.00', '150.00'])),
            max_budget=Decimal(random.choice(['1000.00', '2000.00', '5000.00'])),
            status='PENDING'
        )
        
        # Add doctors to request
        for _ in range(random.randint(2, 5)):
            doc = random.choice(doctors)
            EventRequestDoctor.objects.create(
                event_request=req,
                existing_doctor=doc,
                is_created=True
            )
            
    print("Created Event Requests.")

    # 2. Approve some requests to create Events and Vouchers
    requests = EventRequest.objects.filter(status='PENDING')[:3]
    for req in requests:
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
                    current_balance=req.voucher_value,
                    expiry_date=req.date + timedelta(days=30)
                )
        
        req.status = 'APPROVED'
        req.save()
        
    print("Approved Events and created Vouchers.")

    # 3. Create Transactions (Doctors spending Vouchers at Vendors)
    vouchers = list(Voucher.objects.filter(is_active=True))
    for voucher in vouchers[:5]: # Take 5 vouchers
        if voucher.current_balance <= 0: continue
        
        vendor = random.choice(vendors)
        spend_amount = min(voucher.current_balance, Decimal(random.randint(20, 50)))
        
        # Deduct from voucher
        voucher.current_balance -= spend_amount
        if voucher.current_balance <= 0:
            voucher.is_active = False
        voucher.save()
        
        management_fee_rate = vendor.management_fee_percentage / Decimal('100.00')
        management_fee = spend_amount * management_fee_rate
        net_to_vendor = spend_amount - management_fee
        
        transaction = Transaction.objects.create(
            doctor=voucher.doctor,
            vendor=vendor,
            amount_spent=spend_amount,
            management_fee_percentage=vendor.management_fee_percentage,
            management_fee_amount=management_fee,
            total_deducted=net_to_vendor, # net amount to vendor
            invoice_number=f"INV-{fake.random_int(1000, 9999)}",
            
        )
        transaction.vouchers.add(voucher)
        
    print("Created Transactions.")

    # 4. Create Vendor Settlements
    for vendor in vendors[:2]:
        unsettled_transactions = Transaction.objects.filter(vendor=vendor, is_settled=False)
        if unsettled_transactions.exists():
            total_spent = sum(t.amount_spent for t in unsettled_transactions)
            total_commission = sum(t.management_fee_amount for t in unsettled_transactions)
            total_net = sum(t.total_deducted for t in unsettled_transactions)
            
            settlement = VendorSettlement.objects.create(
                vendor=vendor,
                amount_settled=total_spent,
                management_fee_amount=total_commission,
                net_amount_to_vendor=total_net,
                settlement_date=timezone.now().date(),
                settlement_status='COMPLETED'
            )
            for t in unsettled_transactions:
                settlement.transactions.add(t)
                t.is_settled = True
                t.save()
                
    print("Created Vendor Settlements.")

    # 5. Create Company Settlements
    for company in companies[:2]:
        # Company owes for what doctors consumed
        # Consumed = initial_value - current_balance for its vouchers
        vouchers = Voucher.objects.filter(company=company)
        consumed = sum(v.initial_value - v.current_balance for v in vouchers)
        
        if consumed > 0:
            CompanySettlement.objects.create(
                company=company,
                total_budget_allocated=sum(v.initial_value for v in vouchers),
                total_vouchers_distributed=sum(v.initial_value for v in vouchers),
                total_amount_spent=consumed,
                settlement_amount=consumed / 2, # Partial settlement
                settlement_date=timezone.now().date(),
                settlement_status='PARTIAL'
            )
            
    print("Created Company Settlements.")
    
    # 6. Create Delegate Settlements
    for delegate in delegates[:2]:
        # Delegate owes for what doctors consumed from his events
        vouchers = Voucher.objects.filter(event__delegates=delegate)
        consumed = sum(v.initial_value - v.current_balance for v in vouchers)
        
        if consumed > 0:
            DelegateSettlement.objects.create(
                delegate=delegate,
                total_budget_allocated=sum(v.initial_value for v in vouchers),
                total_vouchers_distributed=sum(v.initial_value for v in vouchers),
                total_amount_spent=consumed,
                settlement_amount=consumed / 2, # Partial settlement
                settlement_date=timezone.now().date(),
                settlement_status='PARTIAL'
            )
            
    print("Created Delegate Settlements.")
    print("Done!")

if __name__ == '__main__':
    run()
