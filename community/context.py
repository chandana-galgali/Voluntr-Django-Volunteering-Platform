from django.conf import settings
from .services import email_verified
from .models import Notification

def community(request):
    user=request.user
    return {'google_enabled':bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),'verified_email':email_verified(user) if user.is_authenticated else False,'unread_notifications':Notification.objects.filter(user=user,read=False).count() if user.is_authenticated else 0}
