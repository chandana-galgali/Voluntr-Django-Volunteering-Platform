from django.contrib import admin
from .models import *
@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display=('title','organization','category','published','demo'); list_filter=('category','published','demo'); search_fields=('title','organization'); prepopulated_fields={'slug':('title',)}; actions=['publish_selected']
    @admin.action(description='Publish selected opportunities')
    def publish_selected(self,request,queryset): queryset.update(published=True)
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display=('volunteer','opportunity','status','created'); list_filter=('status',)
admin.site.register([Profile,Bookmark,Hours,Article,Contact,Subscriber])
@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_display=('opportunity','reporter','resolved','created')
    list_filter=('resolved',)
