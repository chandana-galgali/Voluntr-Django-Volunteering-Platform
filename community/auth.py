import hashlib, secrets, urllib.parse, urllib.request, json, base64
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.contrib.auth.views import LoginView
from django.db import transaction, IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.core import signing
from .models import Account, LoginAttempt
from .services import verification
import re

RESULT_MESSAGES={
 'sent':(messages.SUCCESS,'Verification email sent. Check your inbox (and spam folder) for a link from Voluntr.'),
 'throttled':(messages.INFO,'A verification email was sent less than a minute ago. Please wait a moment before requesting another.'),
 'no_email':(messages.WARNING,'Add an email address first using "Set or change email".'),
 'not_configured':(messages.ERROR,'Email delivery is not configured on this server yet. Please contact the site administrator.'),
 'failed':(messages.ERROR,'We could not send the verification email right now. Please try again in a few minutes.'),
}

def report(request,result):
    level,text=RESULT_MESSAGES.get(result,RESULT_MESSAGES['failed']); messages.add_message(request,level,text)

def unique_username(base):
    from django.contrib.auth import get_user_model
    User=get_user_model()
    base=re.sub(r'[^\w.@+-]','',base or '')[:140] or 'volunteer'
    candidate=base; n=1
    while User.objects.filter(username__iexact=candidate).exists():
        n+=1; candidate=f'{base}{n}'
    return candidate

class LimitedLogin(LoginView):
    template_name='login.html'
    def post(self, request, *args, **kwargs):
        # Shared database counter keyed by normalized username; no forwarded-IP trust.
        username=request.POST.get('username','').strip().casefold()
        key=salted_hmac('voluntr-login', username).hexdigest()
        with transaction.atomic():
            row,_=LoginAttempt.objects.select_for_update().get_or_create(key=key)
            now=timezone.now()
            if row.until<=now: row.count=0; row.until=now+timedelta(minutes=15)
            if row.count>=5:
                return render(request,self.template_name,{'form':self.get_form(),'rate_limited':True},status=429)
            row.count+=1; row.save(update_fields=['count','until'])
        result=super().post(request,*args,**kwargs)
        if request.user.is_authenticated: LoginAttempt.objects.filter(key=key).delete()
        return result

@login_required
@require_POST
def resend(request):
    report(request,verification(request,request.user))
    return redirect(request.POST.get('next') if request.POST.get('next','').startswith('/') and not request.POST.get('next','').startswith('//') else 'dashboard')

@require_GET
def verify(request,token):
    try:
        data=signing.loads(token,salt='voluntr-email-v1',max_age=86400)
        user=get_user_model().objects.get(pk=data['uid'],email=data['email'],is_active=True)
        account,_=Account.objects.get_or_create(user=user)
        account.verified_email=user.email; account.save(update_fields=['verified_email'])
        messages.success(request,'Email verified. You can now apply, post opportunities and send messages.')
    except (signing.BadSignature, get_user_model().DoesNotExist, KeyError, TypeError): messages.error(request,'Invalid or expired verification link. Request a new one from your dashboard.')
    return redirect('dashboard' if request.user.is_authenticated else 'login')

def google_start(request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET: return redirect('login')
    state,nonce,verifier=[secrets.token_urlsafe(32) for _ in range(3)]
    request.session['google_oauth']={'state':state,'nonce':nonce,'verifier':verifier,'at':timezone.now().timestamp()}
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    callback=settings.GOOGLE_REDIRECT_URI or request.build_absolute_uri(reverse('google_callback'))
    params=dict(client_id=settings.GOOGLE_CLIENT_ID,redirect_uri=callback,response_type='code',scope='openid email profile',state=state,nonce=nonce,code_challenge=challenge,code_challenge_method='S256',prompt='select_account')
    return redirect('https://accounts.google.com/o/oauth2/v2/auth?'+urllib.parse.urlencode(params))

@require_GET
def google_callback(request):
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    session=request.session.pop('google_oauth',{})
    try:
        if not session or not secrets.compare_digest(request.GET.get('state',''),session['state']) or timezone.now().timestamp()-session['at']>600: raise ValueError('Invalid state')
        callback=settings.GOOGLE_REDIRECT_URI or request.build_absolute_uri(reverse('google_callback'))
        payload=urllib.parse.urlencode(dict(code=request.GET['code'],client_id=settings.GOOGLE_CLIENT_ID,client_secret=settings.GOOGLE_CLIENT_SECRET,redirect_uri=callback,grant_type='authorization_code',code_verifier=session['verifier'])).encode()
        with urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',data=payload),timeout=12) as response: tokens=json.load(response)
        claims=id_token.verify_oauth2_token(tokens['id_token'],google_requests.Request(),settings.GOOGLE_CLIENT_ID)
        if claims.get('nonce')!=session['nonce'] or claims.get('email_verified') is not True: raise ValueError('Invalid claims')
        email=claims['email'].lower(); sub=claims['sub']; User=get_user_model()
        with transaction.atomic():
            account=Account.objects.select_for_update().filter(google_subject=sub).select_related('user').first()
            given=(claims.get('given_name') or '')[:150]; family=(claims.get('family_name') or '')[:150]
            if not given and not family and claims.get('name'):
                given,_,family=claims['name'].partition(' '); given=given[:150]; family=family[:150]
            if account:
                user=account.user
                # Repair accounts created before names were stored (displayed as google_xxxx).
                changed=[]
                if not user.first_name and given: user.first_name=given; changed.append('first_name')
                if not user.last_name and family: user.last_name=family; changed.append('last_name')
                if changed: user.save(update_fields=changed)
            else:
                # Do not silently link an existing password account by email.
                if User.objects.filter(email__iexact=email).exists(): raise ValueError('Existing account: use password sign-in')
                user=User.objects.create_user(username=unique_username(email.split('@')[0]),email=email,first_name=given,last_name=family)
                user.set_unusable_password(); user.save(update_fields=['password'])
                Account.objects.create(user=user,verified_email=email,google_subject=sub)
                from core.models import Profile
                Profile.objects.get_or_create(user=user)
            if not user.is_active: raise ValueError('Inactive account')
        login(request,user,backend='django.contrib.auth.backends.ModelBackend'); return redirect('dashboard')
    except Exception as exc:
        import logging; logging.getLogger(__name__).warning('Google sign-in failed: %s', exc)
        if request.GET.get('error'): messages.info(request,'Google sign-in was cancelled.')
        elif 'Existing account' in str(exc): messages.error(request,'An account with this email already exists. Sign in with your username and password instead.')
        else: messages.error(request,'Google sign-in could not be completed. Please try again.')
        return redirect('login')

@login_required
def change_email(request):
    from django import forms
    class EmailForm(forms.Form):
        email=forms.EmailField()
        password=forms.CharField(widget=forms.PasswordInput)
    f=EmailForm(request.POST if request.method=='POST' else None,initial={'email':request.user.email})
    if not request.user.has_usable_password():
        # Google-only accounts have no password to confirm with.
        del f.fields['password']
    if request.method=='POST' and f.is_valid():
        email=f.cleaned_data['email'].lower()
        if 'password' in f.fields and not request.user.check_password(f.cleaned_data['password']): f.add_error('password','Incorrect password.')
        elif get_user_model().objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists(): f.add_error('email','Email already registered.')
        else:
            with transaction.atomic():
                request.user.email=email; request.user.save(update_fields=['email'])
                account,_=Account.objects.get_or_create(user=request.user)
                account.verified_email=''; account.last_verification=None; account.save(update_fields=['verified_email','last_verification'])
            messages.success(request,'Email updated. Please verify the new address.'); report(request,verification(request,request.user)); return redirect('dashboard')
    return render(request,'form.html',{'form':f,'title':'Set or change email','action':'Save and verify email'})
