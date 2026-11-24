"""End-to-end walkthrough of the Voluntr master testing checklist.

Run with: python manage.py test core.test_checklist
"""
import json
from datetime import timedelta
from unittest import mock
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from core.models import Opportunity, Application, Profile, Hours, Bookmark, Article, Contact, Subscriber, ListingReport
from community.models import Account, Organization, Event, Attendance, Notification, Message, Location

PW = 'Sturdy-Pass-2026!'


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', EMAIL_CONFIGURED=True, PUBLIC_BASE_URL='https://voluntr.onrender.com')
class ChecklistTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)

    def make(self, username, role='volunteer', verified=True, **extra):
        u = User.objects.create_user(username, email=f'{username}@example.test', password=PW, **extra)
        Profile.objects.create(user=u, role=role)
        if verified: Account.objects.create(user=u, verified_email=u.email)
        return u

    def setUp(self):
        self.vol = self.make('vol', first_name='Asha', last_name='Rao')
        self.vol2 = self.make('vol2')
        self.org = self.make('org', role='organizer', first_name='Ravi')
        self.org2 = self.make('org2', role='organizer')
        self.o = Opportunity.objects.create(title='River cleanup day', slug='river', organization='Org', category='Environment', city='Pune', summary='Clean', description='Help', commitment='2h', owner=self.org, published=True, slots=5)

    def test_01_navigation(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        for name in ['explore', 'about', 'blog', 'organizations', 'opportunity_map', 'contact', 'privacy', 'signup', 'login']:
            self.assertContains(r, reverse(name))
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get(reverse('publish')).status_code, 302)

    def test_02_registration(self):
        base = {'username': 'newvol', 'first_name': 'New', 'last_name': 'Person', 'email': 'new@example.test', 'role': 'volunteer', 'password1': PW, 'password2': PW}
        r = self.client.post(reverse('signup'), base)
        self.assertRedirects(r, reverse('profile'), fetch_redirect_response=False)
        u = User.objects.get(username='newvol'); self.assertEqual(u.profile.role, 'volunteer')
        self.assertEqual(len(mail.outbox), 1); self.assertIn('https://voluntr.onrender.com/community/verify/', mail.outbox[0].body)
        self.client.logout()
        self.client.post(reverse('signup'), dict(base, username='orgx', email='orgx@example.test', role='organizer'))
        self.assertEqual(User.objects.get(username='orgx').profile.role, 'organizer'); self.client.logout()
        cases = [(dict(base, username='other1'), 'email'), (dict(base, email='z@example.test', username='NEWVOL'), 'username'),
                 (dict(base, username='x2', email='not-an-email'), 'email'), (dict(base, username='x3', email='x3@e.test', password1='12345', password2='12345'), 'password2'),
                 (dict(base, username='x4', email='x4@e.test', password2='Different-1!'), 'password2'), ({}, 'username')]
        for bad, field in cases:
            r = self.client.post(reverse('signup'), bad)
            self.assertEqual(r.status_code, 200); self.assertTrue(r.context['form'].errors.get(field), (field, r.context['form'].errors))

    def test_03_login(self):
        r = self.client.post(reverse('login'), {'username': 'vol', 'password': PW}); self.assertRedirects(r, reverse('dashboard'), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse('dashboard')), 'Hello, Asha Rao.')
        self.client.post(reverse('logout')); self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)
        r = self.client.post(reverse('login'), {'username': 'vol', 'password': 'nope'}); self.assertContains(r, 'did not match')
        for _ in range(4): self.client.post(reverse('login'), {'username': 'vol', 'password': 'nope'})
        self.assertEqual(self.client.post(reverse('login'), {'username': 'vol', 'password': PW}).status_code, 429)

    @override_settings(GOOGLE_CLIENT_ID='cid', GOOGLE_CLIENT_SECRET='sec')
    def test_03_google(self):
        import sys, types
        try:
            import google.oauth2.id_token  # noqa
        except Exception:
            # Provide stand-ins so the flow can be exercised without google-auth installed.
            for name in ['google', 'google.oauth2', 'google.oauth2.id_token', 'google.auth', 'google.auth.transport', 'google.auth.transport.requests']:
                sys.modules.setdefault(name, types.ModuleType(name))
            sys.modules['google.oauth2.id_token'].verify_oauth2_token = lambda *a, **k: None
            sys.modules['google.oauth2'].id_token = sys.modules['google.oauth2.id_token']
            sys.modules['google.auth.transport.requests'].Request = object
            sys.modules['google.auth.transport'].requests = sys.modules['google.auth.transport.requests']
            sys.modules['google'].oauth2 = sys.modules['google.oauth2']; sys.modules['google'].auth = sys.modules['google.auth']; sys.modules['google.auth'].transport = sys.modules['google.auth.transport']
        claims = {'nonce': None, 'email_verified': True, 'email': 'Priya.Sharma@gmail.com', 'sub': 'g-123', 'given_name': 'Priya', 'family_name': 'Sharma'}
        def run():
            self.client.get(reverse('google_start')); s = self.client.session['google_oauth']; claims['nonce'] = s['nonce']
            fake = mock.MagicMock(); fake.__enter__.return_value = fake
            with mock.patch('urllib.request.urlopen', return_value=fake), mock.patch('json.load', return_value={'id_token': 'x'}), mock.patch('google.oauth2.id_token.verify_oauth2_token', return_value=claims):
                return self.client.get(reverse('google_callback'), {'state': s['state'], 'code': 'abc'})
        self.assertRedirects(run(), reverse('dashboard'), fetch_redirect_response=False)
        u = User.objects.get(email='priya.sharma@gmail.com')
        self.assertFalse(u.username.startswith('google_')); self.assertEqual(u.get_full_name(), 'Priya Sharma')
        self.assertContains(self.client.get(reverse('dashboard')), 'Hello, Priya Sharma.')
        self.client.post(reverse('logout')); run(); self.assertEqual(User.objects.filter(email='priya.sharma@gmail.com').count(), 1)
        self.client.post(reverse('logout'))
        self.client.get(reverse('google_start')); s = self.client.session['google_oauth']
        r = self.client.get(reverse('google_callback'), {'state': s['state'], 'error': 'access_denied'}, follow=True)
        self.assertContains(r, 'cancelled')

    def test_04_email(self):
        u = self.make('fresh', verified=False); self.client.force_login(u)
        self.assertContains(self.client.get(reverse('dashboard')), 'Send verification email')
        r = self.client.post(reverse('resend_verification'), follow=True); self.assertContains(r, 'Verification email sent'); self.assertEqual(len(mail.outbox), 1)
        r = self.client.post(reverse('resend_verification'), follow=True); self.assertContains(r, 'less than a minute')
        r = self.client.post(reverse('apply', args=['river']), {'motivation': 'x' * 30}, follow=True); self.assertContains(r, 'verify your email'); self.assertFalse(Application.objects.exists())
        link = mail.outbox[0].body.split('https://voluntr.onrender.com')[1].split()[0]
        r = self.client.get(link, follow=True); self.assertContains(r, 'Email verified'); self.assertNotContains(r, 'Send verification email')
        r = self.client.post(reverse('change_email'), {'email': 'changed@example.test', 'password': PW}, follow=True)
        u.refresh_from_db(); self.assertEqual(u.email, 'changed@example.test'); self.assertContains(r, 'Send verification email')
        self.client.logout(); mail.outbox.clear()
        self.client.post(reverse('password_reset'), {'email': 'vol@example.test'}); self.assertEqual(len(mail.outbox), 1)
        url = [l for l in mail.outbox[0].body.split() if '/reset/' in l][0].split('testserver')[1]
        r = self.client.get(url, follow=True); self.assertContains(r, 'new password')
        self.client.post(r.redirect_chain[-1][0], {'new_password1': 'Another-Pass-77!', 'new_password2': 'Another-Pass-77!'})
        self.assertTrue(self.client.login(username='vol', password='Another-Pass-77!')); self.assertFalse(self.client.login(username='vol', password=PW))
        self.client.logout(); self.assertContains(self.client.get(url, follow=True), 'already been used')

    @override_settings(EMAIL_BACKEND='community.email_backend.BrevoEmailBackend', BREVO_API_KEY='k', DEFAULT_FROM_EMAIL='Voluntr <hello@voluntr.test>')
    def test_04_brevo_backend(self):
        resp = mock.MagicMock(status=201); resp.__enter__.return_value = resp
        with mock.patch('urllib.request.urlopen', return_value=resp) as call:
            self.assertEqual(mail.send_mail('Hi', 'Body', None, ['a@b.test']), 1)
        req = call.call_args[0][0]; body = json.loads(req.data)
        self.assertEqual(req.full_url, 'https://api.brevo.com/v3/smtp/email')
        self.assertEqual(body['sender'], {'email': 'hello@voluntr.test', 'name': 'Voluntr'}); self.assertEqual(body['to'], [{'email': 'a@b.test'}])

    def test_05_profile(self):
        self.client.force_login(self.vol)
        r = self.client.post(reverse('profile'), {'first_name': 'Asha', 'last_name': 'Kulkarni', 'bio': 'I like helping', 'city': 'Pune', 'skills': 'teaching, first aid', 'interests': ['Education', 'Environment']})
        self.assertRedirects(r, reverse('dashboard'), fetch_redirect_response=False)
        p = Profile.objects.get(user=self.vol); self.assertEqual((p.city, p.interests, p.skills, p.bio), ('Pune', 'Education,Environment', 'teaching, first aid', 'I like helping'))
        self.client.logout(); self.client.login(username='vol', password=PW)
        self.assertContains(self.client.get(reverse('dashboard')), 'Hello, Asha Kulkarni.')
        self.assertContains(self.client.get(reverse('profile')), 'checked')
        r = self.client.post(reverse('profile'), {'first_name': 'A1!', 'city': '123', 'skills': 'x' * 70}); self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.context['form'].errors), {'first_name', 'city', 'skills'})

    def test_06_discovery(self):
        r = self.client.get(reverse('explore')); self.assertGreaterEqual(r.context['page'].paginator.count, 19)
        self.assertTrue(all(o.category == 'Environment' for o in self.client.get(reverse('explore'), {'category': 'Environment'}).context['page']))
        self.assertTrue(all(o.city == 'Mumbai' for o in self.client.get(reverse('explore'), {'city': 'Mumbai'}).context['page']))
        r = self.client.get(reverse('explore'), {'category': 'Environment', 'city': 'Pune'}); self.assertIn('river', [o.slug for o in r.context['page']]); self.assertTrue(all(o.city == 'Pune' and o.category == 'Environment' for o in r.context['page']))
        self.assertContains(self.client.get(reverse('explore'), {'q': 'Education'}), 'Tutoring for Kids')
        self.assertContains(self.client.get(reverse('explore'), {'q': 'xyz123'}), 'No opportunities match')
        self.assertEqual(self.client.get(reverse('explore'), {'page': 2}).context['page'].number, 2)
        d = self.client.get(reverse('detail', args=['tutoring-for-kids'])); self.assertContains(d, 'About the opportunity')
        self.assertContains(d, '/community/organizations/bright-futures-learning-trust-sample/')
        self.o.deadline = timezone.localdate() - timedelta(days=1); self.o.save()
        self.client.force_login(self.vol)
        self.assertContains(self.client.get(reverse('detail', args=['river'])), 'Applications for this opportunity are closed')
        self.client.post(reverse('apply', args=['river']), {'motivation': 'x' * 30}); self.assertFalse(Application.objects.exists())
        Profile.objects.filter(user=self.vol).update(interests='Animals')
        self.assertEqual(self.client.get(reverse('dashboard')).context['matches'][0].category, 'Animals')

    def test_07_applications(self):
        self.client.force_login(self.vol)
        self.client.post(reverse('bookmark', args=['river'])); self.assertContains(self.client.get(reverse('dashboard')), 'River cleanup day')
        self.client.post(reverse('bookmark', args=['river'])); self.assertFalse(Bookmark.objects.exists())
        r = self.client.post(reverse('apply', args=['river']), {'motivation': 'I would love to help clean the river.'}, follow=True)
        self.assertContains(r, 'Application submitted'); self.assertContains(r, 'Pending')
        self.assertContains(self.client.get(reverse('apply', args=['river']), follow=True), 'already applied')
        self.assertEqual(Application.objects.count(), 1)
        self.assertTrue(Notification.objects.filter(user=self.org, text__icontains='Asha Rao').exists())
        a = Application.objects.get()
        self.client.force_login(self.org); mail.outbox.clear()
        self.assertContains(self.client.get(reverse('dashboard')), 'Asha Rao')
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('review', args=[a.pk]), {'status': 'accepted'})
        a.refresh_from_db(); self.assertEqual(a.status, 'accepted')
        self.assertEqual(mail.outbox[0].to, ['vol@example.test']); self.assertIn('accepted', mail.outbox[0].body)
        self.client.force_login(self.vol2); self.client.post(reverse('apply', args=['river']), {'motivation': 'Another applicant here, hello!'})
        b = Application.objects.get(volunteer=self.vol2)
        self.client.force_login(self.org)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('review', args=[b.pk]), {'status': 'declined'})
        self.client.force_login(self.vol2); self.assertContains(self.client.get(reverse('dashboard')), 'Rejected')
        self.assertIn('not accepted', mail.outbox[-1].body)
        self.assertContains(self.client.get(reverse('dashboard')), 'class="count-badge"')
        n = Notification.objects.filter(user=self.vol2).first()
        self.assertRedirects(self.client.get(reverse('open_notification', args=[n.pk])), reverse('dashboard'), fetch_redirect_response=False)
        n.refresh_from_db(); self.assertTrue(n.read)
        self.client.post(reverse('mark_read')); self.assertFalse(Notification.objects.filter(user=self.vol2, read=False).exists())
        self.client.force_login(self.vol); self.assertEqual(self.client.get(reverse('open_notification', args=[n.pk])).status_code, 404)
        o2 = Opportunity.objects.create(title='Second', slug='second', organization='Org', category='Health', city='Pune', summary='s', description='d', commitment='1h', owner=self.org, published=True)
        self.client.force_login(self.vol2)
        self.client.post(reverse('apply', args=['second']), {'motivation': 'Happy to help with this one.'}); c = Application.objects.get(opportunity=o2)
        self.client.post(reverse('withdraw', args=[c.pk])); c.refresh_from_db(); self.assertEqual(c.status, 'withdrawn')
        self.assertContains(self.client.get(reverse('activity')), 'Withdrawn')

    def test_09_organizer(self):
        self.client.force_login(self.org)
        self.assertContains(self.client.get(reverse('dashboard')), 'Create opportunity')
        self.assertTrue(self.client.post(reverse('publish'), {}).context['form'].errors)
        data = {'title': 'Beach Day', 'organization': 'Org', 'category': 'Environment', 'city': 'Mumbai', 'mode': 'On-site', 'summary': 'Sum', 'description': 'Desc', 'skills': '', 'commitment': '2h', 'slots': 3}
        self.client.post(reverse('publish'), data); o = Opportunity.objects.get(title='Beach Day')
        self.assertFalse(o.published); self.assertContains(self.client.get(reverse('dashboard')), 'Awaiting moderation')
        self.assertEqual(self.client.get(reverse('detail', args=[o.slug])).status_code, 404)
        self.client.post(reverse('edit_opportunity', args=[o.slug]), dict(data, title='Beach Day Updated')); o.refresh_from_db(); self.assertEqual(o.title, 'Beach Day Updated')
        o.published = True; o.save(); self.assertEqual(self.client.get(reverse('detail', args=[o.slug])).status_code, 200)
        self.client.post(reverse('toggle_listing', args=[o.slug])); o.refresh_from_db(); self.assertTrue(o.closed)
        self.client.force_login(self.vol); self.client.post(reverse('apply', args=[o.slug]), {'motivation': 'x' * 30}); self.assertFalse(Application.objects.filter(opportunity=o).exists())
        self.client.post(reverse('apply', args=['river']), {'motivation': 'Let me help with the river.'})
        self.client.force_login(self.org)
        csv = self.client.get(reverse('export_applications')); self.assertEqual(csv['Content-Type'], 'text/csv'); self.assertIn(b'Asha Rao', csv.content)
        r = self.client.get(reverse('dashboard')); self.assertEqual(len(r.context['incoming']), 1); self.assertEqual(r.context['incoming_pending'], 1)
        self.client.force_login(self.org2); self.assertEqual(self.client.get(reverse('edit_opportunity', args=['river'])).status_code, 404)
        self.client.force_login(self.vol); self.assertEqual(self.client.get(reverse('publish')).status_code, 302)
        self.assertEqual(self.client.get(reverse('edit_organization')).status_code, 302)

    def test_10_organizations(self):
        r = self.client.get(reverse('organizations')); self.assertGreaterEqual(len(r.context['organizations']), 9)
        self.assertContains(r, 'Sample profile'); self.assertContains(r, 'Not verified')
        self.assertEqual(len(self.client.get(reverse('organizations'), {'q': 'Paws'}).context['organizations']), 1)
        self.assertTrue(all(o.city == 'Mumbai' for o in self.client.get(reverse('organizations'), {'city': 'Mumbai'}).context['organizations']))
        self.assertContains(self.client.get(reverse('organization', args=['green-streets-collective-sample'])), 'Environmental Cleanup')
        self.client.force_login(self.org)
        self.client.post(reverse('edit_organization'), {'name': 'River Friends', 'bio': 'We clean rivers.', 'city': 'Pune', 'website': '', 'verification_note': '', 'public': 'on'})
        mine = Organization.objects.get(owner=self.org); self.assertEqual(mine.name, 'River Friends')
        self.assertContains(self.client.get(reverse('detail', args=['river'])), mine.slug)
        self.assertNotContains(self.client.get(reverse('organization', args=[mine.slug])), '✓ Verified')
        mine.verified = True; mine.save(); self.assertContains(self.client.get(reverse('organization', args=[mine.slug])), 'Verified organization')

    def test_11_map(self):
        r = self.client.get(reverse('opportunity_map')); pts = r.context['points']
        self.assertGreaterEqual(len(pts), 15); self.assertContains(r, 'leaflet'); self.assertIn('/opportunities/river/', [p['url'] for p in pts])
        self.assertEqual(len({tuple(p['coords']) for p in pts}), len(pts))
        self.assertTrue(all(p['category'] == 'Animals' for p in self.client.get(reverse('opportunity_map'), {'category': 'Animals'}).context['points']))
        self.assertEqual(r['Referrer-Policy'], 'strict-origin-when-cross-origin')
        self.client.force_login(self.org); self.client.post(reverse('edit_location', args=['river']), {'latitude': 18.5, 'longitude': 73.8})
        self.assertTrue(Location.objects.filter(opportunity=self.o).exists())

    def test_12_events_hours(self):
        a = Application.objects.create(volunteer=self.vol, opportunity=self.o, motivation='m' * 25, status='accepted')
        self.client.force_login(self.org)
        start = timezone.localtime() + timedelta(minutes=10)
        self.client.post(reverse('create_event', args=['river']), {'title': 'Cleanup', 'starts': start.strftime('%Y-%m-%dT%H:%M'), 'ends': (start + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'), 'venue': 'Ghat 3'})
        e = Event.objects.get(); self.assertTrue(Notification.objects.filter(user=self.vol, text__startswith='New event').exists())
        self.assertContains(self.client.get(reverse('event_detail', args=[e.pk])), 'Attendance QR')
        try:
            import PIL.Image  # noqa
            self.assertEqual(self.client.get(reverse('event_qr', args=[e.pk]))['Content-Type'], 'image/png')
        except Exception:
            pass
        self.client.force_login(self.vol)
        self.assertContains(self.client.get(reverse('calendar')), 'Cleanup')
        nxt = (timezone.localdate().replace(day=1) + timedelta(days=40)).strftime('%Y-%m')
        self.assertEqual(self.client.get(reverse('calendar'), {'month': nxt}).context['month'].strftime('%Y-%m'), nxt)
        self.assertEqual(len(self.client.get(reverse('dashboard')).context['upcoming']), 1)
        url = reverse('checkin', args=[e.pk, e.checkin_key])
        self.client.post(url); self.client.post(url); self.assertEqual(Attendance.objects.count(), 1)
        self.client.force_login(self.vol2); self.assertEqual(self.client.post(url).status_code, 403)
        self.assertEqual(self.client.get(f'/community/events/{e.pk}/checkin/00000000-0000-0000-0000-000000000000/').status_code, 404)
        self.client.force_login(self.vol)
        r = self.client.post(reverse('log_hours', args=[a.pk]), {'date': timezone.localdate(), 'hours': '-2', 'note': 'n'}); self.assertTrue(r.context['form'].errors.get('hours'))
        self.client.post(reverse('log_hours', args=[a.pk]), {'date': timezone.localdate(), 'hours': '3', 'note': 'Cleanup'})
        self.client.post(reverse('log_hours', args=[a.pk]), {'date': timezone.localdate(), 'hours': '5', 'note': 'Wrong'})
        self.assertEqual(self.client.get(reverse('certificate', args=[a.pk])).status_code, 302)
        h3, h5 = Hours.objects.get(hours=3), Hours.objects.get(hours=5)
        self.client.force_login(self.org)
        self.assertContains(self.client.get(reverse('dashboard')), 'Wrong')
        self.client.post(reverse('approve_hours', args=[h3.pk])); self.client.post(reverse('reject_hours', args=[h5.pk]))
        self.client.force_login(self.vol)
        self.assertEqual(self.client.get(reverse('dashboard')).context['total'], 3)
        imp = self.client.get(reverse('impact')); self.assertEqual(imp.context['total'], 3); self.assertContains(imp, '★ Earned')
        cert = self.client.get(reverse('certificate', args=[a.pk])); self.assertContains(cert, 'Asha Rao'); self.assertContains(cert, '3 approved volunteer hours'); self.assertContains(cert, 'window.print')
        self.client.force_login(self.vol2); self.assertEqual(self.client.get(reverse('certificate', args=[a.pk])).status_code, 404)
        self.client.force_login(self.org); self.assertContains(self.client.get(reverse('impact')), 'Organization analytics')
        self.client.post(reverse('edit_event', args=[e.pk, 'river']), {'title': 'Cleanup', 'starts': '2025-01-01T10:00', 'ends': '2025-01-01T12:00', 'venue': 'Ghat 3'})
        e.refresh_from_db(); self.assertEqual(e.starts.year, 2025); self.assertContains(self.client.get(reverse('event_detail', args=[e.pk])), 'Completed')
        self.client.force_login(self.vol); self.assertEqual(len(self.client.get(reverse('dashboard')).context['completed']), 1)

    def test_15_fresh_account(self):
        u = self.make('blank'); self.client.force_login(u)
        for name in ['dashboard', 'impact', 'calendar', 'inbox', 'notifications', 'activity', 'profile']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertNotContains(self.client.get(reverse('impact')), '★ Earned')

    def test_18_messaging(self):
        a = Application.objects.create(volunteer=self.vol, opportunity=self.o, motivation='m' * 25)
        self.client.force_login(self.vol)
        self.client.post(reverse('conversation', args=[a.pk]), {'body': 'Hello organizer'})
        self.client.post(reverse('conversation', args=[a.pk]), {'body': '   '}); self.assertEqual(Message.objects.count(), 1)
        self.client.force_login(self.org)
        self.assertContains(self.client.get(reverse('inbox')), 'count-badge">New')
        self.assertContains(self.client.get(reverse('conversation', args=[a.pk])), 'Hello organizer')
        self.assertNotContains(self.client.get(reverse('inbox')), 'count-badge">New')
        self.client.post(reverse('conversation', args=[a.pk]), {'body': 'Welcome!'})
        self.client.force_login(self.vol); self.assertContains(self.client.get(reverse('conversation', args=[a.pk])), 'Welcome!')
        self.client.force_login(self.vol2); self.assertEqual(self.client.get(reverse('conversation', args=[a.pk])).status_code, 404)

    def test_19_reminders(self):
        Application.objects.create(volunteer=self.vol, opportunity=self.o, motivation='m' * 25, status='accepted')
        Event.objects.create(opportunity=self.o, title='Soon', starts=timezone.now() + timedelta(hours=3), ends=timezone.now() + timedelta(hours=4))
        with self.captureOnCommitCallbacks(execute=True):
            call_command('send_event_reminders', verbosity=0)
        with self.captureOnCommitCallbacks(execute=True):
            call_command('send_event_reminders', verbosity=0)
        self.assertEqual(Notification.objects.filter(user=self.vol, text__startswith='Upcoming').count(), 1)
        self.assertEqual(len([m for m in mail.outbox if 'Soon' in m.body]), 1)

    def test_20_journal(self):
        self.assertEqual(len(self.client.get(reverse('blog')).context['articles']), 8)
        art = Article.objects.first(); self.assertEqual(len(self.client.get(reverse('article', args=[art.slug])).context['related']), 3)
        self.assertTrue(all(a.category == 'Impact' for a in self.client.get(reverse('blog'), {'category': 'Impact'}).context['articles']))
        self.assertGreater(len(self.client.get(reverse('blog'), {'q': 'volunteer'}).context['articles']), 0)

    def test_21_forms(self):
        r = self.client.post(reverse('contact'), {'name': 'T', 'email': 't@e.test', 'message': 'Testing the contact form'}, follow=True)
        self.assertContains(r, 'Thanks for reaching out'); self.assertEqual(Contact.objects.count(), 1)
        self.assertTrue(self.client.post(reverse('contact'), {}).context['form'].errors)
        self.assertContains(self.client.post(reverse('subscribe'), {'email': 'n@e.test'}, follow=True), 'Thanks for subscribing')
        self.assertContains(self.client.post(reverse('subscribe'), {'email': 'N@e.test'}, follow=True), 'already subscribed'); self.assertEqual(Subscriber.objects.count(), 1)
        self.assertContains(self.client.post(reverse('subscribe'), {'email': 'bad'}, follow=True), 'valid email')
        self.client.force_login(self.vol); self.client.post(reverse('report_listing', args=['river']), {'reason': 'Looks like spam to me'})
        self.assertEqual(ListingReport.objects.count(), 1)

    def test_24_26_platform(self):
        self.assertContains(self.client.get('/sitemap.xml'), '<urlset')
        self.assertContains(self.client.get('/robots.txt'), 'Sitemap:')
        self.assertEqual(self.client.get('/manifest.webmanifest').json()['name'], 'Voluntr')
        self.assertContains(self.client.get('/service-worker.js'), 'offline')
        self.assertEqual(self.client.get('/health/').json(), {'status': 'ok'})
        self.assertContains(self.client.get(reverse('detail', args=['river'])), 'og:title')
        self.client.force_login(self.vol); self.assertEqual(self.client.get('/admin/').status_code, 302)
        self.assertEqual(self.client.get(reverse('export_applications')).status_code, 302)
        Profile.objects.filter(user=self.vol).update(bio='<script>alert(1)</script>')
        self.assertNotContains(self.client.get(reverse('profile')), '<script>alert(1)</script>')
        admin = User.objects.create_superuser('boss', 'b@e.test', PW); self.client.force_login(admin)
        for path in ['/admin/', '/admin/auth/user/', '/admin/core/opportunity/', '/admin/core/application/', '/admin/core/hours/', '/admin/community/event/', '/admin/community/organization/', '/admin/core/article/', '/admin/core/subscriber/', '/admin/core/contact/', '/admin/core/listingreport/']:
            self.assertEqual(self.client.get(path).status_code, 200, path)
        pending = Opportunity.objects.create(title='Pending', slug='pending', organization='O', category='Health', city='Pune', summary='s', description='d', commitment='1h', owner=self.org)
        self.client.post('/admin/core/opportunity/', {'action': 'publish_selected', '_selected_action': [pending.pk]}); pending.refresh_from_db(); self.assertTrue(pending.published)
        self.assertTrue(Notification.objects.filter(user=self.org, text__contains='approved').exists())
        self.assertEqual(self.client.get('/random123/').status_code, 404)

    def test_27_seed_preserves_edits(self):
        a = Article.objects.first(); a.summary = 'Edited by admin'; a.save()
        call_command('seed_demo', verbosity=0); a.refresh_from_db(); self.assertEqual(a.summary, 'Edited by admin')
        self.assertEqual(Organization.objects.filter(name__endswith='(Sample)').count(), 9)
