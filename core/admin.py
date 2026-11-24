from django.contrib import admin
from .models import *

admin.site.site_header = 'Voluntr administration'
admin.site.site_title = 'Voluntr admin'

@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display=('title','organization','owner_name','category','city','published','closed','demo','created'); list_filter=('published','closed','category','demo'); search_fields=('title','organization','city','owner__username'); prepopulated_fields={'slug':('title',)}; actions=['publish_selected','unpublish_selected']; list_editable=('published',)
    @admin.display(description='Owner',ordering='owner__username')
    def owner_name(self,o):
        if not o.owner: return '—'
        return 'Sample account' if not o.owner.is_active else (o.owner.get_full_name() or o.owner.username)
    @admin.action(description='Approve & publish selected opportunities')
    def publish_selected(self,request,queryset):
        from community.services import notify
        from django.urls import reverse
        for o in queryset.filter(published=False):
            o.published=True; o.save(update_fields=['published'])
            notify(o.owner,f'Your listing "{o.title}" was approved and is now public.',reverse('detail',args=[o.slug]),email=True)
    @admin.action(description='Unpublish selected opportunities')
    def unpublish_selected(self,request,queryset): queryset.update(published=False)
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display=('volunteer','opportunity','status','created'); list_filter=('status',); search_fields=('volunteer__username','volunteer__email','opportunity__title')
@admin.register(Hours)
class HoursAdmin(admin.ModelAdmin):
    list_display=('application','date','hours','approved','rejected'); list_filter=('approved','rejected')
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display=('user','role','city'); list_filter=('role',); search_fields=('user__username','user__email','city')
@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display=('title','category','published','created'); list_filter=('published','category'); search_fields=('title','summary'); prepopulated_fields={'slug':('title',)}
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display=('name','email','created'); search_fields=('name','email','message'); readonly_fields=('created',)
@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display=('email','created'); search_fields=('email',)
admin.site.register(Bookmark)
@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_display=('opportunity','reporter','resolved','created')
    list_filter=('resolved',); actions=['mark_resolved']
    @admin.action(description='Mark selected reports resolved')
    def mark_resolved(self,request,queryset): queryset.update(resolved=True)
