import os
import polib

def main():
    po_filepath = r'locale/en/LC_MESSAGES/django.po'
    if not os.path.exists(po_filepath):
        print(f"File not found: {po_filepath}")
        return

    po = polib.pofile(po_filepath)
    
    # Custom Dictionary
    custom_dict = {
        'نظام': 'System',
        'تسوية': 'Settlement',
        'التسويات': 'Settlements',
        'قسيمة': 'Voucher',
        'القسائم': 'Vouchers',
        'تاجر': 'Vendor',
        'مورد': 'Vendor',
        'الموردين': 'Vendors',
        'طبيب': 'Doctor',
        'أطباء': 'Doctors',
        'الأطباء': 'Doctors',
        'عميل': 'Client',
        'مندوب': 'Delegate',
        'مناديب': 'Delegates',
        'شركة': 'Company',
        'شركات': 'Companies',
        'الشركات': 'Companies',
        'إدارة': 'Admin',
        'الإعدادات': 'Settings',
        'إشعارات': 'Notifications',
        'الإشعارات': 'Notifications',
        'لوحة التحكم': 'Dashboard',
        'لوحة القياس': 'Dashboard',
        'قرية حضرموت': 'Hadramout Village',
        'نقطة البيع': 'POS',
        'حفظ': 'Save',
        'إلغاء': 'Cancel',
        'تعديل': 'Edit',
        'حذف': 'Delete',
        'إضافة': 'Add',
        'بحث': 'Search',
        'تأكيد': 'Confirm',
        'الاسم': 'Name',
        'البريد الإلكتروني': 'Email',
        'رقم الهاتف': 'Phone Number',
        'الحالة': 'Status',
        'التاريخ': 'Date',
        'القيمة': 'Amount',
        'الرصيد': 'Balance',
        'تفاصيل': 'Details',
        'نشط': 'Active',
        'غير نشط': 'Inactive',
        'تسجيل خروج': 'Logout',
        'الملف الشخصي': 'Profile',
        'إجمالي الإيرادات': 'Total Revenue',
        'العمليات': 'Transactions',
        'الرئيسية': 'Home',
        'إيرادات هذا الشهر': 'This Month Revenue',
        'لوحة التحكم الرئيسية': 'Main Dashboard',
        'إجمالي الإيرادات الكلية': 'Total Revenue',
        'إجمالي العمولات المحصّلة': 'Total Collected Commissions',
        'التسويات المعلقة للموردين': 'Pending Vendor Settlements',
        'الأطباء النشطين': 'Active Doctors',
        'الموردين النشطين': 'Active Vendors',
        'الشركات الدوائية': 'Pharmaceutical Companies',
        'اتجاهات الاستهلاك (آخر 30 يوم)': 'Consumption Trends (Last 30 Days)',
        'توزيع التخصصات': 'Specialties Distribution',
        'حالة القسائم': 'Vouchers Status',
        'أفضل الفعاليات': 'Top Events',
        'الموردون الأكثر مبيعاً': 'Top Selling Vendors',
        'أحدث العمليات': 'Recent Transactions',
        'آخر الأطباء المسجلين': 'Recently Registered Doctors'
    }

    # First pass: exact matches
    for entry in po:
        text = entry.msgid.strip()
        if text in custom_dict:
            entry.msgstr = custom_dict[text]
        elif not entry.msgstr:
            # Fallback for now: just use the arabic text or empty
            pass

    # Fix fuzzy entries
    for entry in po:
        if 'fuzzy' in entry.flags:
            entry.flags.remove('fuzzy')

    po.save(po_filepath)
    print("Dictionary translation applied successfully!")

if __name__ == '__main__':
    main()
