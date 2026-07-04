# 🔐 نموذج العلاقات والحسابات المالية - نظام التسويات

---

## 📊 1. مخطط العلاقات بين الكيانات

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ADMIN (System Admin)                         │
│                    يدير جميع التسويات الثلاثة                       │
└────────────┬──────────────────────┬──────────────────────┬──────────┘
             │                      │                      │
             │ (1)                  │ (2)                  │ (3)
             ▼                      ▼                      ▼
    ┌────────────────┐   ┌──────────────────┐   ┌──────────────────┐
    │    VENDOR      │   │ PHARMACEUTICAL   │   │    DELEGATE      │
    │ (المورد/التاجر) │   │    COMPANY       │   │    (المندوب)     │
    │                │   │   (الشركة)       │   │                  │
    └────────┬───────┘   └────────┬─────────┘   └─────────┬────────┘
             │                    │                       │
             │ Receives           │ Receives              │ Receives
             │ Payment            │ Refund                │ Commission
             │                    │                       │
    ┌────────▼──────────────┬─────▼────────────────┬──────▼──────────┐
    │ VendorSettlement      │ CompanySettlement    │ DelegateSettlement
    │ (تسوية المورد)       │ (تسوية الشركة)      │ (تسوية المندوب)
    └───────────────────────┴──────────────────────┴──────────────────┘
```

---

## 💰 2. دورة الأموال والعمليات

### **نمط 1: تسوية الموردين (Vendor Settlement)**

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCTOR (الطبيب)                              │
│                                                                  │
│  ┌───────────────────────────────────────────┐                 │
│  │ Vouchers (قسائم)                         │                 │
│  │ - Voucher 1: 1000 ج.م                    │                 │
│  │ - Voucher 2: 1000 ج.م                    │                 │
│  │ - Voucher 3: 1000 ج.م                    │                 │
│  │ Total Balance: 3000 ج.م                  │                 │
│  └───────────────────────────────────────────┘                 │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
                                  │ (يشتري من)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     VENDOR (الموردين)                          │
│                     (مطاعم، صيدليات، إلخ)                       │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
                                  │ (يسجل عملية شراء)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TRANSACTION (عملية)                          │
│                                                                  │
│  amount_spent = 500 ج.م                                        │
│  management_fee_percentage = 25%                               │
│  management_fee_amount = 500 × 0.25 = 125 ج.م                │
│  total_deducted = 500 + 125 = 625 ج.م                        │
│                                                                  │
│  [تخصم من الـ Vouchers]                                        │
│  Voucher 1: 1000 - 625 = 375 ج.م                             │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
                                  │ (تراكم العمليات)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│         VENDOR SETTLEMENT (تسوية المورد)                       │
│                                                                  │
│  المورد: مطاعم السرايا                                         │
│  إجمالي عمليات: 45 عملية                                        │
│  إجمالي المبيعات (amount_spent): 8,400 ج.م                    │
│  إجمالي الرسوم الإدارية: 2,100 ج.م (25%)                      │
│  الصافي المستحق للمورد: 6,300 ج.م                            │
│                                                                  │
│  ✅ تسوية بقيمة 6,300 ج.م → المورد                           │
│  ✅ عمولة 2,100 ج.م → تبقى مع النظام (Admin)                │
└─────────────────────────────────────────────────────────────────┘
```

**الصيغة الرياضية**:
```
Transactions filtered by vendor AND status != settled

For each transaction:
  - amount_spent = المبلغ المنفق فعلاً
  - fee = amount_spent × 0.25
  - total_deducted = amount_spent + fee
  
VendorSettlement:
  - settlement_amount = Σ(amount_spent) of all unsettled transactions
  - admin_commission_amount = Σ(management_fee_amount)
  - net_amount_to_vendor = settlement_amount
```

---

### **نمط 2: تسوية الشركات (Company Settlement)**

```
┌─────────────────────────────────────────────────────────────────┐
│            PHARMACEUTICAL COMPANY (الشركة الدوائية)             │
│                    (منظمة الفعالية)                             │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
                                  │ (تمول فعالية)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EVENT (فعالية)                             │
│                                                                  │
│  name: "معرض صحي - مايو 2024"                                 │
│  max_budget: 50,000 ج.م (الميزانية المخصصة)                   │
│  voucher_value: 1,000 ج.م                                      │
│  doctors_count: 50 طبيب                                        │
│  total_vouchers_distributed: 50,000 ج.م                       │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    ▼                            ▼
        ┌──────────────────┐        ┌──────────────────┐
        │ Unused Budget    │        │ Used Budget      │
        │ (غير مستخدم)    │        │ (مستخدم)        │
        │                  │        │                  │
        │ 50,000 - 45,000  │        │ 45,000 ج.م       │
        │ = 5,000 ج.م     │        │ (spent by doctors│
        │                  │        │ in transactions) │
        └──────────────────┘        └──────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│        COMPANY SETTLEMENT (تسوية الشركة)                       │
│                                                                  │
│  Company: شركة دواء أمينة                                      │
│  Event: معرض صحي - مايو 2024                                   │
│  total_budget_allocated: 50,000 ج.م                            │
│  total_vouchers_distributed: 45,000 ج.م                       │
│  (spent by doctors): 42,000 ج.م                               │
│  unused_budget: 5,000 ج.م                                      │
│                                                                  │
│  Settlement Logic:                                             │
│  - Company should refund: unused_budget = 5,000 ج.م           │
│  - OR keep as credit for next event                           │
│  - Settlement_amount = الاتفاق بين Admin والشركة            │
└─────────────────────────────────────────────────────────────────┘
```

**الصيغة الرياضية**:
```
Company Budget Analysis:
  - total_allocated = Σ(max_budget) per event
  - total_distributed = Σ(voucher.initial_value) issued
  - total_spent = Σ(amount_spent) from transactions using vouchers
  - unused = total_allocated - total_distributed
  
CompanySettlement:
  - settlement_amount = unused_budget (ما ستسترجعه الشركة)
  - settlement_status = negotiable (يمكن التفاوض)
```

---

### **نمط 3: تسوية المناديب (Delegate Settlement)**

```
┌─────────────────────────────────────────────────────────────────┐
│          PHARMACEUTICAL COMPANY (الشركة الدوائية)              │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
                                  │ (توكل فعاليات للمندوب)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DELEGATE (المندوب)                            │
│                                                                  │
│  name: أحمد محمد علي                                           │
│  company: شركة دواء أمينة                                      │
│  assigned_events:                                              │
│    - معرض صحي (50 طبيب)                                       │
│    - جلسة توعية (30 طبيب)                                      │
│    - ندوة طبية (25 طبيب)                                       │
│  total_doctors_registered: 105 طبيب                            │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
                                  │ (يتلقى عمولة بناءً على الأداء)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│       DELEGATE SETTLEMENT (تسوية المندوب)                      │
│                                                                  │
│  Delegate: أحمد محمد علي                                       │
│  Company: شركة دواء أمينة                                      │
│  events_assigned: 3 فعاليات                                    │
│  doctors_registered: 105 طبيب                                  │
│  commission_rate: 5% (عمولة 5% لكل طبيب)                      │
│                                                                  │
│  Calculation:                                                  │
│  - Per Doctor Commission: 1,000 ج.م × 5% = 50 ج.م           │
│  - Total Commission: 105 × 50 = 5,250 ج.م                    │
│                                                                  │
│  Settlement:                                                   │
│  ✅ صرف 5,250 ج.م → المندوب                                 │
│  ✅ خصم من ميزانية الشركة                                    │
└─────────────────────────────────────────────────────────────────┘
```

**الصيغة الرياضية**:
```
Delegate Performance:
  - events_assigned = Σ(events delegated to delegate)
  - doctors_registered = Σ(doctors registered in those events)
  - commission_rate = negotiated % per event/doctor
  
DelegateSettlement:
  - total_commission = doctors_registered × commission_rate
  - settlement_amount = total_commission
  - settlement_status = automatic OR negotiable
```

---

## 🧮 3. جداول الحسابات بالأرقام الفعلية

### مثال عملي شامل:

#### **السيناريو**:
```
Month: May 2024
Vendor: مطاعم السرايا
Company: شركة أمينة للأدوية
Delegate: أحمد محمد
```

#### **البيانات الأساسية**:

| العنصر | القيمة |
|--------|--------|
| Transactions Count | 45 |
| Doctors Involved | 25 |
| Average Transaction | 186.67 ج.م |
| Period | May 1 - May 31 |

#### **التفصيل بالعمليات**:

```
═══════════════════════════════════════════════════════════════

TRANSACTION BREAKDOWN (العمليات التفصيلية)

Transaction #1:  500 ج.م × 25% = 625 ج.م total
Transaction #2:  400 ج.م × 25% = 500 ج.م total
Transaction #3:  250 ج.م × 25% = 312.5 ج.م total
...
Transaction #45: 300 ج.م × 25% = 375 ج.م total

═══════════════════════════════════════════════════════════════

VENDOR SETTLEMENT CALCULATION

Total amount_spent:         8,400.00 ج.م
Total management_fees:      2,100.00 ج.م (25%)
───────────────────────────────────────
Net to Vendor:              6,300.00 ج.م

═══════════════════════════════════════════════════════════════

COMPANY SETTLEMENT CALCULATION

Budget Allocated for Event: 50,000.00 ج.م
Vouchers Distributed:       42,000.00 ج.م (35 doctors × 1200 avg)
Actually Spent:             35,000.00 ج.م
───────────────────────────────────────
Unused Budget (Refund):      7,000.00 ج.م

═══════════════════════════════════════════════════════════════

DELEGATE SETTLEMENT CALCULATION

Events Assigned:             3
Doctors Registered:         105 (35 + 40 + 30)
Commission Rate:            5% per doctor
Per Doctor Amount:          1,000 ج.م (avg)
───────────────────────────────────────
Total Commission:           5,250.00 ج.م (105 × 50)

═══════════════════════════════════════════════════════════════
```

---

## 📐 4. الصيغ والمعادلات الرياضية

### **Vendor Settlement**:
```
Pending Transactions = Transactions WHERE status != 'SETTLED'

Available Balance = Σ(Transaction.amount_spent) - Σ(Previous Settlements)

Admin Commission = Σ(Transaction.management_fee_amount)
                = Σ(Transaction.amount_spent × 0.25)

Net to Vendor = Σ(Transaction.amount_spent)

VendorSettlement.settlement_amount = Net to Vendor
```

### **Company Settlement**:
```
Event Budget Utilization = (Vouchers Distributed / Max Budget) × 100

Unused Budget = Max Budget - Vouchers Distributed

Actual Spending = Σ(Transaction.total_deducted) from this event

CompanySettlement.settlement_amount = Unused Budget or
                                      Negotiated Amount
```

### **Delegate Settlement**:
```
Doctor Count = COUNT(doctors in assigned events)

Base Commission = Doctor Count × Commission Rate

Performance Bonus = if (Doctor Count > Target) 
                     then (Extra × Bonus Rate)
                     else 0

Total Commission = Base Commission + Performance Bonus

DelegateSettlement.settlement_amount = Total Commission
```

---

## 🔗 5. العلاقات بين الجداول

```
VendorSettlement:
├── vendor (FK → Vendor)
├── transactions (M2M → Transaction)
├── amount_settled
├── admin_commission_amount
├── net_amount_to_vendor
└── settlement_status

CompanySettlement:
├── company (FK → PharmaceuticalCompany)
├── events (implicit via vouchers)
├── total_budget_allocated
├── total_vouchers_distributed
├── settlement_amount
└── settlement_status

DelegateSettlement:
├── delegate (FK → Delegate)
├── company (FK → PharmaceuticalCompany)
├── events_assigned (count)
├── doctors_registered (count)
├── commission_rate
├── total_commission
└── settlement_status
```

---

## 📅 6. جدول المقارنة الشامل

| المقياس | Vendor Settlement | Company Settlement | Delegate Settlement |
|--------|-------------------|-------------------|---------------------|
| **المتلقي** | Vendor (مورد) | Pharmaceutical Company | Delegate (مندوب) |
| **المصدر** | Transactions | Events Budget | Performance |
| **الحساب** | Sum of spent | Budget unused | Commission × Doctors |
| **الرسوم** | 25% للإدارة | بدون رسوم | حسب الاتفاق |
| **التكرار** | شهري/أسبوعي | شهري | شهري |
| **التعقيد** | متوسط | عالي | متوسط |
| **الأولوية** | 🔴 عالية جداً | 🔴 عالية جداً | 🟠 عالية |

---

**الرسم التخطيطي منقح**: 30 مايو 2026
