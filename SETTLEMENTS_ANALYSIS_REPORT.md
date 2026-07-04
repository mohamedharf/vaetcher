# تقرير تحليل شامل - صفحة التسويات والمستحقات

---

## 📋 جدول المحتويات
1. [تحليل الوضع الحالي](#تحليل-الوضع-الحالي)
2. [تحليل Frontend الحالي](#تحليل-frontend-الحالي)
3. [تحليل Backend الحالي](#تحليل-backend-الحالي)
4. [المتطلبات الجديدة](#المتطلبات-الجديدة)
5. [التعديلات المطلوبة على Backend](#التعديلات-المطلوبة-على-backend)
6. [التعديلات المطلوبة على Frontend](#التعديلات-المطلوبة-على-frontend)
7. [قائمة Tasks المراد تنفيذها](#قائمة-tasks-المراد-تنفيذها)

---

## تحليل الوضع الحالي

### الصفحة الحالية: `http://127.0.0.1:8000/ar/custom-settlements/`

#### ✅ ما هو موجود حالياً:
- **صفحة Frontend** بتصميم جميل وحديث يعرض:
  - إجمالي الديون المعلقة للموردين
  - الرسوم الإدارية المكتسبة
  - قائمة الموردين مع الديون المعلقة
  - Modal لإصدار إيصال تصفية نهائي

- **Model في Backend**: `VendorSettlement`
  ```python
  - vendor (FK to Vendor)
  - amount_settled (الرقم المبلغ)
  - settlement_date
  - عملية خصم من رصيد الطبيب
  ```

- **Transaction Model**: يسجل كل عملية شراء وينسب الرسوم الإدارية (25%)

#### ❌ ما ينقص:
- **البيانات الفعلية**: الصفحة تعرض بيانات وهمية (hardcoded)
- **حساب ديناميكي**: لا يتم حساب الديون من قاعدة البيانات
- **أنماط التسوية**: نمط واحد فقط (Admin → Vendor)
  - **غير موجود**: Company → Admin
  - **غير موجود**: Delegate → Company

---

## تحليل Frontend الحالي

### ملف: `templates/custom_admin/vendor_settlements.html`

#### 🎨 المميزات الموجودة:
```html
✅ Header Bar مع معلومات المستخدم
✅ Metrics Grid يعرض الإحصائيات العامة
✅ Vendor List مع تصنيفات اللون حسب الحالة:
   - Red (status-pending): ديون مرتفعة
   - Yellow (status-warn): ديون متوسطة
   - Green (status-good): ديون منخفضة أو تم سدادها
✅ Settlement Calculator Modal (Glassmorphism)
✅ حسابات الرسوم الإدارية في Modal
```

#### ⚙️ الوظائف الموجودة:
- `openSettlementModal()` - فتح modal التصفية
- `closeSettlementModal()` - إغلاق Modal
- `confirmSettlement()` - تأكيد التصفية (placeholder)
- `formatMoney()` - تنسيق الأرقام

#### 🔧 ما ينقص:
- اتصال حقيقي بـ Backend لجلب البيانات
- معالجة الـ POST request لحفظ التسويات
- دعم أنماط تسوية متعددة
- Pagination للقوائم الطويلة
- فلترة وبحث فعال
- تصدير Excel للتقارير

---

## تحليل Backend الحالي

### View: `CustomVendorSettlementsView`
```python
class CustomVendorSettlementsView(LoginRequiredMixin, VendorAdminRequiredMixin, TemplateView):
    template_name = 'custom_admin/vendor_settlements.html'
```

**الحالة**: ✅ موجود لكن فارغ (لا يمرر بيانات للـ Template)

### Model: `VendorSettlement` 
```python
class VendorSettlement(models.Model):
    vendor = models.ForeignKey('accounts.Vendor', ...)
    amount_settled = models.DecimalField(max_digits=12, decimal_places=2)
    settlement_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        # يتحقق من كفاية الرصيد المتاح
```

### العلاقات المالية الموجودة:
```
Vendor ← Transaction → Doctor
             ↓
          Voucher (deduction)
             
VendorSettlement ← links vendors to settled transactions
```

### 🔴 المشاكل:
1. **VendorSettlement** تفتقر إلى:
   - العلاقة المباشرة بـ Transactions
   - Tracking للعمليات المسوّاة
   - سجل دقيق للتسويات

2. **غير موجود**:
   - `CompanySettlement` (الشركات → Admin)
   - `DelegateSettlement` (المناديب → الشركات)
   - نموذج عام قابل للاستخدام لأنماط متعددة

---

## المتطلبات الجديدة

### 🎯 أنواع التسويات الثلاثة المطلوبة:

#### 1️⃣ **Vendor Settlement** (Admin ← Vendor) ✅ 
   - **القائم بالتسوية**: Admin
   - **المستقبل**: Vendor (صاحب المتجر)
   - **مصدر الأموال**: Transactions (عمليات الشراء)
   - **الحساب**: 
     ```
     Available Balance = Σ(amount_spent) - Σ(amount_settled)
     Admin Commission = Σ(management_fee_amount)
     Net to Vendor = amount_spent - admin_commission
     ```

#### 2️⃣ **Company Settlement** (Admin ← Company) 🆕
   - **القائم بالتسوية**: Admin
   - **المستقبل**: Pharmaceutical Company (منظمة الفعالية)
   - **مصدر الأموال**: Events (الفعاليات الممولة)
   - **الحساب**:
     ```
     Company Spending = Σ(max_budget) per Event
     Already Spent = Σ(voucher.initial_value) distributed
     Remaining Budget = max_budget - total_distributed
     Settlement Amount = what company paid vs what was used
     ```

#### 3️⃣ **Delegate Settlement** (Company ← Delegate) 🆕
   - **القائم بالتسوية**: Pharmaceutical Company
   - **المستقبل**: Delegate (المندوب)
   - **مصدر الأموال**: Event assignments + doctor registrations
   - **الحساب**:
     ```
     Delegates assigned to events
     Commission per doctors registered/attended
     Settlement based on performance metrics
     ```

---

## التعديلات المطلوبة على Backend

### 📝 1. إنشاء نماذج جديدة

#### أ) CompanySettlement Model
```python
class CompanySettlement(models.Model):
    company = models.ForeignKey(PharmaceuticalCompany, ...)
    total_budget_allocated = models.DecimalField()
    total_vouchers_distributed = models.DecimalField()
    total_amount_spent = models.DecimalField()
    settlement_amount = models.DecimalField()
    settlement_date = models.DateField()
    notes = models.TextField()
    created_by = models.ForeignKey(User, ...)  # Admin user
```

#### ب) DelegateSettlement Model
```python
class DelegateSettlement(models.Model):
    delegate = models.ForeignKey(Delegate, ...)
    company = models.ForeignKey(PharmaceuticalCompany, ...)
    events_assigned = models.IntegerField()
    doctors_registered = models.IntegerField()
    commission_rate = models.DecimalField()  # %
    total_commission = models.DecimalField()
    settlement_date = models.DateField()
    created_by = models.ForeignKey(User, ...)  # Company admin
```

### 📝 2. تحسين VendorSettlement
```python
# إضافة علاقة مع Transactions
class VendorSettlement(models.Model):
    # ... الحقول الموجودة ...
    transactions = models.ManyToManyField(Transaction, blank=True)
    admin_commission_amount = models.DecimalField(default=0)
    net_amount_to_vendor = models.DecimalField()
```

### 📝 3. إضافة Methods للحسابات
```python
# في VendorSettlement
def get_pending_transactions(self):
    """جلب العمليات المعلقة للتاجر"""
    
def calculate_total_due(self):
    """حساب الإجمالي المستحق"""
    
def get_available_balance(self):
    """الرصيد المتاح للتسوية"""

# في CompanySettlement  
def get_event_summary(self):
    """ملخص الفعاليات والميزانيات"""
    
def calculate_unused_budget(self):
    """حساب الميزانية غير المستخدمة"""

# في DelegateSettlement
def get_assigned_events(self):
    """الفعاليات المنسوبة للمندوب"""
    
def calculate_performance_score(self):
    """حساب درجة الأداء"""
```

### 🔌 4. APIs/Views المطلوبة
```python
# API endpoints للـ Frontend

class VendorSettlementsListAPI(APIView):
    """جلب قائمة الموردين مع الديون المعلقة"""
    
class CompanySettlementsListAPI(APIView):
    """جلب قائمة الشركات مع الميزانيات"""
    
class DelegateSettlementsListAPI(APIView):
    """جلب قائمة المناديب مع العمولات"""
    
class CreateSettlementAPI(APIView):
    """API لإنشاء عملية تسوية جديدة"""
    POST - Save settlement and mark transactions/events as settled
```

---

## التعديلات المطلوبة على Frontend

### 🎨 1. تحويل الصفحة من Single إلى Multi-Settlement

#### أ) إضافة Tabs/Navigation
```html
<div class="settlement-tabs">
  <button class="tab-btn active" data-tab="vendors">
    Vendor Settlements (Admin ← Vendor)
  </button>
  <button class="tab-btn" data-tab="companies">
    Company Settlements (Admin ← Company)
  </button>
  <button class="tab-btn" data-tab="delegates">
    Delegate Settlements (Company ← Delegate)
  </button>
</div>
```

#### ب) Dynamic Content Loading
```javascript
// تحميل البيانات ديناميكياً حسب نوع التسوية
function loadSettlementData(settlementType) {
    fetch(`/api/settlements/${settlementType}/`)
        .then(response => response.json())
        .then(data => renderSettlementList(data))
}
```

### 📊 2. جداول البيانات الجديدة

#### Vendor Settlements Table
```
| اسم الموردين | إجمالي المبيعات | الرسوم الإدارية | الصافي المستحق | عدد العمليات | الإجراء |
|---|---|---|---|---|---|
| مطاعم السرايا | 8,400 | 2,100 | 6,300 | 45 | [تصفية] |
```

#### Company Settlements Table
```
| اسم الشركة | الميزانية المخصصة | المستخدم | المتبقي | عدد الفعاليات | الإجراء |
|---|---|---|---|---|---|
| شركة دواء X | 50,000 | 32,000 | 18,000 | 3 | [تصفية] |
```

#### Delegate Settlements Table
```
| اسم المندوب | الشركة | الفعاليات | الأطباء المسجلين | العمولة | الإجراء |
|---|---|---|---|---|---|
| أحمد محمد | شركة X | 5 | 25 | 2,500 | [تصفية] |
```

### 🔄 3. Modals/Forms الجديدة

#### Settlement Confirmation Modal
```html
<form>
  <!-- Settlement Details -->
  <input type="hidden" name="settlement_type" />
  <input type="hidden" name="settlement_id" />
  
  <!-- Summary calculations -->
  <div class="settlement-summary">
    <!-- حسابات ديناميكية -->
  </div>
  
  <!-- Amount to settle -->
  <input type="number" name="settlement_amount" required />
  
  <!-- Settlement date -->
  <input type="date" name="settlement_date" required />
  
  <!-- Notes -->
  <textarea name="notes"></textarea>
  
  <!-- Payment method -->
  <select name="payment_method">
    <option>Bank Transfer</option>
    <option>Cash</option>
    <option>Check</option>
  </select>
  
  <button type="submit">Confirm Settlement</button>
</form>
```

### 📈 4. Features إضافية
- **Filtering**: حسب التاريخ، الحالة، النطاق السعري
- **Search**: البحث بالاسم أو الرقم
- **Pagination**: تقسيم النتائج
- **Export**: تصدير CSV/Excel
- **Print**: طباعة الإيصالات والتقارير
- **History**: سجل التسويات السابقة

---

## قائمة Tasks المراد تنفيذها

### ✅ المرحلة 1: تحسين Backend الأساسي

#### Task 1.1: إنشاء Models جديدة
- [ ] إنشاء `CompanySettlement` Model
- [ ] إنشاء `DelegateSettlement` Model
- [ ] تحسين `VendorSettlement` بإضافة حقول جديدة
- [ ] إنشاء Migrations

#### Task 1.2: إضافة Business Logic
- [ ] إضافة methods للحسابات في كل Model
- [ ] إضافة validation للبيانات
- [ ] إضافة Admin Actions للتسويات

#### Task 1.3: إنشاء API Endpoints
- [ ] REST API لجلب Vendor Settlements
- [ ] REST API لجلب Company Settlements
- [ ] REST API لجلب Delegate Settlements
- [ ] API لإنشاء عملية تسوية جديدة
- [ ] API لتحديث حالة التسوية

### ✅ المرحلة 2: تطوير Frontend الديناميكي

#### Task 2.1: إعادة هيكلة الصفحة
- [ ] إضافة Tabs للتنقل بين أنواع التسويات
- [ ] تحويل البيانات من Hardcoded إلى Dynamic
- [ ] إضافة Loading States و Error Handling

#### Task 2.2: إنشاء جداول ديناميكية
- [ ] Vendor Settlements Table
- [ ] Company Settlements Table
- [ ] Delegate Settlements Table

#### Task 2.3: تحسين Modals والـ Forms
- [ ] تحديث Settlement Confirmation Modal
- [ ] إضافة Form Validation
- [ ] تحسين UX/UI

#### Task 2.4: Features إضافية
- [ ] البحث والفلترة
- [ ] الترتيب والـ Pagination
- [ ] الطباعة والتصدير
- [ ] سجل التسويات

### ✅ المرحلة 3: الاختبار والتحقق

#### Task 3.1: Unit Tests
- [ ] اختبار حسابات VendorSettlement
- [ ] اختبار حسابات CompanySettlement
- [ ] اختبار حسابات DelegateSettlement

#### Task 3.2: Integration Tests
- [ ] اختبار API Endpoints
- [ ] اختبار الـ Frontend Integration

#### Task 3.3: User Testing
- [ ] اختبار سهولة الاستخدام
- [ ] اختبار الأداء
- [ ] اختبار الوصول (Accessibility)

---

## 📊 الأولويات الموصى بها

### 🔴 عالية جداً (Critical)
1. إنشاء Models الجديدة
2. حساب الأرقام بشكل صحيح من قاعدة البيانات
3. API Endpoints للبيانات

### 🟠 عالية
1. تحديث الـ Frontend لجلب البيانات الفعلية
2. إضافة Tabs لأنماط التسوية الثلاثة
3. تحسين Modal الخاص بالتصفية

### 🟡 متوسطة
1. Features البحث والفلترة
2. التصدير والطباعة
3. سجل التسويات

### 🟢 منخفضة
1. الرسوم البيانية والإحصائيات المتقدمة
2. الإشعارات التلقائية
3. التنبؤ بالتسويات المستقبلية

---

## 📎 ملاحظات إضافية

### نقاط مهمة:
1. **الدقة المالية**: جميع الحسابات يجب أن تكون دقيقة لـ 2 عشر عشري
2. **التدقيق**: يجب الاحتفاظ بسجل شامل لكل تسوية
3. **الأمان**: فقط الـ Admin يمكنه تنفيذ التسويات
4. **الإشعارات**: إرسال إشعارات للأطراف المعنية
5. **التقارير**: توليد تقارير شاملة قابلة للطباعة

---

**تاريخ الإنشاء**: 30 مايو 2026
**الحالة**: تحت المراجعة
**الأولوية**: عالية جداً
