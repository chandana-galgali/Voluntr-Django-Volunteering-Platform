from django.conf import settings
from django.core.mail import send_mail
from django.core import signing
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from .models import Account, Notification
import logging
log = logging.getLogger(__name__)

def email_verified(user):
    return bool(user.email and Account.objects.filter(user=user, verified_email__iexact=user.email).exists())

def send_email(user, subject, text):
    if not user.email: return False
    try:
        return bool(send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False))
    except Exception:
        log.exception('Voluntr email delivery failed')
        return False

def verification(request, user):
    if not user.email: return False
    account, _ = Account.objects.get_or_create(user=user)
    if account.last_verification and (timezone.now()-account.last_verification).total_seconds()<60: return False
    account.last_verification=timezone.now(); account.save(update_fields=['last_verification'])
    token=signing.dumps({'uid':user.pk,'email':user.email}, salt='voluntr-email-v1')
    link=request.build_absolute_uri(reverse('verify_email', args=[token]))
    return send_email(user,'Verify your Voluntr email','Confirm your email within 24 hours:\n'+link)

def notify(user, text, link='', email=False):
    if not user: return
    Notification.objects.create(user=user,text=text[:250],link=link)
    if email and email_verified(user):
        base=getattr(settings,'PUBLIC_BASE_URL','').rstrip('/')
        transaction.on_commit(lambda:send_email(user,'Voluntr update',text+'\n'+(base+link if base else 'Open Voluntr to view details.')))

def application_changed(a):
    notify(a.volunteer, f'Your application for {a.opportunity.title} is {a.status}.', reverse('dashboard'), email=True)

def application_received(a):
    notify(a.opportunity.owner, f'New application for {a.opportunity.title}.', reverse('dashboard'), email=True)
