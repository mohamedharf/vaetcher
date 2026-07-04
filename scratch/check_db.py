import os
import django
import sys

# Set up Django environment
sys.path.append('c:\\Users\\PC HOME\\OneDrive\\Desktop\\hadramout_events\\hadramout_events_final\\hadramout_events')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from core.models import PharmaceuticalCompany
from accounts.models import Delegate, User

print("=== Pharmaceutical Companies ===")
for comp in PharmaceuticalCompany.objects.all().order_by('-id')[:10]:
    print(f"ID: {comp.id}, Name: {comp.name}, Phone: {comp.phone}, Email: {comp.email}, Deleted: {comp.is_deleted}")

print("\n=== Delegates ===")
for dele in Delegate.objects.all().order_by('-id')[:10]:
    print(f"ID: {dele.id}, Name: {dele.name}, Phone: {dele.phone}, Deleted: {dele.is_deleted}")

print("\n=== Users ===")
for user in User.objects.all().order_by('-id')[:10]:
    print(f"ID: {user.id}, Username: {user.username}, Email: {user.email}, Type: {user.type}, Active: {user.is_active}")
