import os
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import Doctor, Delegate, Vendor, Specialty
from core.models import PharmaceuticalCompany, CompanySettlement, DelegateSettlement
from events.models import Event, Voucher
from core.models import Transaction

def create_user(username, email, password='password123'):
    user, created = User.objects.get_or_create(username=username, defaults={'email': email})
    if created:
        user.set_password(password)
        user.save()
    return user

def run():
    print("Starting database population with financial data...")

    # 1. Create Specialties
    specialties_names = ['Cardiology', 'Neurology', 'Pediatrics', 'Orthopedics', 'General Surgery']
    specialties = []
    for name in specialties_names:
        sp, _ = Specialty.objects.get_or_create(name=name)
        specialties.append(sp)

    # 2. Create Vendors (Merchants)
    vendor_names = ['KFC Restaurant', 'El-Ezaby Pharmacy', 'Starbucks', 'Seif Pharmacy', 'McDonalds']
    vendors = []
    for i, v_name in enumerate(vendor_names):
        user = create_user(f'vendor_{i}', f'vendor{i}@example.com')
        vendor, _ = Vendor.objects.get_or_create(
            user=user, 
            defaults={
                'name': v_name, 
                'phone': f'010000000{i}',
                'address': f'Street {i}, Cairo'
            }
        )
        vendors.append(vendor)

    # 3. Create Doctors
    doctors = []
    for i in range(10):
        user = create_user(f'doc_{i}', f'doc{i}@example.com')
        doc, _ = Doctor.objects.get_or_create(
            user=user,
            defaults={
                'name': f'Dr. Name {i}',
                'phone': f'011000000{i}',
                'specialty': random.choice(specialties),
                'email': f'doc{i}@example.com'
            }
        )
        doctors.append(doc)

    # 4. Create Companies
    companies = []
    for i in range(3):
        user = create_user(f'company_{i}', f'comp{i}@example.com')
        comp, _ = PharmaceuticalCompany.objects.get_or_create(
            user=user,
            defaults={
                'name': f'Pharma Company {i}',
                'contact_person': f'Manager {i}',
                'phone': f'012000000{i}',
                'email': f'comp{i}@example.com',
                'address': f'Pharma Blvd {i}'
            }
        )
        for _ in range(random.randint(1, 3)):
            comp.specialties.add(random.choice(specialties))
        companies.append(comp)

    # 5. Create Delegates
    delegates = []
    for i in range(5):
        user = create_user(f'delegate_{i}', f'del{i}@example.com')
        delegate, _ = Delegate.objects.get_or_create(
            user=user,
            defaults={
                'name': f'Delegate {i}',
                'phone': f'015000000{i}'
            }
        )
        # Assign delegate to 1 or 2 companies
        delegate.companies.add(*random.sample(companies, random.randint(1, 2)))
        for _ in range(random.randint(1, 3)):
            delegate.specialties.add(random.choice(specialties))
        delegates.append(delegate)

    # 6. Create Events & Vouchers & Transactions & Settlements
    print("Creating Events, Vouchers, and Transactions...")
    
    now = timezone.now()
    
    for _ in range(15): # Create 15 Random Events
        company = random.choice(companies)
        
        # safely pick a delegate belonging to this company
        company_dels = delegate.companies.filter(id=company.id)
        if not delegate.companies.filter(id=company.id).exists():
            delegate.companies.add(company) # Ensure relationship
        
        event_date = now.date() - timedelta(days=random.randint(1, 60))
        voucher_val = Decimal(random.choice([500, 1000, 2000]))
        budget = voucher_val * random.randint(5, 15)
        
        event = Event.objects.create(
            name=f'Event for {company.name} - {event_date.strftime("%B")}',
            date=event_date,
            company=company,
            payment_type=random.choice(['CASH', 'DEFERRED']),
            voucher_value=voucher_val,
            max_budget=budget,
            voucher_expiry_days=90
        )
        event.delegates.add(delegate)
        event.specialties.add(random.choice(specialties))
        
        # Create Vouchers for this Event
        event_doctors = random.sample(doctors, random.randint(3, 8))
        event.doctors.add(*event_doctors)
        
        for doc in event_doctors:
            voucher = Voucher.objects.create(
                doctor=doc,
                event=event,
                company=company,
                initial_value=voucher_val,
                current_balance=voucher_val,
                expiry_date=event_date + timedelta(days=90)
            )
            # Override created_at for history logic
            Voucher.objects.filter(id=voucher.id).update(created_at=now - timedelta(days=random.randint(1, 60)))
            
            # Create Transactions for some Vouchers
            if random.random() > 0.3: # 70% chance voucher is used
                vendor = random.choice(vendors)
                spend_amount = Decimal(random.randint(100, int(voucher.current_balance)))
                
                txn = Transaction.objects.create(
                    doctor=doc,
                    vendor=vendor,
                    amount_spent=spend_amount,
                    payment_status='COMPLETED'
                )
                txn.vouchers.add(voucher)
                
                # Update voucher balance
                voucher.current_balance -= spend_amount
                voucher.save()
                
                # Override txn date
                Transaction.objects.filter(id=txn.id).update(transaction_date=now - timedelta(days=random.randint(1, 30)))

    # 7. Create Settlements
    print("Creating Settlements...")
    for comp in companies:
        CompanySettlement.objects.create(
            company=comp,
            amount_requested=Decimal(random.randint(5000, 20000)),
            status=random.choice(['PENDING', 'APPROVED', 'PAID']),
            due_date=now.date() + timedelta(days=random.randint(1, 30))
        )
        
    for d in delegates:
        for c in d.companies.all():
            DelegateSettlement.objects.create(
                delegate=d,
                company=c,
                settlement_amount=Decimal(random.randint(1000, 5000)),
                settlement_status=random.choice(['PENDING', 'COMPLETED']),
                settlement_date=now - timedelta(days=random.randint(1, 30))
            )

    print("Data population successful!")

if __name__ == '__main__':
    run()
