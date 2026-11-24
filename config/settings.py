import os
from pathlib import Path
import dj_database_url
BASE_DIR=Path(__file__).resolve().parent.parent
DEBUG=os.getenv('DEBUG','1')=='1'
SECRET_KEY=os.getenv('SECRET_KEY','local-development-only-not-for-production')
if not DEBUG and not os.getenv('SECRET_KEY'): raise RuntimeError('SECRET_KEY required')
ALLOWED_HOSTS=os.getenv('ALLOWED_HOSTS','localhost,127.0.0.1').split(',')
if os.getenv('RENDER_EXTERNAL_HOSTNAME'): ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])
CSRF_TRUSTED_ORIGINS=[x for x in os.getenv('CSRF_TRUSTED_ORIGINS','').split(',') if x]
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    CSRF_TRUSTED_ORIGINS.append('https://' + os.environ['RENDER_EXTERNAL_HOSTNAME'])
INSTALLED_APPS=['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','core']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
DATABASES={'default':dj_database_url.config(default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',conn_max_age=60)}
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.'+n} for n in ['UserAttributeSimilarityValidator','MinimumLengthValidator','CommonPasswordValidator','NumericPasswordValidator']]
LANGUAGE_CODE='en-us'; TIME_ZONE='Asia/Kolkata'; USE_I18N=True; USE_TZ=True
STATIC_URL='/static/'; STATICFILES_DIRS=[BASE_DIR/'static']; STATIC_ROOT=BASE_DIR/'staticfiles'
STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='login'; LOGIN_REDIRECT_URL='dashboard'; LOGOUT_REDIRECT_URL='home'
if not DEBUG:
    SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
    SECURE_SSL_REDIRECT=True; SESSION_COOKIE_SECURE=True; CSRF_COOKIE_SECURE=True
    SECURE_HSTS_SECONDS=3600; SECURE_CONTENT_TYPE_NOSNIFF=True
    SECURE_REDIRECT_EXEMPT=[r"^health/$"]
if DEBUG:
    STORAGES['staticfiles']={'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}

# Email delivery. Preferred in production: BREVO_API_KEY (HTTPS API, works on Render,
# whose free instances block SMTP ports). Fallbacks: SMTP via EMAIL_HOST, then console (DEBUG).
BREVO_API_KEY=os.getenv('BREVO_API_KEY','')
if os.getenv('EMAIL_BACKEND'): EMAIL_BACKEND=os.environ['EMAIL_BACKEND']
elif BREVO_API_KEY: EMAIL_BACKEND='community.email_backend.BrevoEmailBackend'
elif os.getenv('EMAIL_HOST'): EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
else: EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.dummy.EmailBackend'
EMAIL_CONFIGURED=bool(os.getenv('EMAIL_BACKEND') or BREVO_API_KEY or os.getenv('EMAIL_HOST') or DEBUG)
EMAIL_HOST=os.getenv('EMAIL_HOST','')
EMAIL_PORT=int(os.getenv('EMAIL_PORT','587'))
EMAIL_HOST_USER=os.getenv('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD=os.getenv('EMAIL_HOST_PASSWORD','')
EMAIL_USE_TLS=os.getenv('EMAIL_USE_TLS','1')=='1'
DEFAULT_FROM_EMAIL=os.getenv('DEFAULT_FROM_EMAIL','Voluntr <no-reply@example.com>')
SERVER_EMAIL=DEFAULT_FROM_EMAIL
# Set REQUIRE_EMAIL_VERIFICATION=0 to temporarily allow unverified accounts to act (e.g. while email delivery is being set up).
REQUIRE_EMAIL_VERIFICATION=os.getenv('REQUIRE_EMAIL_VERIFICATION','1')=='1'

INSTALLED_APPS += ['django.contrib.sitemaps', 'community']
TEMPLATES[0]['OPTIONS']['context_processors'] += ['community.context.community']
GOOGLE_CLIENT_ID=os.getenv('GOOGLE_CLIENT_ID','')
GOOGLE_CLIENT_SECRET=os.getenv('GOOGLE_CLIENT_SECRET','')
GOOGLE_REDIRECT_URI=os.getenv('GOOGLE_REDIRECT_URI','')
PUBLIC_BASE_URL=os.getenv('PUBLIC_BASE_URL',('https://'+os.environ['RENDER_EXTERNAL_HOSTNAME']) if os.getenv('RENDER_EXTERNAL_HOSTNAME') else '')
EMAIL_TIMEOUT=10

MIDDLEWARE += ['community.middleware.PrivateResponseMiddleware']
# OpenStreetMap tiles require a Referer header; Django's default 'same-origin' policy strips it and the map tiles are blocked.
SECURE_REFERRER_POLICY='strict-origin-when-cross-origin'
LOGGING={'version':1,'disable_existing_loggers':False,'handlers':{'console':{'class':'logging.StreamHandler'}},'root':{'handlers':['console'],'level':'WARNING'}}

