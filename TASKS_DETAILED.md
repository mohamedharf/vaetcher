# 📋 قائمة المهام التفصيلية - نظام التسويات المتكامل

## 🎯 ملخص المشروع

| الميزة | الحالة | الأولوية |
|--------|--------|---------|
| Vendor Settlements (موجود) | ⚠️ Incomplete | 🔴 عالية جداً |
| Company Settlements (جديد) | ❌ Not Started | 🔴 عالية جداً |
| Delegate Settlements (جديد) | ❌ Not Started | 🔴 عالية جداً |
| Dynamic Data Loading | ❌ Not Started | 🔴 عالية جداً |
| API Endpoints | ❌ Not Started | 🔴 عالية جداً |

---

## 📝 المرحلة الأولى: تطوير Backend

### ✅ Task 1.01: إنشاء CompanySettlement Model
**الملف**: `core/models.py`

**الوصف**: إنشاء نموذج لتسويات الشركات الدوائية

**التفاصيل**:
```python
class CompanySettlement(models.Model):
    """
    تسويات الشركات الدوائية مع الإدارة
    الشركة تتلقى تمويلاً للفعاليات ثم يتم المحاسبة
    """
    company = models.ForeignKey(
        'core.PharmaceuticalCompany',
        on_delete=models.CASCADE,
        related_name='settlements'
    )
    
    # التمويل
    total_budget_allocated = models.DecimalField(
        _('Total Budget Allocated'),
        max_digits=12, decimal_places=2
    )
    
    # الاستخدام
    total_vouchers_distributed = models.DecimalField(
        _('Total Vouchers Distributed'),
        max_digits=12, decimal_places=2
    )
    total_amount_spent = models.DecimalField(
        _('Total Amount Spent by Doctors'),
        max_digits=12, decimal_places=2
    )
    
    # المستحق
    settlement_amount = models.DecimalField(
        _('Settlement Amount'),
        max_digits=12, decimal_places=2
    )
    settlement_date = models.DateField(_('Settlement Date'))
    settlement_status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('PENDING', 'معلق'),
            ('PARTIAL', 'تسوية جزئية'),
            ('COMPLETED', 'مكتمل'),
        ],
        default='PENDING'
    )
    
    # التفاصيل
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='created_company_settlements'
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Company Settlement')
        verbose_name_plural = _('Company Settlements')
        ordering = ['-settlement_date']
```

**المتطلبات الإضافية**:
- [ ] إضافة validation للتحقق من الأرقام
- [ ] إضافة method `get_unused_budget()`
- [ ] إضافة method `get_settlement_percentage()`

---

### ✅ Task 1.02: إنشاء DelegateSettlement Model
**الملف**: `core/models.py`

**الوصف**: إنشاء نموذج لتسويات المناديب مع الشركات

**التفاصيل**:
```python
class DelegateSettlement(models.Model):
    """
    تسويات المناديب مع الشركات الدوائية
    المندوب يعمل على فعاليات الشركة ويتلقى عمولة
    """
    delegate = models.ForeignKey(
        'accounts.Delegate',
        on_delete=models.CASCADE,
        related_name='settlements'
    )
    company = models.ForeignKey(
        'core.PharmaceuticalCompany',
        on_delete=models.CASCADE,
        related_name='delegate_settlements'
    )
    
    # الإحصائيات
    events_assigned = models.IntegerField(
        _('Events Assigned'),
        default=0
    )
    doctors_registered = models.IntegerField(
        _('Doctors Registered'),
        default=0
    )
    
    # العمولة
    commission_rate = models.DecimalField(
        _('Commission Rate (%)'),
        max_digits=5, decimal_places=2
    )
    total_commission = models.DecimalField(
        _('Total Commission'),
        max_digits=12, decimal_places=2
    )
    
    # التسوية
    settlement_date = models.DateField(_('Settlement Date'))
    settlement_status = models.CharField(
        _('Status'),
        max_length=20,
        choices=[
            ('PENDING', 'معلق'),
            ('COMPLETED', 'مكتمل'),
            ('DISPUTED', 'محل نزاع'),
        ],
        default='PENDING'
    )
    
    # التفاصيل
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='created_delegate_settlements'
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Delegate Settlement')
        verbose_name_plural = _('Delegate Settlements')
        ordering = ['-settlement_date']
```

---

### ✅ Task 1.03: تحسين VendorSettlement Model
**الملف**: `core/models.py`

**الوصف**: إضافة حقول وعلاقات جديدة لـ VendorSettlement

**التفاصيل** (الحقول الجديدة):
```python
# في class VendorSettlement:

# العلاقات
transactions = models.ManyToManyField(
    'core.Transaction',
    blank=True,
    related_name='vendor_settlement',
    verbose_name=_('Transactions Settled')
)

# الحسابات المالية
admin_commission_amount = models.DecimalField(
    _('Admin Commission Amount'),
    max_digits=12, decimal_places=2,
    default=0
)
net_amount_to_vendor = models.DecimalField(
    _('Net Amount to Vendor'),
    max_digits=12, decimal_places=2,
    default=0
)

# الحالة والتفاصيل
settlement_status = models.CharField(
    _('Status'),
    max_length=20,
    choices=[
        ('PENDING', 'معلق'),
        ('COMPLETED', 'مكتمل'),
        ('FAILED', 'فشل'),
    ],
    default='PENDING'
)
payment_method = models.CharField(
    _('Payment Method'),
    max_length=50,
    choices=[
        ('BANK', 'تحويل بنكي'),
        ('CASH', 'نقدي'),
        ('CHECK', 'شيك'),
    ],
    blank=True
)

# إضافة Methods:
def calculate_admin_commission(self):
    """حساب عمولة الإدارة من العمليات"""
    total_commission = self.transactions.aggregate(
        Sum('management_fee_amount')
    )['management_fee_amount__sum'] or 0
    return Decimal(total_commission)

def calculate_net_amount(self):
    """حساب الصافي المستحق للمورد"""
    total_spent = self.transactions.aggregate(
        Sum('amount_spent')
    )['amount_spent__sum'] or 0
    return Decimal(total_spent)
```

---

### ✅ Task 1.04: إنشاء Database Migrations
**الملف**: `core/migrations/`

**الوصف**: إنشاء ملفات Migration للـ Models الجديدة

**الخطوات**:
```bash
python manage.py makemigrations core
python manage.py migrate core
```

**التحقق**:
- [ ] التحقق من إنشاء الجداول بشكل صحيح
- [ ] اختبار إدراج بيانات تجريبية
- [ ] التحقق من العلاقات بين الجداول

---

### ✅ Task 1.05: إنشاء API Endpoints
**الملف**: `core/api_views.py` (ملف جديد أو إضافة لـ existing)

**الوصف**: إنشاء REST API للتعامل مع التسويات

**الـ Endpoints**:
```python
# 1. جلب قائمة Vendor Settlements
GET /api/settlements/vendors/
Response: {
    "count": 10,
    "results": [
        {
            "id": 1,
            "vendor": {
                "id": 1,
                "name": "مطاعم السرايا"
            },
            "total_sales": 8400.00,
            "admin_commission": 2100.00,
            "net_amount": 6300.00,
            "status": "PENDING"
        }
    ]
}

# 2. جلب Vendor Settlement محدد
GET /api/settlements/vendors/{id}/

# 3. إنشاء Vendor Settlement
POST /api/settlements/vendors/
Body: {
    "vendor_id": 1,
    "amount_settled": 6300.00,
    "settlement_date": "2024-05-30",
    "transactions": [1, 2, 3],
    "notes": "تصفية نهائية"
}

# 4. جلب Company Settlements
GET /api/settlements/companies/

# 5. جلب Delegate Settlements
GET /api/settlements/delegates/
```

**التفاصيل البرمجية**:
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

class VendorSettlementViewSet(viewsets.ModelViewSet):
    queryset = VendorSettlement.objects.all()
    serializer_class = VendorSettlementSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        """فقط الـ Admins يمكنهم رؤية التسويات"""
        if self.request.user.is_staff:
            return VendorSettlement.objects.all()
        return VendorSettlement.objects.none()
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """جلب التسويات المعلقة فقط"""
        pending = self.get_queryset().filter(settlement_status='PENDING')
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)

class CompanySettlementViewSet(viewsets.ModelViewSet):
    queryset = CompanySettlement.objects.all()
    serializer_class = CompanySettlementSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class DelegateSettlementViewSet(viewsets.ModelViewSet):
    queryset = DelegateSettlement.objects.all()
    serializer_class = DelegateSettlementSerializer
    permission_classes = [IsAuthenticated]
```

---

### ✅ Task 1.06: إنشاء Serializers
**الملف**: `core/serializers.py` (ملف جديد)

**الوصف**: إنشاء Serializers لتحويل Models إلى JSON

```python
from rest_framework import serializers
from .models import VendorSettlement, CompanySettlement, DelegateSettlement

class VendorSettlementSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    transaction_count = serializers.SerializerMethodField()
    
    class Meta:
        model = VendorSettlement
        fields = [
            'id', 'vendor', 'vendor_name', 'amount_settled',
            'settlement_date', 'admin_commission_amount',
            'net_amount_to_vendor', 'settlement_status',
            'transaction_count'
        ]
    
    def get_transaction_count(self, obj):
        return obj.transactions.count()
```

---

## 📝 المرحلة الثانية: تطوير Frontend

### ✅ Task 2.01: إعادة هيكلة Template الرئيسي
**الملف**: `templates/custom_admin/vendor_settlements.html`

**الوصف**: تحويل الصفحة من نمط واحد إلى دعم أنماط متعددة

**التعديلات**:
```html
<!-- إضافة Tabs Navigation -->
<div class="settlement-tabs">
    <button class="tab-btn active" data-tab="vendors" onclick="loadSettlements('vendors')">
        <i class="fa-solid fa-store"></i> تسويات الموردين
    </button>
    <button class="tab-btn" data-tab="companies" onclick="loadSettlements('companies')">
        <i class="fa-solid fa-building"></i> تسويات الشركات
    </button>
    <button class="tab-btn" data-tab="delegates" onclick="loadSettlements('delegates')">
        <i class="fa-solid fa-user-tie"></i> تسويات المناديب
    </button>
</div>

<!-- Dynamic Content Area -->
<div id="settlements-container" class="mt-xl"></div>
```

---

### ✅ Task 2.02: إنشاء JavaScript Module للـ Data Loading
**الملف**: `templates/custom_admin/includes/settlements_loader.js` (ملف جديد)

**الوصف**: تحميل البيانات ديناميكياً من API

```javascript
class SettlementsLoader {
    constructor() {
        this.currentType = 'vendors';
        this.data = {};
    }
    
    async loadSettlements(type) {
        try {
            const response = await fetch(`/api/settlements/${type}/`);
            const data = await response.json();
            this.data[type] = data;
            this.renderSettlements(type);
        } catch (error) {
            console.error('Error loading settlements:', error);
            this.showError('فشل تحميل البيانات');
        }
    }
    
    renderSettlements(type) {
        const container = document.getElementById('settlements-container');
        const data = this.data[type];
        
        if (type === 'vendors') {
            container.innerHTML = this.renderVendorsList(data);
        } else if (type === 'companies') {
            container.innerHTML = this.renderCompaniesList(data);
        } else if (type === 'delegates') {
            container.innerHTML = this.renderDelegatesList(data);
        }
    }
    
    renderVendorsList(data) {
        // سيتم تنفيذه في Task 2.03
    }
    
    // ... methods أخرى
}
```

---

### ✅ Task 2.03: إنشاء Vendor Settlements List
**الملف**: `templates/custom_admin/vendor_settlements.html`

**الوصف**: تحديث قائمة الموردين لتكون ديناميكية

**المكونات**:
- [ ] جدول الموردين المعلقين
- [ ] حسابات ديناميكية للمبالغ
- [ ] أزرار التسوية
- [ ] الألوان حسب الحالة

---

### ✅ Task 2.04: إنشاء Company Settlements List
**الملف**: `templates/custom_admin/includes/company_settlements.html` (ملف جديد)

**الوصف**: إنشاء قائمة تسويات الشركات

**المحتوى**:
```html
<div class="companies-settlements-container">
    <!-- Metrics -->
    <div class="metrics-grid">
        <div class="metric-card">
            <span>إجمالي الميزانيات</span>
            <div class="metric-value" id="total-budgets">0.00 ج.م</div>
        </div>
        <div class="metric-card">
            <span>الموزعة فعلاً</span>
            <div class="metric-value" id="total-distributed">0.00 ج.م</div>
        </div>
    </div>
    
    <!-- Companies Table -->
    <table class="settlements-table">
        <thead>
            <tr>
                <th>اسم الشركة</th>
                <th>الميزانية المخصصة</th>
                <th>الموزعة</th>
                <th>المستخدمة</th>
                <th>المتبقية</th>
                <th>عدد الفعاليات</th>
                <th>الإجراء</th>
            </tr>
        </thead>
        <tbody id="companies-tbody">
            <!-- تعمير ديناميكي -->
        </tbody>
    </table>
</div>
```

---

### ✅ Task 2.05: إنشاء Delegate Settlements List
**الملف**: `templates/custom_admin/includes/delegate_settlements.html` (ملف جديد)

**الوصف**: إنشاء قائمة تسويات المناديب

**المحتوى**: جدول يعرض:
- اسم المندوب
- الشركة المرتبطة به
- عدد الفعاليات المسندة
- عدد الأطباء المسجلين
- نسبة العمولة
- إجمالي العمولة المستحقة
- زر التسوية

---

### ✅ Task 2.06: تحديث Settlement Confirmation Modal
**الملف**: `templates/custom_admin/vendor_settlements.html`

**الوصف**: إضافة دعم لأنواع التسوية المختلفة

```html
<!-- Settlement Confirmation Modal -->
<div class="glass-overlay" id="settlementOverlay">
    <form class="settlement-calculator" id="settlementForm">
        <!-- Settlement Type Hidden -->
        <input type="hidden" id="settlementType" name="type" />
        <input type="hidden" id="settlementId" name="id" />
        
        <!-- Header -->
        <div style="text-align: center;">
            <div class="settlement-icon">
                <i class="fa-solid fa-file-invoice-dollar"></i>
            </div>
            <h2 id="settlementTitle">إيصال تصفية</h2>
            <p id="settlementSubtitle"></p>
        </div>
        
        <!-- Summary Section -->
        <div class="settlement-summary">
            <div class="calc-row">
                <span>الإجمالي المستحق</span>
                <span id="summaryTotal">0.00 ج.م</span>
            </div>
            <div class="calc-row" id="commissionRow" style="display: none;">
                <span>العمولة/الخصم</span>
                <span id="summaryCommission">0.00 ج.م</span>
            </div>
            <div class="calc-row">
                <span>المبلغ الصافي</span>
                <span id="summaryNet">0.00 ج.م</span>
            </div>
        </div>
        
        <!-- Form Fields -->
        <div class="form-group">
            <label>المبلغ المسدد:</label>
            <input type="number" name="amount" required step="0.01" />
        </div>
        
        <div class="form-group">
            <label>تاريخ التسوية:</label>
            <input type="date" name="date" required />
        </div>
        
        <div class="form-group">
            <label>طريقة الدفع:</label>
            <select name="payment_method">
                <option>تحويل بنكي</option>
                <option>نقدي</option>
                <option>شيك</option>
            </select>
        </div>
        
        <div class="form-group">
            <label>ملاحظات:</label>
            <textarea name="notes"></textarea>
        </div>
        
        <!-- Buttons -->
        <div class="form-actions">
            <button type="button" class="btn btn-secondary" onclick="closeSettlementModal()">
                إلغاء
            </button>
            <button type="submit" class="btn btn-primary">
                <i class="fa-solid fa-check"></i> تأكيد التسوية
            </button>
        </div>
    </form>
</div>
```

---

### ✅ Task 2.07: إضافة Event Handlers والـ Validation
**الملف**: `templates/custom_admin/vendor_settlements.html` (في قسم extra_js)

**الوصف**: معالجة Form Submission والـ Validation

```javascript
// Form Submission
document.getElementById('settlementForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const settlementType = formData.get('type');
    
    try {
        const response = await fetch(`/api/settlements/${settlementType}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(Object.fromEntries(formData))
        });
        
        if (response.ok) {
            showSuccess('تم التسوية بنجاح');
            closeSettlementModal();
            loadSettlements(settlementType);
        } else {
            showError('فشلت عملية التسوية');
        }
    } catch (error) {
        showError('حدث خطأ: ' + error.message);
    }
});
```

---

## 📊 المرحلة الثالثة: الميزات الإضافية

### ✅ Task 3.01: إضافة البحث والفلترة
- [ ] حقل بحث بالاسم
- [ ] فلترة حسب الحالة (معلق/مكتمل)
- [ ] فلترة حسب نطاق التاريخ
- [ ] ترتيب الجدول (Sort)

### ✅ Task 3.02: إضافة Pagination
- [ ] تقسيم النتائج إلى صفحات
- [ ] عدد عناصر لكل صفحة قابل للتعديل
- [ ] ملخص العدد الإجمالي

### ✅ Task 3.03: إضافة Export/Print
- [ ] تصدير إلى CSV
- [ ] تصدير إلى Excel
- [ ] طباعة الإيصالات
- [ ] طباعة التقارير الشهرية

### ✅ Task 3.04: إضافة History/Audit Trail
- [ ] عرض التسويات السابقة
- [ ] سجل التغييرات
- [ ] معلومات من قام بالتسوية ومتى

---

## 🧪 المرحلة الرابعة: الاختبار

### ✅ Task 4.01: Unit Tests
- [ ] اختبار Models
- [ ] اختبار Methods والـ Validation
- [ ] اختبار الحسابات المالية

### ✅ Task 4.02: API Tests
- [ ] اختبار GET Endpoints
- [ ] اختبار POST Endpoints
- [ ] اختبار Authorization
- [ ] اختبار Error Handling

### ✅ Task 4.03: Frontend Tests
- [ ] اختبار تحميل البيانات
- [ ] اختبار Form Submission
- [ ] اختبار Error Messages
- [ ] اختبار Responsive Design

---

## 📅 الجدول الزمني المقترح

| المرحلة | المهام | المدة المقدرة | التاريخ المتوقع |
|--------|-------|------------|----------------|
| المرحلة 1 | Backend | 3-4 أيام | 31 مايو - 2 يونيو |
| المرحلة 2 | Frontend | 4-5 أيام | 3-7 يونيو |
| المرحلة 3 | Features | 2-3 أيام | 8-10 يونيو |
| المرحلة 4 | Testing | 2-3 أيام | 11-13 يونيو |
| **الإجمالي** | | **11-15 يوم** | |

---

## 📎 ملاحظات هامة

### قبل البدء:
- [ ] عمل Backup لقاعدة البيانات
- [ ] إنشاء branch جديد في Git
- [ ] تجهيز بيئة التطوير

### أثناء التطوير:
- [ ] اختبار كل Task على الفور
- [ ] توثيق الكود بشكل جيد
- [ ] عمل commit منتظمة

### بعد الانتهاء:
- [ ] عمل full testing
- [ ] عمل code review
- [ ] تحضير documentation
- [ ] عمل deployment

---

**آخر تحديث**: 30 مايو 2026
**الحالة**: جاهز للتنفيذ
