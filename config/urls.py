from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from community.auth import LimitedLogin
from community import views as cv
from community.sitemaps import StaticMap, OpportunityMap, JournalMap, OrgMap
from django.contrib.auth import views as auth
from django.views.generic import TemplateView
from core import views as v
urlpatterns=[path('admin/',admin.site.urls),path('',v.home,name='home'),path('opportunities/',v.explore,name='explore'),path('opportunities/<slug:slug>/',v.detail,name='detail'),path('opportunities/<slug:slug>/apply/',v.apply,name='apply'),path('opportunities/<slug:slug>/save/',v.bookmark,name='bookmark'),path('join/',v.signup,name='signup'),path('login/',LimitedLogin.as_view(),name='login'),path('logout/',auth.LogoutView.as_view(),name='logout'),path('dashboard/',v.dashboard,name='dashboard'),path('profile/',v.edit_profile,name='profile'),path('organize/',v.publish,name='publish'),path('applications/<int:pk>/review/',v.review,name='review'),path('applications/<int:pk>/withdraw/',v.withdraw,name='withdraw'),path('applications/<int:pk>/hours/',v.log_hours,name='log_hours'),path('hours/<int:pk>/approve/',v.approve_hours,name='approve_hours'),path('journal/',v.blog,name='blog'),path('journal/<slug:slug>/',v.article,name='article'),path('about/',v.about,name='about'),path('contact/',v.contact,name='contact'),path('api/opportunities/',v.api,name='api'),path('subscribe/',v.subscribe,name='subscribe'),path('health/',v.health),path('privacy/',TemplateView.as_view(template_name='privacy.html'),name='privacy')]

urlpatterns += [
 path('opportunities/<slug:slug>/report/',v.report_listing,name='report_listing'),
 path('applications/<int:pk>/certificate/',v.certificate,name='certificate'),
 path('organizer/export/',v.export_applications,name='export_applications'),
 path('activity/',v.activity,name='activity'),
 path('password-reset/',auth.PasswordResetView.as_view(template_name='password_reset.html',email_template_name='password_reset_email.txt'),name='password_reset'),
 path('password-reset/done/',auth.PasswordResetDoneView.as_view(template_name='password_reset_done.html'),name='password_reset_done'),
 path('reset/<uidb64>/<token>/',auth.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'),name='password_reset_confirm'),
 path('reset/done/',auth.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'),name='password_reset_complete'),
]

urlpatterns += [path('community/',include('community.urls')),path('sitemap.xml',sitemap,{'sitemaps':{'pages':StaticMap,'opportunities':OpportunityMap,'journal':JournalMap,'organizations':OrgMap}},name='sitemap'),path('robots.txt',cv.robots),path('manifest.webmanifest',cv.manifest),path('service-worker.js',cv.worker),path('offline/',TemplateView.as_view(template_name='community/offline.html'))]
