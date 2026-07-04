from django.urls import path
from .views import (
    HomeView, VendorDashboardView, TransactionCreateView, DoctorLookupView,
    DoctorProfileView, CashierCreateView, CashierDeleteView, SendOTPView,
    AdminCompanyDelegatesView, AdminDelegateSpecialtiesView, VoucherTransferView,
    CustomPOSView, CustomManagerDashboardView, CustomDoctorsView,
    CustomDoctorProfileView, CustomVendorSettlementsView, CustomEventsWizardView,
    CustomDoctorPortalView, CustomDoctorVouchersView, CustomDoctorTransactionsView,
    CustomDoctorTransfersView, CustomDoctorSettingsView, CustomDoctorCardView,
    SendTransferOTPView, CustomVendorPortalView, VendorActionView,
    CustomLoginGatewayView, CustomRegisterGatewayView, CustomSystemSettingsView,
    BulkPrintDoctorsView, CustomCompaniesView, CustomCompanyPortalView,
    CustomDelegatePortalView, CustomCompanyProfileView, CustomDelegateProfileView,
    AdminCompanyDelegateHistoryView, CustomVendorsDirectoryView, CustomVendorProfileView,
    mark_notification_as_read, CustomEmailLogsView, CustomEmailActionsView,
    CustomEventRequestCreateView, AdminEventRequestsView, AdminEventRequestDetailView,
    AdminCreateRequestedDoctorView, AdminApproveEventRequestView,
    AdminRejectEventRequestView, PortalDoctorSearchView, CustomCompanySettingsView,
    CustomDelegateSettingsView, CustomNotificationsView, CompanyDelegatesDoctorsView,
    DelegateDoctorsView,
)
from .qr_views import QRCodeScanView
from .api_views import dashboard_stats_api
from accounts.views import DoctorRegistrationView, SpecialtySearchView, RegistrationQRView

urlpatterns = [
    # ── Core / Home ──────────────────────────────────────────────────────────
    path('', HomeView.as_view(), name='home'),
    path('api/dashboard-stats/', dashboard_stats_api, name='dashboard_stats_api'),

    # ── Vendor / POS ─────────────────────────────────────────────────────────
    path('vendor/dashboard/', VendorDashboardView.as_view(), name='vendor_dashboard'),
    path('vendor/transaction/new/', TransactionCreateView.as_view(), name='transaction_create'),
    path('vendor/transaction/send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('vendor/cashier/new/', CashierCreateView.as_view(), name='cashier_create'),
    path('vendor/cashier/<int:pk>/delete/', CashierDeleteView.as_view(), name='cashier_delete'),
    path('voucher/<int:pk>/transfer/', VoucherTransferView.as_view(), name='voucher_transfer'),
    path('send-transfer-otp/', SendTransferOTPView.as_view(), name='send_transfer_otp'),

    # ── Doctor public / portal ────────────────────────────────────────────────
    path('doctor/<int:pk>/', DoctorProfileView.as_view(), name='doctor_profile'),
    path('api/doctor-lookup/', DoctorLookupView.as_view(), name='doctor_lookup'),
    path('register/doctor/', DoctorRegistrationView.as_view(), name='doctor_register'),
    path('api/specialties/', SpecialtySearchView.as_view(), name='specialty_search'),
    path('registration-qr/', RegistrationQRView.as_view(), name='registration_qr'),
    path('scan/<str:qr_code>/', QRCodeScanView.as_view(), name='qr_scan'),

    # ── Admin Doctor portal ───────────────────────────────────────────────────
    path('custom-doctor-portal/', CustomDoctorPortalView.as_view(), name='custom_doctor_portal'),
    path('custom-doctor-vouchers/', CustomDoctorVouchersView.as_view(), name='custom_doctor_vouchers'),
    path('custom-doctor-transactions/', CustomDoctorTransactionsView.as_view(), name='custom_doctor_transactions'),
    path('custom-doctor-transfers/', CustomDoctorTransfersView.as_view(), name='custom_doctor_transfers'),
    path('custom-doctor-portal/settings/', CustomDoctorSettingsView.as_view(), name='custom_doctor_settings'),
    path('custom-doctor-portal/card/', CustomDoctorCardView.as_view(), name='custom_doctor_card'),

    # ── Custom Admin ──────────────────────────────────────────────────────────
    path('custom-login/', CustomLoginGatewayView.as_view(), name='custom_login'),
    path('custom-register/', CustomRegisterGatewayView.as_view(), name='custom_register'),
    path('custom-pos/', CustomPOSView.as_view(), name='custom_pos'),
    path('custom-dashboard/', CustomManagerDashboardView.as_view(), name='custom_dashboard'),
    path('custom-settings/', CustomSystemSettingsView.as_view(), name='custom_settings'),
    path('bulk-print-doctors/', BulkPrintDoctorsView.as_view(), name='bulk_print_doctors'),

    # ── Doctors admin ─────────────────────────────────────────────────────────
    path('custom-doctors/', CustomDoctorsView.as_view(), name='custom_doctors'),
    path('custom-doctor/<int:pk>/', CustomDoctorProfileView.as_view(), name='custom_doctor_profile'),

    # ── Companies & Delegates admin ───────────────────────────────────────────
    path('custom-companies/', CustomCompaniesView.as_view(), name='custom_companies'),
    path('custom-company/<int:pk>/', CustomCompanyProfileView.as_view(), name='custom_company_profile'),
    path('custom-delegate/<int:pk>/', CustomDelegateProfileView.as_view(), name='custom_delegate_profile'),
    path('custom-company/<int:company_id>/delegate/<int:delegate_id>/history/',
         AdminCompanyDelegateHistoryView.as_view(), name='admin_company_delegate_history'),
    path('api/admin/company-delegates/', AdminCompanyDelegatesView.as_view(), name='admin_company_delegates'),
    path('api/admin/delegate-specialties/', AdminDelegateSpecialtiesView.as_view(), name='admin_delegate_specialties'),

    # ── Company portal ────────────────────────────────────────────────────────
    path('custom-company-portal/', CustomCompanyPortalView.as_view(), name='custom_company_portal'),
    path('custom-company-portal/settings/', CustomCompanySettingsView.as_view(), name='company_portal_settings'),
    path('custom-company-portal/delegates-doctors/', CompanyDelegatesDoctorsView.as_view(), name='company_delegates_doctors'),

    # ── Delegate portal ───────────────────────────────────────────────────────
    path('custom-delegate-portal/', CustomDelegatePortalView.as_view(), name='custom_delegate_portal'),
    path('custom-delegate-portal/settings/', CustomDelegateSettingsView.as_view(), name='delegate_portal_settings'),
    path('custom-delegate-portal/doctors/', DelegateDoctorsView.as_view(), name='delegate_doctors'),

    # ── Vendors admin ─────────────────────────────────────────────────────────
    path('custom-vendors/', CustomVendorsDirectoryView.as_view(), name='custom_vendors_directory'),
    path('custom-vendor/<int:pk>/', CustomVendorProfileView.as_view(), name='custom_vendor_profile'),
    path('custom-vendor-portal/', CustomVendorPortalView.as_view(), name='custom_vendor_portal'),
    path('vendor-action/', VendorActionView.as_view(), name='vendor_action'),

    # ── Settlements admin ─────────────────────────────────────────────────────
    path('custom-settlements/', CustomVendorSettlementsView.as_view(), name='custom_settlements'),

    # ── Events admin ──────────────────────────────────────────────────────────
    path('custom-events/', CustomEventsWizardView.as_view(), name='custom_events'),
    path('custom-event-request/new/', CustomEventRequestCreateView.as_view(), name='custom_event_request_create'),
    path('admin-event-requests/', AdminEventRequestsView.as_view(), name='admin_event_requests_list'),
    path('admin-event-requests/<int:pk>/', AdminEventRequestDetailView.as_view(), name='admin_event_request_detail'),
    path('custom-event-requests/create-doctor/<int:pk>/',
         AdminCreateRequestedDoctorView.as_view(), name='admin_create_requested_doctor'),
    path('admin-event-requests/<int:pk>/approve/',
         AdminApproveEventRequestView.as_view(), name='admin_event_request_approve'),
    path('admin-event-requests/<int:pk>/reject/',
         AdminRejectEventRequestView.as_view(), name='admin_event_request_reject'),

    # ── Notifications ─────────────────────────────────────────────────────────
    path('custom-notifications/', CustomNotificationsView.as_view(), name='custom_notifications'),
    path('notifications/read/<int:pk>/', mark_notification_as_read, name='mark_notification_as_read'),

    # ── Email logs ────────────────────────────────────────────────────────────
    path('email-logs/', CustomEmailLogsView.as_view(), name='custom_email_logs'),
    path('email-actions/', CustomEmailActionsView.as_view(), name='custom_email_actions'),

    # ── Portal Doctor Search API ──────────────────────────────────────────────
    path('api/portal/doctor-search/', PortalDoctorSearchView.as_view(), name='portal_doctor_search'),
]
