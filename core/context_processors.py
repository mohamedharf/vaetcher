from accounts.models import Vendor
from core.models import Notification

def global_system_settings(request):
    try:
        # Assuming the main system settings are stored in the first ADMIN vendor
        admin_vendor = Vendor.objects.filter(role='ADMIN', is_deleted=False).order_by('id').first()
        
        context = {
            'global_system_vendor': admin_vendor
        }
        
        if request.user.is_authenticated:
            unread_notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
            recent_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
            
            context['unread_notifications_count'] = unread_notifications.count()
            context['recent_notifications'] = recent_notifications
            
        return context
    except Exception:
        return {}
