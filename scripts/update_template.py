import os

filepath = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\templates\custom_admin\vendor_settlements.html"

new_content = """{% extends 'custom_admin/dashboard_base.html' %}

{% block title %}القسم المالي / التسويات - Arabic Retail Standard{% endblock %}

{% block sidebar %}
    {% include 'custom_admin/includes/sidebar.html' with active_page='settlements' %}
{% endblock %}

{% block extra_head %}
    <style>
        /* Shared Styles */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: var(--spacing-xl);
            margin-bottom: var(--spacing-xl);
        }
        
        .settlement-tabs {
            display: flex;
            gap: var(--spacing-sm);
            margin-bottom: var(--spacing-xl);
            border-bottom: 1px solid var(--surface-container-highest);
            padding-bottom: 10px;
        }
        .tab-btn {
            background: transparent;
            border: none;
            padding: 10px 20px;
            font-size: 1.1rem;
            color: var(--on-surface-variant);
            cursor: pointer;
            border-radius: var(--radius-md) var(--radius-md) 0 0;
            transition: all 0.2s;
        }
        .tab-btn.active {
            color: var(--primary);
            border-bottom: 3px solid var(--primary);
            font-weight: 700;
        }
        .tab-btn:hover:not(.active) {
            background: var(--surface-container-highest);
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }

        .list-container {
            display: flex;
            flex-direction: column;
            gap: var(--spacing-md);
        }

        .list-row {
            background-color: var(--surface-container-lowest);
            border-radius: var(--radius-xl);
            padding: var(--spacing-xl);
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
            overflow: hidden;
        }
        .list-row:hover {
            transform: scale(1.01);
            box-shadow: var(--shadow-ambient);
        }
        .list-row.status-pending::before {
            content: ''; position: absolute; top:0; bottom:0; right:0; width: 6px;
            background-color: var(--danger);
        }

        .avatar-box {
            width: 60px;
            height: 60px;
            border-radius: var(--radius-lg);
            background: var(--surface-container);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: var(--primary);
            flex-shrink: 0;
        }

        .settlement-calculator {
            background: var(--surface-container-lowest);
            border-radius: var(--radius-xl);
            padding: var(--spacing-xxl);
            box-shadow: var(--shadow-lg);
            width: 90%;
            max-width: 500px;
            transform: translateY(20px);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            max-height: 90vh;
            overflow-y: auto;
        }

        .glass-overlay.active .settlement-calculator {
            transform: translateY(0);
        }

        .calc-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: var(--spacing-md) 0;
            border-bottom: 1px dashed var(--surface-container-highest);
        }
        .calc-row:last-of-type {
            border-bottom: none;
            margin-top: 10px;
            padding-top: 20px;
            border-top: 2px solid var(--surface-container-highest);
        }
        .form-group {
            margin-bottom: var(--spacing-md);
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: var(--on-surface-variant);
        }
        .form-group input, .form-group select, .form-group textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid var(--outline-variant);
            border-radius: var(--radius-sm);
        }
    </style>
{% endblock %}

{% block content %}
    <header class="header-bar">
        <div>
            <h2 class="title-md" style="margin:0; color: var(--on-surface);">القسم المالي / التسويات</h2>
        </div>
        <div class="flex-row items-center gap-md">
            <button class="btn btn-secondary" style="border-radius: var(--radius-full);">
                <i class="fa-solid fa-file-export"></i> تصدير إكسيل
            </button>
            <div style="text-align: left;">
                <span class="title-sm" style="display: block;">إدارة النظام</span>
                <span class="label-md" style="color: var(--primary);">المالية</span>
            </div>
            <img src="https://ui-avatars.com/api/?name=Finance&background=005353&color=fff" alt="User" style="width: 40px; height: 40px; border-radius: 50%;">
        </div>
    </header>

    {% if messages %}
        <div class="mt-md">
            {% for message in messages %}
                <div style="padding: 15px; margin-bottom: 10px; border-radius: 8px; 
                            background-color: {% if message.tags == 'success' %}#e8f5e9{% else %}#ffebee{% endif %};
                            color: {% if message.tags == 'success' %}#1b5e20{% else %}#b71c1c{% endif %};">
                    {{ message }}
                </div>
            {% endfor %}
        </div>
    {% endif %}

    <div>
        <div class="metrics-grid mt-xl">
            <div class="pos-card pos-card-ambient relative overflow-hidden">
                <div style="position: absolute; left: -20px; top: -20px; font-size: 8rem; opacity: 0.03; color: var(--danger);">
                    <i class="fa-solid fa-clock-rotate-left"></i>
                </div>
                <span class="title-sm" style="color: var(--on-surface-variant);">إجمالي الديون المعلقة (للموردين)</span>
                <div class="display-lg num-font mt-md" style="color: var(--on-surface);">
                    {{ pending_vendor_debts|floatformat:2 }} <span class="title-md">ج.م</span>
                </div>
            </div>
            <div class="pos-card relative overflow-hidden" style="background-color: var(--primary); color: white;">
                <div style="position: absolute; left: -20px; top: -20px; font-size: 8rem; opacity: 0.1; color: white;">
                    <i class="fa-solid fa-percent"></i>
                </div>
                <span class="title-sm" style="color: rgba(255,255,255,0.7);">الرسوم الإدارية المتوقعة</span>
                <div class="display-lg num-font mt-md">
                    {{ expected_admin_fees|floatformat:2 }} <span class="title-md">ج.م</span>
                </div>
            </div>
        </div>

        <!-- Tabs Navigation -->
        <div class="settlement-tabs mt-xl">
            <button class="tab-btn active" onclick="switchTab('vendors', this)">تسويات الموردين</button>
            <button class="tab-btn" onclick="switchTab('companies', this)">تسويات الشركات</button>
            <button class="tab-btn" onclick="switchTab('delegates', this)">تسويات المناديب</button>
        </div>

        <!-- VENDORS TAB -->
        <div id="tab-vendors" class="tab-content active">
            <div class="flex-row justify-between items-center mb-md">
                <h2 class="headline-sm" style="margin: 0;">الموردين المستحقين</h2>
            </div>
            <div class="list-container">
                {% for data in pending_vendors %}
                <div class="list-row status-pending">
                    <div class="flex-row items-center gap-xl">
                        <div class="avatar-box" style="background:#fff3e0; color:#e65100;">
                            <i class="fa-solid fa-utensils"></i>
                        </div>
                        <div>
                            <h3 class="title-md" style="margin: 0; font-size: 1.2rem;">{{ data.vendor.name }}</h3>
                            <p class="label-md" style="margin: 5px 0 0 0;">كود: #VND-{{ data.vendor.id }}</p>
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <p class="label-md mb-sm">عدد الفواتير</p>
                        <span class="title-sm num-font" style="background:var(--surface-container-high); padding: 4px 12px; border-radius: var(--radius-full);">{{ data.invoices_count }}</span>
                    </div>
                    <div style="text-align: right; min-width: 150px;">
                        <p class="label-md mb-sm">الإجمالي غير المسدد</p>
                        <div class="title-md num-font" style="font-size: 1.5rem; font-weight: 700;">{{ data.debt|floatformat:2 }} ج.م</div>
                    </div>
                    <div>
                        <button class="btn btn-primary" style="padding: 0.8rem 1.5rem; border-radius: var(--radius-md);" 
                                onclick="openSettlementModal('vendor_settlement', '{{ data.vendor.id }}', '{{ data.vendor.name|escapejs }}', '{{ data.debt|stringformat:'f' }}', '{{ data.invoices_count }}')">
                            محاسبة وإصدار إيصال
                        </button>
                    </div>
                </div>
                {% empty %}
                <p>لا يوجد موردين لديهم مديونيات معلقة حالياً.</p>
                {% endfor %}
            </div>
            
            <div class="mt-xl">
                <h3 class="title-md mb-md">سجل تسويات الموردين السابقة</h3>
                <table style="width: 100%; border-collapse: collapse; text-align: right; background: white; border-radius: 8px; overflow: hidden; box-shadow: var(--shadow-sm);">
                    <tr style="border-bottom: 2px solid var(--outline-variant); background: var(--surface-container-lowest);">
                        <th style="padding: 15px;">المورد</th>
                        <th style="padding: 15px;">المبلغ</th>
                        <th style="padding: 15px;">التاريخ</th>
                        <th style="padding: 15px;">طريقة الدفع</th>
                        <th style="padding: 15px;">الحالة</th>
                    </tr>
                    {% for st in vendor_settlements %}
                    <tr style="border-bottom: 1px solid var(--surface-container-highest);">
                        <td style="padding: 15px;">{{ st.vendor.name }}</td>
                        <td style="padding: 15px; font-weight: bold;">{{ st.amount_settled }}</td>
                        <td style="padding: 15px;">{{ st.settlement_date }}</td>
                        <td style="padding: 15px;">{{ st.get_payment_method_display }}</td>
                        <td style="padding: 15px;">
                            <span style="background: var(--success); color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem;">{{ st.get_settlement_status_display }}</span>
                        </td>
                    </tr>
                    {% empty %}
                    <tr><td colspan="5" style="padding: 15px;">لا توجد تسويات سابقة.</td></tr>
                    {% endfor %}
                </table>
            </div>
        </div>

        <!-- COMPANIES TAB -->
        <div id="tab-companies" class="tab-content">
            <div class="flex-row justify-between items-center mb-md">
                <h2 class="headline-sm" style="margin: 0;">تسويات الشركات الدوائية</h2>
                <button class="btn btn-primary" onclick="openSettlementModal('company_settlement', '', '', 0, 0)">
                    <i class="fa-solid fa-plus"></i> تسوية شركة جديدة
                </button>
            </div>
            <div class="list-container">
                <table style="width: 100%; border-collapse: collapse; text-align: right; background: white; border-radius: 8px; overflow: hidden; box-shadow: var(--shadow-sm);">
                    <tr style="border-bottom: 2px solid var(--outline-variant); background: var(--surface-container-lowest);">
                        <th style="padding: 15px;">الشركة</th>
                        <th style="padding: 15px;">الميزانية المخصصة</th>
                        <th style="padding: 15px;">الموزع</th>
                        <th style="padding: 15px;">المستحق تسويته</th>
                        <th style="padding: 15px;">التاريخ</th>
                        <th style="padding: 15px;">الحالة</th>
                    </tr>
                    {% for st in company_settlements %}
                    <tr style="border-bottom: 1px solid var(--surface-container-highest);">
                        <td style="padding: 15px;">{{ st.company.name }}</td>
                        <td style="padding: 15px;">{{ st.total_budget_allocated }}</td>
                        <td style="padding: 15px;">{{ st.total_vouchers_distributed }}</td>
                        <td style="padding: 15px; font-weight: bold;">{{ st.settlement_amount }}</td>
                        <td style="padding: 15px;">{{ st.settlement_date }}</td>
                        <td style="padding: 15px;">
                            <span style="background: var(--success); color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem;">{{ st.get_settlement_status_display }}</span>
                        </td>
                    </tr>
                    {% empty %}
                    <tr><td colspan="6" style="padding: 15px;">لا توجد تسويات شركات سابقة.</td></tr>
                    {% endfor %}
                </table>
            </div>
        </div>

        <!-- DELEGATES TAB -->
        <div id="tab-delegates" class="tab-content">
            <div class="flex-row justify-between items-center mb-md">
                <h2 class="headline-sm" style="margin: 0;">تسويات المناديب</h2>
                <button class="btn btn-primary" onclick="openSettlementModal('delegate_settlement', '', '', 0, 0)">
                    <i class="fa-solid fa-plus"></i> تسوية مندوب جديدة
                </button>
            </div>
            <div class="list-container">
                <table style="width: 100%; border-collapse: collapse; text-align: right; background: white; border-radius: 8px; overflow: hidden; box-shadow: var(--shadow-sm);">
                    <tr style="border-bottom: 2px solid var(--outline-variant); background: var(--surface-container-lowest);">
                        <th style="padding: 15px;">المندوب</th>
                        <th style="padding: 15px;">الشركة</th>
                        <th style="padding: 15px;">العمولة المستحقة</th>
                        <th style="padding: 15px;">الفعاليات/الأطباء</th>
                        <th style="padding: 15px;">التاريخ</th>
                        <th style="padding: 15px;">الحالة</th>
                    </tr>
                    {% for st in delegate_settlements %}
                    <tr style="border-bottom: 1px solid var(--surface-container-highest);">
                        <td style="padding: 15px;">{{ st.delegate.name }}</td>
                        <td style="padding: 15px;">{{ st.company.name }}</td>
                        <td style="padding: 15px; font-weight: bold;">{{ st.total_commission }}</td>
                        <td style="padding: 15px;">{{ st.events_assigned }} / {{ st.doctors_registered }}</td>
                        <td style="padding: 15px;">{{ st.settlement_date }}</td>
                        <td style="padding: 15px;">
                            <span style="background: var(--success); color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem;">{{ st.get_settlement_status_display }}</span>
                        </td>
                    </tr>
                    {% empty %}
                    <tr><td colspan="6" style="padding: 15px;">لا توجد تسويات مناديب سابقة.</td></tr>
                    {% endfor %}
                </table>
            </div>
        </div>
    </div>
    
    <!-- Unified Settlement Form Modal -->
    <div class="glass-overlay" id="settlementOverlay">
        <div class="settlement-calculator">
            <button class="close-btn" type="button" style="position:absolute; top:20px; left:20px; background:transparent; border:none; font-size:1.5rem; cursor:pointer; color: var(--on-surface-variant);" onclick="closeSettlementModal()"><i class="fa-solid fa-xmark"></i></button>
            
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="width: 60px; height: 60px; background: var(--secondary-container); color: var(--primary); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; margin: 0 auto 10px auto;">
                    <i class="fa-solid fa-file-invoice-dollar"></i>
                </div>
                <h2 class="headline-sm" style="margin: 0; color: var(--on-surface);">إيصال تصفية</h2>
                <p class="title-sm" id="modalTargetName" style="color: var(--primary);">---</p>
                <span class="label-md" style="background: #e2e2e2; padding: 2px 8px; border-radius: 4px;" id="modalExtraInfo">---</span>
            </div>
            
            <form method="POST">
                {% csrf_token %}
                <input type="hidden" name="action" id="modalActionType">
                <input type="hidden" name="vendor_id" id="modalVendorId">
                
                <div id="companyDelegateInputs" style="display: none;">
                    <div class="form-group">
                        <label>معرف الشركة (ID):</label>
                        <input type="number" name="company_id" id="modalCompanyId">
                    </div>
                    <div class="form-group" id="delegateIdGroup">
                        <label>معرف المندوب (ID):</label>
                        <input type="number" name="delegate_id" id="modalDelegateId">
                    </div>
                </div>

                <div class="form-group">
                    <label>المبلغ المستحق (ج.م):</label>
                    <input type="number" step="0.01" name="amount" id="modalAmount" required>
                </div>
                
                <div class="form-group">
                    <label>تاريخ التسوية:</label>
                    <input type="date" name="date" id="modalDate" required>
                </div>
                
                <div class="form-group" id="paymentMethodGroup">
                    <label>طريقة الدفع:</label>
                    <select name="payment_method">
                        <option value="CASH">نقدي</option>
                        <option value="BANK">تحويل بنكي</option>
                        <option value="CHECK">شيك</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>ملاحظات (اختياري):</label>
                    <textarea name="notes" rows="2"></textarea>
                </div>

                <div class="flex-row gap-sm mt-md">
                    <button type="button" class="btn btn-secondary" style="flex:1; border-radius: var(--radius-md);" onclick="closeSettlementModal()">إلغاء</button>
                    <button type="submit" class="btn btn-primary" style="flex:2; border-radius: var(--radius-md);">
                        <i class="fa-solid fa-check-double"></i> اعتماد وحفظ
                    </button>
                </div>
            </form>
        </div>
    </div>
{% endblock %}

{% block extra_js %}
    <script>
        // Set today's date in modal by default
        document.getElementById('modalDate').valueAsDate = new Date();
        
        // Setup Tab Persistence
        function switchTab(tabId, btnElement) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            
            document.getElementById('tab-' + tabId).classList.add('active');
            if(btnElement) btnElement.classList.add('active');
            
            localStorage.setItem('activeSettlementsTab', tabId);
        }

        document.addEventListener('DOMContentLoaded', () => {
            const activeTab = localStorage.getItem('activeSettlementsTab');
            if (activeTab) {
                const btn = document.querySelector(`.tab-btn[onclick*="${activeTab}"]`);
                if (btn) switchTab(activeTab, btn);
            }
        });

        function openSettlementModal(type, targetId, targetName, amount, extraInfo) {
            document.getElementById('modalActionType').value = type;
            document.getElementById('modalAmount').value = amount;
            
            if (type === 'vendor_settlement') {
                document.getElementById('modalTargetName').innerText = targetName;
                document.getElementById('modalExtraInfo').innerText = extraInfo + ' فواتير معلقة';
                document.getElementById('modalVendorId').value = targetId;
                document.getElementById('companyDelegateInputs').style.display = 'none';
                document.getElementById('paymentMethodGroup').style.display = 'block';
            } else if (type === 'company_settlement') {
                document.getElementById('modalTargetName').innerText = "تسوية شركة جديدة";
                document.getElementById('modalExtraInfo').innerText = "برجاء إدخال بيانات التسوية";
                document.getElementById('companyDelegateInputs').style.display = 'block';
                document.getElementById('delegateIdGroup').style.display = 'none';
                document.getElementById('paymentMethodGroup').style.display = 'none';
            } else if (type === 'delegate_settlement') {
                document.getElementById('modalTargetName').innerText = "تسوية مندوب جديدة";
                document.getElementById('modalExtraInfo').innerText = "برجاء إدخال بيانات التسوية";
                document.getElementById('companyDelegateInputs').style.display = 'block';
                document.getElementById('delegateIdGroup').style.display = 'block';
                document.getElementById('paymentMethodGroup').style.display = 'none';
            }

            document.getElementById('settlementOverlay').classList.add('active');
        }

        function closeSettlementModal() {
            document.getElementById('settlementOverlay').classList.remove('active');
        }

        document.getElementById('settlementOverlay').addEventListener('click', function(e) {
            if(e.target === this) {
                closeSettlementModal();
            }
        });
    </script>
{% endblock %}
"""

with open(filepath, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Updated template successfully.")
