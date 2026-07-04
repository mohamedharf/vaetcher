import os
import sys
import time
from deep_translator import GoogleTranslator
import polib

def main():
    po_filepath = r'locale/en/LC_MESSAGES/django.po'
    if not os.path.exists(po_filepath):
        print(f"File not found: {po_filepath}")
        return

    print("Loading PO file...")
    po = polib.pofile(po_filepath)
    
    # Custom Dictionary to override some wrong automatic translations
    custom_dict = {
        'نظام': 'System',
        'تسوية': 'Settlement',
        'التسويات': 'Settlements',
        'قسيمة': 'Voucher',
        'القسائم': 'Vouchers',
        'تاجر': 'Vendor',
        'مورد': 'Vendor',
        'طبيب': 'Doctor',
        'عميل': 'Client',
        'مندوب': 'Delegate',
        'مناديب': 'Delegates',
        'شركة': 'Company',
        'شركات': 'Companies',
        'إدارة': 'Admin',
        'الإعدادات': 'Settings',
        'الإشعارات': 'Notifications',
        'لوحة التحكم': 'Dashboard',
        'لوحة القياس': 'Dashboard',
        'قرية حضرموت': 'Hadramout Village',
        'نقطة البيع': 'POS',
    }

    translator = GoogleTranslator(source='ar', target='en')
    
    untranslated_entries = [entry for entry in po if not entry.msgstr or entry.msgstr == entry.msgid]
    total = len(untranslated_entries)
    print(f"Found {total} untranslated entries.")

    batch_size = 50
    for i in range(0, total, batch_size):
        batch = untranslated_entries[i:i+batch_size]
        texts_to_translate = []
        for entry in batch:
            # Check custom dict first
            text = entry.msgid
            if text in custom_dict:
                entry.msgstr = custom_dict[text]
                continue
                
            # Keep track of texts that need API translation
            texts_to_translate.append(text)
            
        if not texts_to_translate:
            continue
            
        print(f"Translating batch {i//batch_size + 1}/{(total//batch_size) + 1} ({len(texts_to_translate)} items)...")
        try:
            translations = translator.translate_batch(texts_to_translate)
            # Map back to entries
            idx = 0
            for entry in batch:
                if not entry.msgstr or entry.msgstr == entry.msgid:
                    entry.msgstr = translations[idx]
                    idx += 1
        except Exception as e:
            print(f"Error translating batch: {e}")
            # Fallback to translate one by one
            for entry in batch:
                if not entry.msgstr or entry.msgstr == entry.msgid:
                    try:
                        entry.msgstr = translator.translate(entry.msgid)
                    except Exception as inner_e:
                        print(f"Failed to translate '{entry.msgid}': {inner_e}")
        
        # Save every batch just in case
        po.save(po_filepath)
        time.sleep(1) # Be nice to the API

    # Fix fuzzy entries
    for entry in po:
        if 'fuzzy' in entry.flags:
            entry.flags.remove('fuzzy')

    po.save(po_filepath)
    print("Translation completed successfully!")

if __name__ == '__main__':
    main()
