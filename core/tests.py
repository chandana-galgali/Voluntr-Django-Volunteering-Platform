from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Opportunity,Profile,Application,Bookmark,Hours
class WorkflowTests(TestCase):
    def setUp(self):
        self.vol=User.objects.create_user('vol',email='vol@example.test',password='Long-test-password-123')
        self.org=User.objects.create_user('org',email='org@example.test',password='Long-test-password-123')
        from community.models import Account
        Account.objects.create(user=self.vol,verified_email=self.vol.email)
        Account.objects.create(user=self.org,verified_email=self.org.email)
        Profile.objects.create(user=self.vol); Profile.objects.create(user=self.org,role='organizer')
        self.o=Opportunity.objects.create(title='Beach cleanup',slug='beach',organization='Demo',category='Environment',city='Mumbai',summary='Cleanup',description='Help safely',commitment='2h',published=True,owner=self.org,slots=1)
    def test_public_pages(self):
        for name in ['home','explore','about','blog','contact','api','privacy','login','signup']:
            self.assertEqual(self.client.get(reverse(name)).status_code,200)
    def test_search(self):
        self.assertContains(self.client.get(reverse('explore'),{'q':'Beach'}),'Beach cleanup')
        self.assertNotContains(self.client.get(reverse('explore'),{'q':'nonexistent'}),'Beach cleanup')
    def test_private_apply(self):
        self.assertEqual(self.client.get(reverse('apply',args=['beach'])).status_code,302)
    def test_workflow(self):
        self.client.force_login(self.vol)
        for _ in range(2): self.client.post(reverse('apply',args=['beach']),{'motivation':'I would like to help the community.'})
        self.assertEqual(Application.objects.count(),1)
        a=Application.objects.get(); self.client.post(reverse('bookmark',args=['beach'])); self.assertEqual(Bookmark.objects.count(),1)
        self.assertEqual(self.client.post(reverse('review',args=[a.pk]),{'status':'accepted'}).status_code,404)
        self.client.force_login(self.org); self.client.post(reverse('review',args=[a.pk]),{'status':'accepted'}); a.refresh_from_db(); self.assertEqual(a.status,'accepted')
        self.client.force_login(self.vol); self.client.post(reverse('log_hours',args=[a.pk]),{'date':'2025-01-01','hours':'2','note':'Cleanup'}); h=Hours.objects.get()
        self.client.force_login(self.org); self.client.post(reverse('approve_hours',args=[h.pk])); h.refresh_from_db(); self.assertTrue(h.approved)
    def test_unpublished_hidden(self):
        self.o.published=False; self.o.save(); self.assertEqual(self.client.get(reverse('detail',args=['beach'])).status_code,404)
    def test_post_only(self):
        self.client.force_login(self.vol); self.assertEqual(self.client.get(reverse('bookmark',args=['beach'])).status_code,405)

class FinalFeatureTests(TestCase):
    def test_password_reset_page(self):
        self.assertEqual(self.client.get('/password-reset/').status_code,200)
    def test_private_activity_requires_login(self):
        self.assertEqual(self.client.get('/activity/').status_code,302)
    def test_private_export_requires_login(self):
        self.assertEqual(self.client.get('/organizer/export/').status_code,302)
    def test_journal_search(self):
        self.assertEqual(self.client.get('/journal/',{'q':'community'}).status_code,200)

class SeedContentTests(TestCase):
    def test_utf8_refresh_and_unique_images(self):
        from django.core.management import call_command
        from django.conf import settings
        from pathlib import Path
        from .models import Article
        call_command('seed_demo')
        call_command('seed_demo')
        self.assertEqual(Opportunity.objects.filter(demo=True).count(),18)
        self.assertEqual(Article.objects.count(),8)
        senior=Opportunity.objects.get(title='Senior Citizens’ Tech Support')
        senior.title='Senior Citizensâ€™ Tech Support'; senior.save()
        call_command('seed_demo'); senior.refresh_from_db()
        self.assertEqual(senior.title,'Senior Citizens’ Tech Support')
        images=list(Opportunity.objects.filter(demo=True).values_list('image',flat=True))+list(Article.objects.values_list('image',flat=True))
        self.assertEqual(len(images),len(set(images)))
        for image in images:
            self.assertTrue((Path(settings.BASE_DIR)/'static'/image).is_file(),image)
