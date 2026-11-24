from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from core.models import Opportunity, Article
from .models import Organization
class StaticMap(Sitemap):
    def items(self): return ['home','explore','blog','about','contact','privacy','organizations','opportunity_map']
    def location(self,item): return reverse(item)
class OpportunityMap(Sitemap):
    def items(self): return Opportunity.objects.filter(published=True).order_by('pk')
    def location(self,obj): return reverse('detail',args=[obj.slug])
class JournalMap(Sitemap):
    def items(self): return Article.objects.filter(published=True).order_by('pk')
    def location(self,obj): return reverse('article',args=[obj.slug])
class OrgMap(Sitemap):
    def items(self): return Organization.objects.filter(public=True).order_by('pk')
    def location(self,obj): return reverse('organization',args=[obj.slug])
