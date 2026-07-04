import os
import glob

# Define the replacements
replacements = {
    "API Endpoints": "Django Views و POST Handlers",
    "`core/api_views.py`": "`core/views.py`",
    "3 APIs للـ REST": "Django Views مسؤولة عن الـ GET/POST",
    "تحميل البيانات ديناميكياً": "تمرير البيانات عبر Context ومعالجتها بالـ POST",
    "JS Module جديد": "معالجة داخل Django View",
    "Fetch من API": "استخدام Form Submit وإعادة التحميل",
    "REST API": "Django Views (TemplateView/post)",
    "API لإنشاء عملية تسوية جديدة": "دالة Post لمعالجة عملية تسوية جديدة",
    "API لتحديث حالة التسوية": "دالة Post لتحديث الحالة",
    "اختبار API Endpoints": "اختبار الـ Views",
    "`core/serializers.py`": "`core/forms.py` (أو استخدام الـ request.POST مباشرة)",
    "لتحويل Models إلى JSON": "للتعامل مع مدخلات المستخدم والـ Validation",
    "API Tests": "View Tests",
    "GET Endpoints": "GET Requests في Views",
    "POST Endpoints": "POST Handlers في Views",
    "REST API لجلب": "Django Context لجلب",
    "API endpoints للـ Frontend": "دوال الـ View للـ Frontend",
    "class VendorSettlementsListAPI(APIView):": "class CustomVendorSettlementsView(LoginRequiredMixin, TemplateView):",
    "class CompanySettlementsListAPI(APIView):": "class CustomCompanySettlementsView(LoginRequiredMixin, TemplateView):",
    "class DelegateSettlementsListAPI(APIView):": "class CustomDelegateSettlementsView(LoginRequiredMixin, TemplateView):",
    "class CreateSettlementAPI(APIView):": "def post(self, request, *args, **kwargs):",
    "fetch(`/api/settlements/${settlementType}/`)": "// سيتم الاعتماد على context الديجانجو بدلا من الـ fetch",
    "class VendorSettlementViewSet(viewsets.ModelViewSet):": "class VendorSettlementView(TemplateView):",
    "class CompanySettlementViewSet(viewsets.ModelViewSet):": "class CompanySettlementView(TemplateView):",
    "class DelegateSettlementViewSet(viewsets.ModelViewSet):": "class DelegateSettlementView(TemplateView):",
    "serializer_class": "# لا حاجة للـ serializers",
    "permission_classes = [IsAuthenticated, IsAdminUser]": "",
    "const response = await fetch(`/api/settlements/${type}/`);": "/* يتم جلب البيانات من الـ Context */",
    "const response = await fetch(`/api/settlements/${settlementType}/`, {": "/* يتم إرسال البيانات كـ Form POST عادي */",
    "API ViewSets و Serializers": "Django Views (GET/POST)",
}

folder = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\التسويات"
files = glob.glob(os.path.join(folder, "*.md"))

updated_files = []

for file_path in files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    original_content = content
    
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        updated_files.append(os.path.basename(file_path))

print("Updated files:", updated_files)
