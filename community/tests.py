from datetime import timedelta
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core import signing
from django.core.management import call_command
from core.models import Opportunity, Application, Profile, Hours
from .models import Account, Attendance, Event, Notification, Organization, Message

class AdvancedTests(TestCase):
    def setUp(self):
        self.vol=User.objects.create_user('vol',email='v@example.test',password='Long-example-password-1')
        self.org=User.objects.create_user('org',email='o@example.test',password='Long-example-password-1')
        self.other=User.objects.create_user('other',password='Long-example-password-1')
        for u in (self.vol,self.org): Account.objects.create(user=u,verified_email=u.email)
        Profile.objects.create(user=self.vol); Profile.objects.create(user=self.org,role='organizer')
        self.o=Opportunity.objects.create(title='Garden',slug='garden',organization='Org',category='Environment',city='Mumbai',summary='Garden',description='Garden',commitment='2h',owner=self.org,published=True)
        self.a=Application.objects.create(volunteer=self.vol,opportunity=self.o,motivation='Test application',status='accepted')
        self.e=Event.objects.create(opportunity=self.o,title='Garden day',starts=timezone.now()-timedelta(minutes=5),ends=timezone.now()+timedelta(hours=1))
    def test_public(self):
        for name in ('organizations','opportunity_map','sitemap'):
            self.assertEqual(self.client.get(reverse(name)).status_code,200)
        self.assertEqual(self.client.get('/manifest.webmanifest').status_code,200)
    def test_private(self):
        self.client.force_login(self.other)
        for name,args in [('conversation',[self.a.pk]),('event_detail',[self.e.pk]),('event_qr',[self.e.pk])]:
            self.assertIn(self.client.get(reverse(name,args=args)).status_code,(403,404))
    def test_attendance(self):
        self.client.force_login(self.vol)
        url=reverse('checkin',args=[self.e.pk,self.e.checkin_key])
        self.client.get(url); self.assertEqual(Attendance.objects.count(),0)
        self.client.post(url); self.client.post(url); self.assertEqual(Attendance.objects.count(),1)
    def test_messages(self):
        self.client.force_login(self.vol)
        self.client.post(reverse('conversation',args=[self.a.pk]),{'body':'Hello organizer'})
        self.assertEqual(Message.objects.count(),1)
        self.assertTrue(Notification.objects.filter(user=self.org).exists())
    def test_verify(self):
        Account.objects.filter(user=self.vol).update(verified_email='')
        token=signing.dumps({'uid':self.vol.pk,'email':self.vol.email},salt='voluntr-email-v1')
        self.client.get(reverse('verify_email',args=[token]))
        self.assertEqual(Account.objects.get(user=self.vol).verified_email,self.vol.email)
    def test_rate_limit(self):
        for _ in range(5): self.client.post(reverse('login'),{'username':'vol','password':'wrong'})
        self.assertEqual(self.client.post(reverse('login'),{'username':'vol','password':'wrong'}).status_code,429)
    def test_reminders_idempotent(self):
        self.e.starts=timezone.now()+timedelta(hours=1); self.e.ends=self.e.starts+timedelta(hours=1); self.e.save()
        call_command('send_event_reminders'); call_command('send_event_reminders')
        self.assertEqual(Notification.objects.filter(user=self.vol).count(),1)
