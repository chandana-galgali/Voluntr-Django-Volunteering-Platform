from datetime import timedelta
from io import BytesIO
from uuid import uuid4
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Count
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST, require_GET
from core.models import Profile, Opportunity, Application, Hours
from .models import Organization, Location, Event, Attendance, Notification, Message
from .forms import OrganizationForm, EventForm, LocationForm, MessageForm
from .services import email_verified, notify, can_act, display_name
import calendar as pycal
from datetime import date

def permitted(request):
    return can_act(request.user)

def gate(request):
    messages.error(request,'Please verify your email address first. Use "Send verification email" at the top of the page.'); return redirect('dashboard')

def is_organizer(user): return Profile.objects.filter(user=user,role='organizer').exists()

def organizations(request):
    qs=Organization.objects.filter(public=True).annotate(listing_count=Count('owner__opportunity',filter=Q(owner__opportunity__published=True))).order_by('-verified','name')
    q=request.GET.get('q','').strip(); city=request.GET.get('city','').strip()
    if q: qs=qs.filter(Q(name__icontains=q)|Q(bio__icontains=q))
    if city: qs=qs.filter(city__iexact=city)
    cities=Organization.objects.filter(public=True).order_by('city').values_list('city',flat=True).distinct()
    return render(request,'community/organizations.html',{'organizations':qs,'cities':cities})

def organization(request,slug):
    org=get_object_or_404(Organization,slug=slug,public=True)
    return render(request,'community/organization.html',{'org':org,'listings':Opportunity.objects.filter(owner=org.owner,published=True).filter(Q(deadline__isnull=True)|Q(deadline__gte=timezone.localdate()))})

@login_required
def edit_organization(request):
    if not is_organizer(request.user):
        messages.info(request,'Organization profiles are available to organizer accounts.'); return redirect('dashboard')
    org=Organization.objects.filter(owner=request.user).first()
    f=OrganizationForm(request.POST if request.method=='POST' else None,instance=org)
    if request.method=='POST' and not permitted(request): return gate(request)
    if request.method=='POST' and f.is_valid():
        obj=f.save(commit=False); obj.owner=request.user
        if not org: obj.slug=slugify(obj.name)[:100]+'-'+uuid4().hex[:8]
        if org and f.has_changed() and set(f.changed_data)&{'name','website','verification_note'}: obj.verified=False
        obj.save()
        # Keep listing cards consistent with the organization name.
        Opportunity.objects.filter(owner=request.user).update(organization=obj.name)
        messages.success(request,'Organization profile saved.'+('' if obj.public else ' Tick "Public" to show it in the Organizations directory.')+' Verification is subject to administrator review.'); return redirect('organization',slug=obj.slug) if obj.public else redirect('dashboard')
    return render(request,'form.html',{'form':f,'title':'Organization profile','action':'Save profile','intro':'Public profiles appear in the Organizations directory and on your listings.'})

@login_required
def location(request,slug):
    if not permitted(request): return gate(request)
    o=get_object_or_404(Opportunity,slug=slug,owner=request.user)
    loc=Location.objects.filter(opportunity=o).first()
    initial=None
    if not loc and city_point(o.city): initial={'latitude':city_point(o.city)[0],'longitude':city_point(o.city)[1],'approximate':True}
    f=LocationForm(request.POST if request.method=='POST' else None,instance=loc,initial=initial)
    if request.method=='POST' and f.is_valid():
        obj=f.save(commit=False); obj.opportunity=o; obj.save(); messages.success(request,'Map location saved.'); return redirect('dashboard')
    return render(request,'form.html',{'form':f,'title':'Set public map location (use a meeting point, not a private address)','action':'Save location'})

CITY_POINTS={'mumbai':[19.076,72.8777],'navi mumbai':[19.033,73.0297],'thane':[19.2183,72.9781],'pune':[18.5204,73.8567],'delhi':[28.6139,77.2090],'new delhi':[28.6139,77.2090],'noida':[28.5355,77.3910],'gurugram':[28.4595,77.0266],'gurgaon':[28.4595,77.0266],'bengaluru':[12.9716,77.5946],'bangalore':[12.9716,77.5946],'chennai':[13.0827,80.2707],'hyderabad':[17.385,78.4867],'kolkata':[22.5726,88.3639],'ahmedabad':[23.0225,72.5714],'jaipur':[26.9124,75.7873],'lucknow':[26.8467,80.9462],'kochi':[9.9312,76.2673],'chandigarh':[30.7333,76.7794],'indore':[22.7196,75.8577],'bhopal':[23.2599,77.4126],'nagpur':[21.1458,79.0882],'goa':[15.2993,74.124],'surat':[21.1702,72.8311],'mysuru':[12.2958,76.6394],'mysore':[12.2958,76.6394],'coimbatore':[11.0168,76.9558],'visakhapatnam':[17.6868,83.2185],'patna':[25.5941,85.1376],'bhubaneswar':[20.2961,85.8245],'dehradun':[30.3165,78.0322]}
def city_point(city): return CITY_POINTS.get((city or '').strip().lower())
def map_page(request):
    points=[]; category=request.GET.get('category','')
    qs=Opportunity.objects.filter(published=True,closed=False).filter(Q(deadline__isnull=True)|Q(deadline__gte=timezone.localdate())).exclude(mode='Remote').select_related('map_location')
    if category: qs=qs.filter(category=category)
    for o in qs[:500]:
        loc=getattr(o,'map_location',None)
        coords=[loc.latitude,loc.longitude] if loc else city_point(o.city)
        if coords:
            if not loc:
                # Spread listings that share a city centre so every pin can be clicked.
                n=sum(1 for p in points if p['city'].lower()==o.city.lower() and p['approximate'])
                coords=[coords[0]+0.012*(n%4)-0.018,coords[1]+0.012*(n//4)-0.006] if n else coords
            points.append({'title':o.title,'city':o.city,'category':o.category,'mode':o.mode,'coords':coords,'approximate':loc.approximate if loc else True,'url':reverse('detail',args=[o.slug])})
    from core.models import Opportunity as Opp
    return render(request,'community/map.html',{'points':points,'categories':Opp.CATEGORIES,'category':category})

@login_required
def impact(request):
    organizer=is_organizer(request.user)
    qs=Hours.objects.filter(approved=True,application__opportunity__owner=request.user) if organizer else Hours.objects.filter(approved=True,application__volunteer=request.user)
    total=qs.aggregate(s=Sum('hours'))['s'] or 0
    apps=Application.objects.filter(opportunity__owner=request.user) if organizer else Application.objects.filter(volunteer=request.user)
    breakdown=qs.values('application__opportunity__category').annotate(hours=Sum('hours')).order_by('-hours')
    attended=Attendance.objects.filter(volunteer=request.user).count() if not organizer else Attendance.objects.filter(event__opportunity__owner=request.user).count()
    completed=apps.filter(status='accepted',hours__approved=True).distinct().count()
    badges=[]
    if not organizer:
        for target,label in [(1,'First steps'),(10,'Community contributor'),(25,'Changemaker'),(50,'Impact champion'),(100,'Century of service')]:
            badges.append({'label':label,'target':target,'earned':total>=target})
    return render(request,'community/impact.html',{'attended':attended,'completed':completed,'total':total,'apps':apps.count(),'accepted':apps.filter(status='accepted').count(),'people':apps.filter(status='accepted').values('volunteer').distinct().count(),'breakdown':breakdown,'badges':badges,'organizer':organizer})

@login_required
def notifications(request):
    return render(request,'community/notifications.html',{'items':Notification.objects.filter(user=request.user)[:100]})
@login_required
def open_notification(request,pk):
    item=get_object_or_404(Notification,pk=pk,user=request.user)
    if not item.read: item.read=True; item.save(update_fields=['read'])
    link=item.link if item.link.startswith('/') and not item.link.startswith('//') else ''
    return redirect(link or 'notifications')
@login_required
@require_POST
def mark_read(request):
    Notification.objects.filter(user=request.user,read=False).update(read=True); messages.success(request,'All notifications marked as read.'); return redirect('notifications')

def event_access(user,event):
    return event.opportunity.owner_id==user.pk or Application.objects.filter(opportunity=event.opportunity,volunteer=user,status='accepted').exists()

@login_required
def calendar(request):
    qs=Event.objects.filter(Q(opportunity__owner=request.user)|Q(opportunity__applications__volunteer=request.user,opportunity__applications__status='accepted')).distinct().select_related('opportunity')
    today=timezone.localdate()
    try:
        year,month=[int(x) for x in request.GET.get('month','').split('-')]
        first=date(year,month,1)
    except (ValueError,TypeError):
        first=today.replace(day=1)
    last=date(first.year,first.month,pycal.monthrange(first.year,first.month)[1])
    month_events=[e for e in qs.filter(starts__date__lte=last,ends__date__gte=first)]
    weeks=[]
    for week in pycal.Calendar(firstweekday=0).monthdatescalendar(first.year,first.month):
        weeks.append([{'date':d,'in_month':d.month==first.month,'today':d==today,'events':[e for e in month_events if timezone.localtime(e.starts).date()<=d<=timezone.localtime(e.ends).date()]} for d in week])
    prev=(first-timedelta(days=1)).replace(day=1); nxt=last+timedelta(days=1)
    upcoming=qs.filter(ends__gte=timezone.now()).order_by('starts')[:20]
    return render(request,'community/calendar.html',{'events':upcoming,'weeks':weeks,'month':first,'prev':prev.strftime('%Y-%m'),'next':nxt.strftime('%Y-%m'),'weekdays':['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],'owned':Opportunity.objects.filter(owner=request.user)})

@login_required
def edit_event(request,slug,pk=None):
    if not permitted(request): return gate(request)
    o=get_object_or_404(Opportunity,slug=slug,owner=request.user)
    e=get_object_or_404(Event,pk=pk,opportunity=o) if pk else None
    f=EventForm(request.POST if request.method=='POST' else None,instance=e)
    if request.method=='POST' and f.is_valid():
        obj=f.save(commit=False); obj.opportunity=o; obj.save()
        for a in o.applications.filter(status='accepted').select_related('volunteer'):
            notify(a.volunteer,('Event updated: ' if e else 'New event: ')+obj.title,reverse('event_detail',args=[obj.pk]))
        messages.success(request,'Event updated.' if e else 'Event created. Accepted volunteers have been notified.')
        return redirect('event_detail',pk=obj.pk)
    return render(request,'form.html',{'form':f,'title':('Edit event' if e else 'Create event')+' — '+o.title,'action':'Save event'})

@login_required
def event_detail(request,pk):
    event=get_object_or_404(Event,pk=pk)
    if not event_access(request.user,event): return HttpResponseForbidden()
    owner=event.opportunity.owner_id==request.user.pk
    now=timezone.now()
    status='Cancelled' if event.cancelled else 'Completed' if event.ends<now else 'In progress' if event.starts<=now else 'Upcoming'
    checked_in=Attendance.objects.filter(event=event,volunteer=request.user).exists()
    checkin_open=not event.cancelled and event.starts-timedelta(minutes=30)<=now<=event.ends+timedelta(minutes=30)
    return render(request,'community/event.html',{'event':event,'owner':owner,'status':status,'checked_in':checked_in,'checkin_open':checkin_open,'attendance':Attendance.objects.filter(event=event).select_related('volunteer') if owner else None})

@login_required
@require_POST
def cancel_event(request,pk):
    if not permitted(request): return gate(request)
    event=get_object_or_404(Event,pk=pk,opportunity__owner=request.user)
    if not event.cancelled:
        event.cancelled=True; event.save(update_fields=['cancelled'])
        for a in event.opportunity.applications.filter(status='accepted').select_related('volunteer'):
            notify(a.volunteer,'Event cancelled: '+event.title,reverse('event_detail',args=[event.pk]),email=True)
    return redirect('event_detail',pk=pk)

@login_required
@require_GET
def qr(request,pk):
    import qrcode
    event=get_object_or_404(Event,pk=pk,opportunity__owner=request.user,cancelled=False)
    target=request.build_absolute_uri(reverse('checkin',args=[event.pk,event.checkin_key]))
    img=qrcode.make(target); buf=BytesIO(); img.save(buf,format='PNG')
    response=HttpResponse(buf.getvalue(),content_type='image/png'); response['Cache-Control']='private, no-store'; return response

@login_required
def checkin(request,pk,key):
    if not permitted(request): return gate(request)
    event=get_object_or_404(Event,pk=pk,checkin_key=key,cancelled=False)
    if not Application.objects.filter(opportunity=event.opportunity,volunteer=request.user,status='accepted').exists():
        return render(request,'community/checkin.html',{'event':event,'error':'Only volunteers whose application for this opportunity was accepted can check in.'},status=403)
    now=timezone.now()
    if not event.starts-timedelta(minutes=30)<=now<=event.ends+timedelta(minutes=30):
        return render(request,'community/checkin.html',{'event':event,'error':'Check-in opens 30 minutes before the event starts and closes 30 minutes after it ends.'},status=403)
    if request.method=='POST':
        _,created=Attendance.objects.get_or_create(event=event,volunteer=request.user)
        if created:
            messages.success(request,'Attendance recorded. Thank you for showing up!')
            notify(event.opportunity.owner,f'{display_name(request.user)} checked in to {event.title}.',reverse('event_detail',args=[event.pk]))
        else: messages.info(request,'You have already checked in to this event.')
        return redirect('event_detail',pk=pk)
    return render(request,'community/checkin.html',{'event':event})

@login_required
def inbox(request):
    apps=list(Application.objects.filter(Q(volunteer=request.user)|Q(opportunity__owner=request.user)).exclude(opportunity__owner=None).exclude(opportunity__owner__is_active=False).select_related('opportunity','volunteer','opportunity__owner').annotate(message_count=Count('conversation_messages')).order_by('-created'))
    unread_links=set(Notification.objects.filter(user=request.user,read=False,link__startswith='/community/inbox/').values_list('link',flat=True))
    for a in apps:
        other=a.opportunity.owner if a.volunteer_id==request.user.pk else a.volunteer
        a.other_name=display_name(other); a.unread=reverse('conversation',args=[a.pk]) in unread_links
    return render(request,'community/inbox.html',{'apps':apps})

@login_required
def conversation(request,pk):
    a=get_object_or_404(Application.objects.filter(Q(volunteer=request.user)|Q(opportunity__owner=request.user)).exclude(opportunity__owner=None),pk=pk)
    f=MessageForm(request.POST if request.method=='POST' else None)
    if request.method=='POST' and f.is_valid():
        if not permitted(request): return gate(request)
        msg=f.save(commit=False); msg.sender=request.user; msg.application=a; msg.save()
        receiver=a.opportunity.owner if request.user==a.volunteer else a.volunteer
        notify(receiver,f'New message from {display_name(request.user)} about {a.opportunity.title}',reverse('conversation',args=[a.pk])); return redirect('conversation',pk=pk)
    # Opening a conversation marks its message notifications as read.
    Notification.objects.filter(user=request.user,read=False,link=reverse('conversation',args=[a.pk])).update(read=True)
    other=a.opportunity.owner if request.user==a.volunteer else a.volunteer
    return render(request,'community/conversation.html',{'a':a,'form':f,'other':other,'other_name':display_name(other),'thread':a.conversation_messages.select_related('sender'),'can_send':permitted(request)})

@require_GET
def manifest(request):
    from django.templatetags.static import static
    return JsonResponse({'name':'Voluntr','short_name':'Voluntr','start_url':'/','scope':'/','display':'standalone','theme_color':'#205b44','background_color':'#faf9f4','icons':[{'src':static('img/icon-512.png'),'sizes':'512x512','type':'image/png'},{'src':static('img/apple-touch-icon.png'),'sizes':'180x180','type':'image/png'}]},content_type='application/manifest+json')
@require_GET
def worker(request):
    # Never cache private pages or authenticated responses.
    response=HttpResponse("""const CACHE='voluntr-offline-v1'; self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.add('/offline/')))); self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('voluntr-')&&k!==CACHE).map(k=>caches.delete(k)))))); self.addEventListener('fetch',e=>{if(e.request.mode==='navigate'&&e.request.method==='GET')e.respondWith(fetch(e.request).catch(()=>caches.match('/offline/')))});""",content_type='application/javascript')
    response['Cache-Control']='no-cache'; return response

def robots(request):
    return HttpResponse('User-agent: *\nDisallow: /admin/\nDisallow: /dashboard/\nDisallow: /community/inbox/\nDisallow: /community/notifications/\nDisallow: /community/calendar/\nDisallow: /community/impact/\nDisallow: /profile/\nDisallow: /activity/\nDisallow: /organizer/\nDisallow: /login/\nDisallow: /join/\nSitemap: '+request.build_absolute_uri('/sitemap.xml')+'\n',content_type='text/plain')
