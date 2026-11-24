from django.conf import settings
from .services import email_verified, can_act, display_name
from .models import Notification

def community(request):
    user=request.user
    return {'google_enabled':bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),'verified_email':email_verified(user) if user.is_authenticated else False,'needs_verification':user.is_authenticated and not can_act(user),'display_name':display_name(user) if user.is_authenticated else '','unread_notifications':Notification.objects.filter(user=user,read=False).count() if user.is_authenticated else 0}
