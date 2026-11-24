from django.contrib import admin
from .models import Organization, Event, Attendance, Location, Notification, Account, LoginAttempt, Reminder, Message
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display=('name','owner','city','verified','public'); list_filter=('verified','public'); search_fields=('name','city','owner__username'); actions=['verify','unverify']
    @admin.action(description='Mark selected organizations verified after evidence review')
    def verify(self,request,queryset): queryset.update(verified=True)
    @admin.action(description='Revoke verification')
    def unverify(self,request,queryset): queryset.update(verified=False)
for model in (Event,Attendance,Location,Notification,Account,LoginAttempt,Reminder): admin.site.register(model)
# Private messages are deliberately not exposed in the standard admin interface.
