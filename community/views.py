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
from .services import email_verified, notify

def permitted(request):
    return request.user.is_staff or email_verified(request.user)

def gate(request):
    messages.error(request,'Verify your email on the dashboard first.'); return redirect('dashboard')

def is_organizer(user): return Profile.objects.filter(user=user,role='organizer').exists()

def organizations(request):
    return render(request,'community/organizations.html',{'organizations':Organization.objects.filter(public=True).order_by('name')})

def organization(request,slug):
    org=get_object_or_404(Organization,slug=slug,public=True)
    return render(request,'community/organization.html',{'org':org,'listings':Opportunity.objects.filter(owner=org.owner,published=True)})

@login_required
def edit_organization(request):
    if not is_organizer(request.user): return HttpResponseForbidden()
    if not permitted(request): return gate(request)
    org=Organization.objects.filter(owner=request.user).first()
    f=OrganizationForm(request.POST or None,instance=org)
    if request.method=='POST' and f.is_valid():
        obj=f.save(commit=False); obj.owner=request.user
        if not org: obj.slug=slugify(obj.name)[:100]+'-'+uuid4().hex[:8]
        if f.has_changed(): obj.verified=False
        obj.save(); messages.success(request,'Organization profile saved. Verification is subject to administrator review.'); return redirect('dashboard')
    return render(request,'form.html',{'form':f,'title':'Organization profile','action':'Save profile'})

@login_required
def location(request,slug):
    if not permitted(request): return gate(request)
    o=get_object_or_404(Opportunity,slug=slug,owner=request.user)
    f=LocationForm(request.POST or None,instance=Location.objects.filter(opportunity=o).first())
    if request.method=='POST' and f.is_valid():
        obj=f.save(commit=False); obj.opportunity=o; obj.save(); return redirect('dashboard')
    return render(request,'form.html',{'form':f,'title':'Set public map location (use a meeting point, not a private address)','action':'Save location'})

CITY_POINTS={'Mumbai':[19.076,72.8777],'Pune':[18.5204,73.8567],'Delhi':[28.6139,77.2090],'Bengaluru':[12.9716,77.5946],'Chennai':[13.0827,80.2707],'Thane':[19.2183,72.9781]}
def map_page(request):
    points=[]
    for o in Opportunity.objects.filter(published=True).filter(Q(deadline__isnull=True)|Q(deadline__gte=timezone.localdate())).exclude(mode='Remote').select_related('map_location')[:500]:
        loc=getattr(o,'map_location',None)
        coords=[loc.latitude,loc.longitude] if loc else CITY_POINTS.get(o.city) if o.demo else None
        if coords: points.append({'title':o.title,'city':o.city,'coords':coords,'approximate':loc.approximate if loc else True,'url':reverse('detail',args=[o.slug])})
    return render(request,'community/map.html',{'points':points})

@login_required
def impact(request):
    organizer=is_organizer(request.user)
    qs=Hours.objects.filter(approved=True,application__opportunity__owner=request.user) if organizer else Hours.objects.filter(approved=True,application__volunteer=request.user)
    total=qs.aggregate(s=Sum('hours'))['s'] or 0
    apps=Application.objects.filter(opportunity__owner=request.user) if organizer else Application.objects.filter(volunteer=request.user)
    breakdown=qs.values('application__opportunity__category').annotate(hours=Sum('hours')).order_by('-hours')
    badges=[]
    if not organizer:
        for target,label in [(1,'First steps'),(10,'Community contributor'),(25,'Changemaker'),(50,'Impact champion'),(100,'Century of service')]:
            badges.append({'label':label,'target':target,'earned':total>=target})
    return render(request,'community/impact.html',{'total':total,'apps':apps.count(),'accepted':apps.filter(status='accepted').count(),'people':apps.filter(status='accepted').values('volunteer').distinct().count(),'breakdown':breakdown,'badges':badges,'organizer':organizer})

@login_required
def notifications(request):
    return render(request,'community/notifications.html',{'items':Notification.objects.filter(user=request.user)[:100]})
@login_required
@require_POST
def mark_read(request):
    Notification.objects.filter(user=request.user,read=False).update(read=True); return redirect('notifications')

def event_access(user,event):
    return event.opportunity.owner_id==user.pk or Application.objects.filter(opportunity=event.opportunity,volunteer=user,status='accepted').exists()

@login_required
def calendar(request):
    qs=Event.objects.filter(Q(opportunity__owner=request.user)|Q(opportunity__applications__volunteer=request.user,opportunity__applications__status='accepted')).distinct()
    return render(request,'community/calendar.html',{'events':qs,'owned':Opportunity.objects.filter(owner=request.user)})

@login_required
def edit_event(request,slug,pk=None):
    if not permitted(request): return gate(request)
    o=get_object_or_404(Opportunity,slug=slug,owner=request.user)
    e=get_object_or_404(Event,pk=pk,opportunity=o) if pk else None
    f=EventForm(request.POST or None,instance=e)
    if request.method=='POST' and f.is_valid():
        obj=f.save(commit=False); obj.opportunity=o; obj.save()
        for a in o.applications.filter(status='accepted').select_related('volunteer'):
            notify(a.volunteer,('Event updated: ' if e else 'New event: ')+obj.title,reverse('event_detail',args=[obj.pk]))
        return redirect('event_detail',pk=obj.pk)
    return render(request,'form.html',{'form':f,'title':'Edit event' if e else 'Create event','action':'Save event'})

@login_required
def event_detail(request,pk):
    event=get_object_or_404(Event,pk=pk)
    if not event_access(request.user,event): return HttpResponseForbidden()
    owner=event.opportunity.owner_id==request.user.pk
    return render(request,'community/event.html',{'event':event,'owner':owner,'attendance':Attendance.objects.filter(event=event).select_related('volunteer') if owner else None})

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
    if not Application.objects.filter(opportunity=event.opportunity,volunteer=request.user,status='accepted').exists(): return HttpResponseForbidden()
    now=timezone.now()
    if not event.starts-timedelta(minutes=30)<=now<=event.ends+timedelta(minutes=30): return HttpResponseForbidden('Check-in opens 30 minutes before the event and closes 30 minutes after.')
    if request.method=='POST':
        Attendance.objects.get_or_create(event=event,volunteer=request.user); messages.success(request,'Attendance recorded.'); return redirect('event_detail',pk=pk)
    return render(request,'community/checkin.html',{'event':event})

@login_required
def inbox(request):
    apps=Application.objects.filter(Q(volunteer=request.user)|Q(opportunity__owner=request.user)).exclude(opportunity__owner=None).select_related('opportunity','volunteer')
    return render(request,'community/inbox.html',{'apps':apps})

@login_required
def conversation(request,pk):
    a=get_object_or_404(Application.objects.filter(Q(volunteer=request.user)|Q(opportunity__owner=request.user)).exclude(opportunity__owner=None),pk=pk)
    f=MessageForm(request.POST or None)
    if request.method=='POST' and f.is_valid():
        if not permitted(request): return gate(request)
        msg=f.save(commit=False); msg.sender=request.user; msg.application=a; msg.save()
        receiver=a.opportunity.owner if request.user==a.volunteer else a.volunteer
        notify(receiver,'New message about '+a.opportunity.title,reverse('conversation',args=[a.pk])); return redirect('conversation',pk=pk)
    return render(request,'community/conversation.html',{'a':a,'form':f,'thread':a.conversation_messages.select_related('sender')})

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
    return HttpResponse('User-agent: *\nDisallow: /admin/\nDisallow: /dashboard/\nDisallow: /community/inbox/\nDisallow: /community/notifications/\nDisallow: /community/calendar/\nDisallow: /community/impact/\nDisallow: /accounts/\nSitemap: '+request.build_absolute_uri('/sitemap.xml')+'\n',content_type='text/plain')
