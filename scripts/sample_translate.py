import re
import os

po_file = r'locale/en/LC_MESSAGES/django.po'
with open(po_file, 'r', encoding='utf-8') as f:
    content = f.read()

translations = {
    'Dashboard': 'Dashboard',
    'Notifications': 'Notifications',
    'System Admin': 'System Admin',
    'Main Dashboard': 'Main Dashboard',
    'Search in this page...': 'Search in this page...',
    'ago': 'ago',
    'new': 'new',
    'No notifications currently': 'No notifications currently',
    'Mark all as read': 'Mark all as read',
    'Interface Language': 'Interface Language',
    'Language': 'Language',
    'Doctors': 'Doctors',
    'Vendors': 'Vendors',
    'Companies': 'Companies',
    'Delegates': 'Delegates',
    'Specialties': 'Specialties',
    'Transactions': 'Transactions',
    'Vendor Settlements': 'Vendor Settlements',
    'Email Logs': 'Email Logs',
}

for ar, en in translations.items():
    pattern = r'(msgid "' + re.escape(ar) + r'"\n)msgstr ""'
    content = re.sub(pattern, r'\g<1>msgstr "' + en + '"', content)

with open(po_file, 'w', encoding='utf-8') as f:
    f.write(content)
print('Sample translations applied.')
