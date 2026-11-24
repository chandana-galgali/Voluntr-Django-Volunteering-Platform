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
    return bool(user.is_authenticated and user.email and Account.objects.filter(user=user, verified_email__iexact=user.email).exists())

def can_act(user):
    """Whether the user may apply, publish, message or check in."""
    return bool(user.is_authenticated and (user.is_staff or not getattr(settings, 'REQUIRE_EMAIL_VERIFICATION', True) or email_verified(user)))

def display_name(user):
    if not user: return ''
    return user.get_full_name().strip() or user.username

def absolute_url(request, path):
    base = getattr(settings, 'PUBLIC_BASE_URL', '').rstrip('/')
    return base + path if base else request.build_absolute_uri(path)

def send_email(user, subject, text):
    if not user.email: return False
    try:
        return bool(send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False))
    except Exception:
        log.exception('Voluntr email delivery failed')
        return False

def verification(request, user):
    """Send a verification link. Returns 'sent', 'throttled', 'no_email', 'not_configured' or 'failed'."""
    if not user.email: return 'no_email'
    if not getattr(settings, 'EMAIL_CONFIGURED', True): return 'not_configured'
    account, _ = Account.objects.get_or_create(user=user)
    if account.last_verification and (timezone.now()-account.last_verification).total_seconds()<60: return 'throttled'
    token=signing.dumps({'uid':user.pk,'email':user.email}, salt='voluntr-email-v1')
    link=absolute_url(request, reverse('verify_email', args=[token]))
    name=display_name(user)
    text=(f'Hi {name},\n\nWelcome to Voluntr! Please confirm your email address by opening the link below '
          f'(valid for 24 hours):\n\n{link}\n\nIf you did not create a Voluntr account, you can ignore this email.\n\n— The Voluntr team')
    if send_email(user,'Verify your Voluntr email',text):
        account.last_verification=timezone.now(); account.save(update_fields=['last_verification'])
        return 'sent'
    return 'failed'

def notify(user, text, link='', email=False):
    if not user or not user.is_active: return
    Notification.objects.create(user=user,text=text[:250],link=link)
    if email and email_verified(user):
        base=getattr(settings,'PUBLIC_BASE_URL','').rstrip('/')
        body=f'Hi {display_name(user)},\n\n{text}\n\n'+(base+link if base else 'Open Voluntr to view details.')+'\n\n— The Voluntr team'
        transaction.on_commit(lambda:send_email(user,'Voluntr update: '+text[:80],body))

def application_changed(a):
    label={'accepted':'accepted','declined':'not accepted this time','withdrawn':'withdrawn'}.get(a.status,a.status)
    notify(a.volunteer, f'Your application for {a.opportunity.title} was {label}.', reverse('dashboard'), email=True)

def application_received(a):
    notify(a.opportunity.owner, f'New application from {display_name(a.volunteer)} for {a.opportunity.title}.', reverse('dashboard'), email=True)
