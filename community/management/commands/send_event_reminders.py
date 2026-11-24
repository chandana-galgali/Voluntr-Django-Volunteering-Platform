from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from community.models import Event, Reminder, LoginAttempt
from community.services import notify
class Command(BaseCommand):
    help='Queue once-per-volunteer reminders for events starting within 24 hours.'
    def handle(self,*args,**kwargs):
        now=timezone.now(); count=0
        for event in Event.objects.filter(cancelled=False,starts__gte=now,starts__lte=now+timedelta(hours=24)):
            for app in event.opportunity.applications.filter(status='accepted').select_related('volunteer'):
                with transaction.atomic():
                    _,created=Reminder.objects.get_or_create(event=event,user=app.volunteer)
                    if created:
                        notify(app.volunteer,f'Upcoming event: {event.title} ({timezone.localtime(event.starts):%d %b %H:%M}).',reverse('event_detail',args=[event.pk]),email=True); count+=1
        LoginAttempt.objects.filter(until__lt=now).delete()
        self.stdout.write(f'{count} reminder(s) created.')
