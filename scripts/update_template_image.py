import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\templates\custom_admin\vendor_settlements.html"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update form tag with enctype
content = content.replace("<form method=\"POST\">", "<form method=\"POST\" enctype=\"multipart/form-data\">")

# 2. Add input file in the modal form
notes_group = """                <div class="form-group">
                    <label>ملاحظات (اختياري):</label>
                    <textarea name="notes" rows="2"></textarea>
                </div>"""

image_group = """                <div class="form-group">
                    <label>ملاحظات (اختياري):</label>
                    <textarea name="notes" rows="2"></textarea>
                </div>
                
                <div class="form-group">
                    <label>إرفاق صورة الإيصال (اختياري):</label>
                    <input type="file" name="receipt_image" accept="image/*" style="border: none; padding: 5px 0;">
                </div>"""

content = content.replace(notes_group, image_group)

# 3. Update Vendors Table Headers & Rows
vendor_table_header = """                    <tr style="border-bottom: 2px solid var(--outline-variant); background: var(--surface-container-lowest);">
                        <th style="padding: 15px;">المورد</th>
                        <th style="padding: 15px;">المبلغ</th>
                        <th style="padding: 15px;">التاريخ</th>
                        <th style="padding: 15px;">طريقة الدفع</th>
                        <th style="padding: 15px;">الحالة</th>
                    </tr>"""

vendor_table_header_new = """                    <tr style="border-bottom: 2px solid var(--outline-variant); background: var(--surface-container-lowest);">
                        <th style="padding: 15px;">المورد</th>
                        <th style="padding: 15px;">المبلغ</th>
                        <th style="padding: 15px;">التاريخ</th>
                        <th style="padding: 15px;">طريقة الدفع</th>
                        <th style="padding: 15px;">الحالة</th>
                        <th style="padding: 15px;">الإيصال</th>
                    </tr>"""

content = content.replace(vendor_table_header, vendor_table_header_new)

vendor_table_row = """                    <tr style="border-bottom: 1px solid var(--surface-container-highest);">
                        <td style="padding: 15px;">{{ st.vendor.name }}</td>
                        <td style="padding: 15px; font-weight: bold;">{{ st.amount_settled }}</td>
                        <td style="padding: 15px;">{{ st.settlement_date }}</td>
                        <td style="padding: 15px;">{{ st.get_payment_method_display }}</td>
                        <td style="padding: 15px;">
                            <span style="background: var(--success); color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem;">{{ st.get_settlement_status_display }}</span>
                        </td>
                    </tr>"""

vendor_table_row_new = """                    <tr style="border-bottom: 1px solid var(--surface-container-highest);">
                        <td style="padding: 15px;">{{ st.vendor.name }}</td>
                        <td style="padding: 15px; font-weight: bold;">{{ st.amount_settled }}</td>
                        <td style="padding: 15px;">{{ st.settlement_date }}</td>
                        <td style="padding: 15px;">{{ st.get_payment_method_display }}</td>
                        <td style="padding: 15px;">
                            <span style="background: var(--success); color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem;">{{ st.get_settlement_status_display }}</span>
                        </td>
                        <td style="padding: 15px;">
                            {% if st.receipt_image %}
                                <a href="{{ st.receipt_image.url }}" target="_blank" style="color: var(--primary); font-weight: bold;"><i class="fa-solid fa-image"></i> عرض</a>
                            {% else %}
                                <span style="color: var(--on-surface-variant); opacity: 0.5;">لا يوجد</span>
                            {% endif %}
                        </td>
                    </tr>"""

content = content.replace(vendor_table_row, vendor_table_row_new)

# 4. Update Companies Table Headers & Rows
company_table_header = """                    <tr style="border-bottom: 2px solid var(--outline-variant); background: var(--surface-container-lowest);">
                        <th style="padding: 15px;">الشركة</th>
                        <th style="padding: 15px;">الميزانية المخصصة</th>
                        <th style="padding: 15px;">الموزع</th>
                        <th style="padding: 15px;">المستحق تسويته</th>
                        <th style="padding: 15px;">التاريخ</th>
                        <th style="padding: 15px;">الحالة</th>
                    </tr>"""

company_table_header_new = """                    <tr style="border-bottom: 2px solid var(--outline-variant); background: var(--surface-container-lowest);">
                        <th style="padding: 15px;">الشركة</th>
                        <th style="padding: 15px;">الميزانية المخصصة</th>
                        <th style="padding: 15px;">الموزع</th>
                        <th style="padding: 15px;">المستحق تسويته</th>
                        <th style="padding: 15px;">التاريخ</th>
                        <th style="padding: 15px;">الحالة</th>
                        <th style="padding: 15px;">الإيصال</th>
                    </tr>"""

content = content.replace(company_table_header, company_table_header_new)

company_table_row = """                    <tr style="border-bottom: 1px solid var(--surface-container-highest);">
                        <td style="padding: 15px;">{{ st.company.name }}</td>
                        <td style="padding: 15px;">{{ st.total_budget_allocated }}</td>
                        <td style="padding: 15px;">{{ st.total_vouchers_distributed }}</td>
                        <td style="padding: 15px; font-weight: bold;">{{ st.settlement_amount }}</td>
                        <td style="padding: 15px;">{{ st.settlement_date }}</td>
                        <td style="padding: 15px;">
                            <span style="background: var(--success); color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem;">{{ st.get_settlement_status_display }}</span>
                        </td>
                    </tr>"""

company_table_row_new = """                    <tr style="border-bottom: 1px solid var(--surface-container-highest);">
                        <td style="padding: 15px;">{{ st.company.name }}</td>
                        <td style="padding: 15px;">{{ st.total_budget_allocated }}</td>
                        <td style="padding: 15px;">{{ st.total_vouchers_distributed }}</td>
                        <td style="padding: 15px; font-weight: bold;">{{ st.settlement_amount }}</td>
                        <td style="padding: 15px;">{{ st.settlement_date }}</td>
                        <td style="padding: 15px;">
                            <span style="background: var(--success); color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem;">{{ st.get_settlement_status_display }}</span>
                        </td>
                        <td style="padding: 15px;">
                            {% if st.receipt_image %}
                                <a href="{{ st.receipt_image.url }}" target="_blank" style="color: var(--primary); font-weight: bold;"><i class="fa-solid fa-image"></i> عرض</a>
                            {% else %}
                                <span style="color: var(--on-surface-variant); opacity: 0.5;">لا يوجد</span>
                            {% endif %}
                        </td>
                    </tr>"""

content = content.replace(company_table_row, company_table_row_new)

# 5. Update Delegates Table Headers & Rows
delegate_table_header = """                    <tr style="border-bottom: 2px solid var(--outline-variant); background: var(--surface-container-lowest);">
                        <th style="padding: 15px;">المندوب</th>
                        <th style="padding: 15px;">الشركة</th>
                        <th style="padding: 15px;">العمولة المستحقة</th>
                        <th style="padding: 15px;">الفعاليات/الأطباء</th>
                        <th style="padding: 15px;">التاريخ</th>
                        <th style="padding: 15px;">الحالة</th>
                    </tr>"""

delegate_table_header_new = """                    <tr style="border-bottom: 2px solid var(--outline-variant); background: var(--surface-container-lowest);">
                        <th style="padding: 15px;">المندوب</th>
                        <th style="padding: 15px;">الشركة</th>
                        <th style="padding: 15px;">العمولة المستحقة</th>
                        <th style="padding: 15px;">الفعاليات/الأطباء</th>
                        <th style="padding: 15px;">التاريخ</th>
                        <th style="padding: 15px;">الحالة</th>
                        <th style="padding: 15px;">الإيصال</th>
                    </tr>"""

content = content.replace(delegate_table_header, delegate_table_header_new)

delegate_table_row = """                    <tr style="border-bottom: 1px solid var(--surface-container-highest);">
                        <td style="padding: 15px;">{{ st.delegate.name }}</td>
                        <td style="padding: 15px;">{{ st.company.name }}</td>
                        <td style="padding: 15px; font-weight: bold;">{{ st.total_commission }}</td>
                        <td style="padding: 15px;">{{ st.events_assigned }} / {{ st.doctors_registered }}</td>
                        <td style="padding: 15px;">{{ st.settlement_date }}</td>
                        <td style="padding: 15px;">
                            <span style="background: var(--success); color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem;">{{ st.get_settlement_status_display }}</span>
                        </td>
                    </tr>"""

delegate_table_row_new = """                    <tr style="border-bottom: 1px solid var(--surface-container-highest);">
                        <td style="padding: 15px;">{{ st.delegate.name }}</td>
                        <td style="padding: 15px;">{{ st.company.name }}</td>
                        <td style="padding: 15px; font-weight: bold;">{{ st.total_commission }}</td>
                        <td style="padding: 15px;">{{ st.events_assigned }} / {{ st.doctors_registered }}</td>
                        <td style="padding: 15px;">{{ st.settlement_date }}</td>
                        <td style="padding: 15px;">
                            <span style="background: var(--success); color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem;">{{ st.get_settlement_status_display }}</span>
                        </td>
                        <td style="padding: 15px;">
                            {% if st.receipt_image %}
                                <a href="{{ st.receipt_image.url }}" target="_blank" style="color: var(--primary); font-weight: bold;"><i class="fa-solid fa-image"></i> عرض</a>
                            {% else %}
                                <span style="color: var(--on-surface-variant); opacity: 0.5;">لا يوجد</span>
                            {% endif %}
                        </td>
                    </tr>"""

content = content.replace(delegate_table_row, delegate_table_row_new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated vendor_settlements.html with receipt image inputs and columns successfully.")
