import os
import django
import sys

sys.path.append('c:\\Users\\PC HOME\\OneDrive\\Desktop\\hadramout_events\\hadramout_events_final\\hadramout_events')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from accounts.models import User
from django.db.models import Count

print("=== Checking Duplicate Emails in User ===")
duplicates_email = User.objects.values('email').annotate(count=Count('id')).filter(count__gt=1)
for d in duplicates_email:
    print(f"Email: '{d['email']}', Count: {d['count']}")

print("=== Checking Duplicate Phones in User ===")
duplicates_phone = User.objects.values('phone').annotate(count=Count('id')).filter(count__gt=1)
for d in duplicates_phone:
    print(f"Phone: '{d['phone']}', Count: {d['count']}")
