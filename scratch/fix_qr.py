
path = 'core/views.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """class CustomDoctorCardView(DoctorPortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/doctor_card.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctor'] = getattr(self.request.user, 'doctor_profile', None)
        return context"""

new = """class CustomDoctorCardView(DoctorPortalRequiredMixin, TemplateView):
    template_name = 'custom_admin/doctor_card.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = getattr(self.request.user, 'doctor_profile', None)
        context['doctor'] = doctor
        if doctor:
            context['qr_url'] = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={doctor.qr_code}&color=005353"
        return context"""

with open(path, 'w', encoding='utf-8') as f:
    f.write(content.replace(old, new))
