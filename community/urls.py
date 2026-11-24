from django.urls import path
from . import views as v, auth
urlpatterns=[
 path('verify/<str:token>/',auth.verify,name='verify_email'),path('resend/',auth.resend,name='resend_verification'),path('email/',auth.change_email,name='change_email'),
 path('google/',auth.google_start,name='google_start'),path('google/callback/',auth.google_callback,name='google_callback'),
 path('organizations/',v.organizations,name='organizations'),path('organizations/edit/',v.edit_organization,name='edit_organization'),path('organizations/<slug:slug>/',v.organization,name='organization'),
 path('location/<slug:slug>/',v.location,name='edit_location'),path('map/',v.map_page,name='opportunity_map'),path('impact/',v.impact,name='impact'),
 path('notifications/',v.notifications,name='notifications'),path('notifications/read/',v.mark_read,name='mark_read'),path('notifications/<int:pk>/open/',v.open_notification,name='open_notification'),
 path('calendar/',v.calendar,name='calendar'),path('events/create/<slug:slug>/',v.edit_event,name='create_event'),path('events/<int:pk>/',v.event_detail,name='event_detail'),path('events/<int:pk>/edit/<slug:slug>/',v.edit_event,name='edit_event'),path('events/<int:pk>/cancel/',v.cancel_event,name='cancel_event'),path('events/<int:pk>/qr/',v.qr,name='event_qr'),path('events/<int:pk>/checkin/<uuid:key>/',v.checkin,name='checkin'),
 path('inbox/',v.inbox,name='inbox'),path('inbox/<int:pk>/',v.conversation,name='conversation'),]
