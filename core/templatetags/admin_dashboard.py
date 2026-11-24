from django import template
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.urls import reverse

register = template.Library()


@register.simple_tag
def voluntr_admin_stats():
    from core.models import Opportunity, Application, Hours, ListingReport, Contact, Subscriber, Profile
    from community.models import Organization, Event
    User = get_user_model()
    real_users = User.objects.filter(is_active=True)
    pl = lambda n, word: f"{n} {word}{'' if n == 1 else 's'}"
    cl = lambda model, query='': reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist') + query
    return {
        'cards': [
            {'label': 'Active users', 'value': real_users.count(), 'sub': pl(Profile.objects.filter(role='volunteer', user__is_active=True).count(), 'volunteer') + ' · ' + pl(Profile.objects.filter(role='organizer', user__is_active=True).count(), 'organizer'), 'url': cl(User)},
            {'label': 'Live opportunities', 'value': Opportunity.objects.filter(published=True, closed=False).count(), 'sub': f"{Opportunity.objects.filter(demo=True).count()} are samples", 'url': cl(Opportunity, '?published__exact=1')},
            {'label': 'Applications', 'value': Application.objects.count(), 'sub': f"{Application.objects.filter(status='pending').count()} pending · {Application.objects.filter(status='accepted').count()} accepted", 'url': cl(Application)},
            {'label': 'Approved hours', 'value': Hours.objects.filter(approved=True).aggregate(s=Sum('hours'))['s'] or 0, 'sub': pl(Hours.objects.filter(approved=False, rejected=False).count(), 'submission') + ' awaiting review', 'url': cl(Hours)},
        ],
        'queue': [
            {'label': 'Listings awaiting approval', 'value': Opportunity.objects.filter(published=False).count(), 'url': cl(Opportunity, '?published__exact=0'), 'tone': 'warn'},
            {'label': 'Open listing reports', 'value': ListingReport.objects.filter(resolved=False).count(), 'url': cl(ListingReport, '?resolved__exact=0'), 'tone': 'danger'},
            {'label': 'Organizations to verify', 'value': Organization.objects.filter(verified=False, owner__is_active=True).count(), 'url': cl(Organization, '?verified__exact=0'), 'tone': 'info'},
            {'label': 'Contact messages', 'value': Contact.objects.count(), 'url': cl(Contact), 'tone': ''},
            {'label': 'Newsletter subscribers', 'value': Subscriber.objects.count(), 'url': cl(Subscriber), 'tone': ''},
            {'label': 'Scheduled events', 'value': Event.objects.filter(cancelled=False).count(), 'url': cl(Event), 'tone': ''},
        ],
        'pending': Opportunity.objects.filter(published=False).select_related('owner').order_by('-created')[:6],
        'reports': ListingReport.objects.filter(resolved=False).select_related('opportunity', 'reporter')[:5],
    }
