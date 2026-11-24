from django import forms
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q,Sum,Count
from django.db import transaction
from django.http import HttpResponseForbidden,JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.text import slugify
from django.core.paginator import Paginator
from uuid import uuid4
from .models import *
from .forms import *
from community.models import Organization
from community.services import verification, email_verified, can_act, application_changed, application_received, notify, display_name
from community.auth import report as report_verification
from community.models import Event, Attendance, Notification
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
def active(): return Opportunity.objects.filter(published=True,closed=False).filter(Q(deadline__isnull=True)|Q(deadline__gte=timezone.localdate()))
def profile(user): return Profile.objects.get_or_create(user=user)[0]
def home(request): return render(request,'home.html',{'opportunities':active()[:3],'articles':Article.objects.filter(published=True)[:3],'categories':Opportunity.CATEGORIES})
def explore(request):
    qs=active(); q=request.GET.get('q','').strip(); category=request.GET.get('category',''); city=request.GET.get('city',''); mode=request.GET.get('mode','')
    if q: qs=qs.filter(Q(title__icontains=q)|Q(summary__icontains=q)|Q(description__icontains=q)|Q(skills__icontains=q)|Q(organization__icontains=q)|Q(category__icontains=q)|Q(city__icontains=q))
    if category: qs=qs.filter(category=category)
    if city: qs=qs.filter(city__icontains=city)
    if mode: qs=qs.filter(mode=mode)
    if request.GET.get('sort')=='title': qs=qs.order_by('title')
    page=Paginator(qs,9).get_page(request.GET.get('page')); params=request.GET.copy(); params.pop('page',None)
    cities=active().order_by('city').values_list('city',flat=True).distinct()
    return render(request,'explore.html',{'page':page,'categories':Opportunity.CATEGORIES,'params':params.urlencode(),'cities':cities})
def detail(request,slug):
    o=get_object_or_404(Opportunity,published=True,slug=slug)
    saved=request.user.is_authenticated and Bookmark.objects.filter(user=request.user,opportunity=o).exists()
    applied=request.user.is_authenticated and Application.objects.filter(volunteer=request.user,opportunity=o).exists()
    related=active().filter(category=o.category).exclude(pk=o.pk)[:3]
    return render(request,'detail.html',{'o':o,'saved':saved,'applied':applied,'related':related,'closed':not active().filter(pk=o.pk).exists(),'org_profile':Organization.objects.filter(owner_id=o.owner_id,public=True).first() if o.owner_id else None})
def signup(request):
    f=Signup(request.POST if request.method=='POST' else None)
    if request.method=='POST' and f.is_valid():
        with transaction.atomic():
            u=f.save(); Profile.objects.create(user=u,role=f.cleaned_data['role'])
        login(request,u,backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request,f'Welcome to Voluntr, {display_name(u)}! Your account has been created.')
        report_verification(request,verification(request,u)); return redirect('profile')
    return render(request,'signup.html',{'form':f})
def form_page(request,form,title,action,success,message='Saved successfully.',intro=''):
    if request.method=='POST' and form.is_valid():
        form.save(); messages.success(request,message); return redirect(success)
    return render(request,'form.html',{'form':form,'title':title,'action':action,'intro':intro})
@login_required
def edit_profile(request):
    p=profile(request.user)
    intro=f'Signed in as {request.user.email or request.user.username}. ' + ('Your email is verified.' if email_verified(request.user) else 'Your email is not verified yet.')
    return form_page(request,ProfileForm(request.POST if request.method=='POST' else None,instance=p),'Your organizer profile' if p.role=='organizer' else 'Your volunteer profile','Save profile','dashboard','Profile saved.',intro)
@login_required
def apply(request,slug):
    o=get_object_or_404(Opportunity,published=True,slug=slug)
    if not active().filter(pk=o.pk).exists():
        messages.error(request,'This opportunity is closed and no longer accepts applications.'); return redirect('detail',slug=slug)
    if profile(request.user).role!='volunteer' or o.owner_id==request.user.pk:
        messages.error(request,'Only volunteer accounts can apply to opportunities.'); return redirect('detail',slug=slug)
    if not can_act(request.user):
        messages.error(request,'Please verify your email address before applying. Use "Send verification email" above.'); return redirect('detail',slug=slug)
    if Application.objects.filter(volunteer=request.user,opportunity=o).exists(): messages.info(request,'You have already applied to this opportunity.'); return redirect('dashboard')
    f=ApplicationForm(request.POST if request.method=='POST' else None)
    if request.method=='POST' and f.is_valid():
        a,created=Application.objects.get_or_create(volunteer=request.user,opportunity=o,defaults={'motivation':f.cleaned_data['motivation']})
        if created: application_received(a)
        messages.success(request,f'Application submitted for {o.title}. The organizer will review it soon.'); return redirect('dashboard')
    return render(request,'form.html',{'form':f,'title':'Apply: '+o.title,'action':'Submit application'})
@login_required
@require_POST
def bookmark(request,slug):
    o=get_object_or_404(Opportunity,published=True,slug=slug); b,created=Bookmark.objects.get_or_create(user=request.user,opportunity=o)
    if not created: b.delete(); messages.info(request,'Removed from your saved opportunities.')
    else: messages.success(request,'Saved. Find it under "Saved for later" on your dashboard.')
    nxt=request.POST.get('next','')
    if nxt and url_has_allowed_host_and_scheme(nxt,allowed_hosts={request.get_host()},require_https=request.is_secure()): return redirect(nxt)
    return redirect('detail',slug=slug)
@login_required
def dashboard(request):
    p=profile(request.user); apps=Application.objects.filter(volunteer=request.user).select_related('opportunity'); saved=Opportunity.objects.filter(bookmark__user=request.user,published=True)
    words={w.strip().lower() for w in (p.interests+','+p.skills).replace(';',',').split(',') if w.strip()}
    def score(o): return sum(w in (o.category+' '+o.skills+' '+o.title).lower() for w in words)+int(bool(p.city and p.city.lower()==o.city.lower()))
    applied=set(apps.values_list('opportunity_id',flat=True))
    matches=sorted([o for o in active().exclude(owner=request.user)[:200] if o.pk not in applied],key=lambda o:(score(o),o.created),reverse=True)[:3]
    now=timezone.now()
    owned=Opportunity.objects.filter(owner=request.user).annotate(applicant_count=Count('applications'))
    incoming=Application.objects.filter(opportunity__owner=request.user).select_related('volunteer','opportunity').order_by('-created')
    if p.role=='organizer':
        events=Event.objects.filter(opportunity__owner=request.user)
    else:
        events=Event.objects.filter(opportunity__applications__volunteer=request.user,opportunity__applications__status='accepted').distinct()
    attended=set(Attendance.objects.filter(volunteer=request.user).values_list('event_id',flat=True))
    upcoming=events.filter(cancelled=False,ends__gte=now).select_related('opportunity').order_by('starts')[:5]
    completed=[e for e in events.filter(ends__lt=now).select_related('opportunity').order_by('-starts')[:10]]
    for e in completed: e.attended=e.pk in attended
    org=Organization.objects.filter(owner=request.user).first()
    if p.role=='organizer':
        steps=[('Verify your email',email_verified(request.user),'/dashboard/'),('Create your organization profile',bool(org),reverse('edit_organization')),('Make your organization public',bool(org and org.public),reverse('edit_organization')),('Post your first opportunity',Opportunity.objects.filter(owner=request.user).exists(),reverse('publish'))]
    else:
        steps=[('Verify your email',email_verified(request.user),'/dashboard/'),('Add your name',bool(request.user.get_full_name()),reverse('profile')),('Choose causes you care about',bool(p.interests),reverse('profile')),('Add your city and skills',bool(p.city and p.skills),reverse('profile')),('Apply to an opportunity',apps.exists(),reverse('explore'))]
    return render(request,'dashboard.html',{'p':p,'apps':apps.order_by('-created'),'saved':saved,'matches':matches,'total':Hours.objects.filter(application__volunteer=request.user,approved=True).aggregate(s=Sum('hours'))['s'] or 0,'owned':owned,'incoming':incoming,'incoming_pending':incoming.filter(status='pending').count(),'incoming_accepted':incoming.filter(status='accepted').count(),'org_hours':Hours.objects.filter(application__opportunity__owner=request.user,approved=True).aggregate(s=Sum('hours'))['s'] or 0,'logs':Hours.objects.filter(application__volunteer=request.user).select_related('application__opportunity'),'review_logs':Hours.objects.filter(application__opportunity__owner=request.user).select_related('application__volunteer','application__opportunity'),'upcoming':upcoming,'completed':completed,'organization':Organization.objects.filter(owner=request.user).first(),'display_name':display_name(request.user),'verified':email_verified(request.user),'steps':steps,'steps_done':sum(1 for _,d,_ in steps if d),'recent_notes':Notification.objects.filter(user=request.user)[:4],'pending_hours':Hours.objects.filter(application__opportunity__owner=request.user,approved=False,rejected=False).count()})
@login_required
@require_POST
def withdraw(request,pk):
    with transaction.atomic():
        a=get_object_or_404(Application,pk=pk,volunteer=request.user)
        Opportunity.objects.select_for_update().get(pk=a.opportunity_id)
        a.refresh_from_db()
        if a.status=='pending':
            a.status='withdrawn'; a.save(update_fields=['status']); application_changed(a)
            notify(a.opportunity.owner, 'Application withdrawn for '+a.opportunity.title, reverse('dashboard'))
    return redirect('dashboard')
@login_required
def publish(request):
    if profile(request.user).role!='organizer':
        messages.info(request,'Posting opportunities needs an organizer account. Create a separate organizer account to host opportunities.'); return redirect('dashboard')
    if request.method=='POST' and not can_act(request.user):
        messages.error(request,'Please verify your email address before submitting an opportunity.'); return redirect('dashboard')
    org=Organization.objects.filter(owner=request.user).first()
    f=OpportunityForm(request.POST if request.method=='POST' else None,initial={'organization':org.name} if org else None)
    if request.method=='POST' and f.is_valid():
        o=f.save(commit=False); o.owner=request.user; o.image='img/'+{'Education': 'education', 'Community': 'community', 'Environment': 'environment', 'Animals': 'animals', 'Food security': 'food-security', 'Health': 'health', 'Sports': 'sports', 'Disaster relief': 'disaster-relief', 'Technology': 'technology'}.get(o.category,'community')+'.svg'; o.slug=(slugify(o.title)[:100] or 'opportunity')+'-'+uuid4().hex[:8]; o.save(); messages.success(request,'Opportunity submitted. It will appear publicly once an administrator approves it.'); return redirect('dashboard')
    return render(request,'form.html',{'form':f,'title':'Create an opportunity','action':'Submit for review','intro':'New listings are reviewed by an administrator before they appear publicly.'})

@login_required
def edit_opportunity(request,slug):
    o=get_object_or_404(Opportunity,slug=slug,owner=request.user)
    f=OpportunityForm(request.POST if request.method=='POST' else None,instance=o)
    if request.method=='POST' and f.is_valid():
        if not can_act(request.user):
            messages.error(request,'Please verify your email address before editing listings.'); return redirect('dashboard')
        f.save(); messages.success(request,'Listing updated.'); return redirect('dashboard')
    return render(request,'form.html',{'form':f,'title':'Edit: '+o.title,'action':'Save changes'})

@login_required
@require_POST
def toggle_listing(request,slug):
    o=get_object_or_404(Opportunity,slug=slug,owner=request.user)
    o.closed=not o.closed; o.save(update_fields=['closed'])
    messages.success(request,f'"{o.title}" is now '+('closed to new applications.' if o.closed else 'open for applications again.'))
    return redirect('dashboard')
@login_required
@require_POST
def review(request,pk):
    with transaction.atomic():
        a=get_object_or_404(Application,pk=pk,opportunity__owner=request.user)
        o=Opportunity.objects.select_for_update().get(pk=a.opportunity_id)
        a.refresh_from_db(); status=request.POST.get('status')
        if a.status=='pending' and status in ['accepted','declined']:
            if status=='accepted' and o.applications.filter(status='accepted').count()>=o.slots: messages.error(request,'No slots remaining.')
            else:
                a.status=status; a.save(update_fields=['status']); application_changed(a)
                messages.success(request,f'{display_name(a.volunteer)} was '+('accepted.' if status=='accepted' else 'rejected.'))
    return redirect('dashboard')
@login_required
def log_hours(request,pk):
    a=get_object_or_404(Application,pk=pk,volunteer=request.user,status='accepted'); f=HoursForm(request.POST if request.method=='POST' else None)
    if request.method=='POST' and f.is_valid():
        h=f.save(commit=False); h.application=a; h.save()
        notify(a.opportunity.owner,f'{display_name(request.user)} submitted {h.hours} hours for {a.opportunity.title}.',reverse('dashboard'))
        messages.success(request,'Hours submitted for organizer approval.'); return redirect('dashboard')
    return render(request,'form.html',{'form':f,'title':'Log volunteer hours','action':'Submit hours','intro':'For '+a.opportunity.title+'. Hours count towards your total once the organizer approves them.'})
@login_required
@require_POST
def approve_hours(request,pk):
    h=get_object_or_404(Hours,pk=pk,application__opportunity__owner=request.user,application__status='accepted')
    if not h.approved:
        h.approved=True; h.rejected=False; h.save(update_fields=['approved','rejected']); notify(h.application.volunteer,f'Your {h.hours} volunteer hours for {h.application.opportunity.title} were approved.',reverse('impact'))
        messages.success(request,'Hours approved.')
    return redirect('dashboard')
@login_required
@require_POST
def reject_hours(request,pk):
    h=get_object_or_404(Hours,pk=pk,application__opportunity__owner=request.user)
    if not h.approved and not h.rejected:
        h.rejected=True; h.save(update_fields=['rejected']); notify(h.application.volunteer,f'Your {h.hours} hour submission for {h.application.opportunity.title} was not approved.',reverse('dashboard'))
        messages.info(request,'Hours rejected. They will not count towards the volunteer total.')
    return redirect('dashboard')
def blog(request):
    qs=Article.objects.filter(published=True).order_by('-created')
    q=request.GET.get('q','').strip(); category=request.GET.get('category','')
    if q: qs=qs.filter(Q(title__icontains=q)|Q(summary__icontains=q)|Q(body__icontains=q))
    if category: qs=qs.filter(category=category)
    return render(request,'blog.html',{'articles':qs,'categories':Article.objects.filter(published=True).order_by('category').values_list('category',flat=True).distinct()})
def article(request,slug):
    article=get_object_or_404(Article,published=True,slug=slug)
    related=list(Article.objects.filter(published=True,category=article.category).exclude(pk=article.pk).order_by('-created')[:3])
    if len(related)<3: related+=list(Article.objects.filter(published=True).exclude(pk__in=[article.pk]+[a.pk for a in related]).order_by('-created')[:3-len(related)])
    return render(request,'article.html',{'article':article,'related':related})
def contact(request): return form_page(request,ContactForm(request.POST if request.method=='POST' else None,initial={'name':display_name(request.user),'email':request.user.email} if request.user.is_authenticated else None),'Get in touch','Send message','contact','Thanks for reaching out! We received your message and will reply by email.','Questions, partnership ideas or feedback — we would love to hear from you.')
@require_POST
def subscribe(request):
    f=SubscribeForm(request.POST)
    if f.is_valid():
        _,created=Subscriber.objects.get_or_create(email=f.cleaned_data['email'].lower())
        if created: messages.success(request,'Thanks for subscribing! You are on the newsletter list.')
        else: messages.info(request,'This email is already subscribed.')
    else: messages.error(request,'Enter a valid email address to subscribe.')
    back=request.META.get('HTTP_REFERER','')
    if back and url_has_allowed_host_and_scheme(back,allowed_hosts={request.get_host()},require_https=request.is_secure()): return redirect(back)
    return redirect('home')
def about(request): return render(request,'about.html')
def api(request): return JsonResponse({'opportunities':list(active().values('title','slug','organization','category','city','mode','summary','commitment','demo')[:100])})
def health(request): return JsonResponse({'status':'ok'})

@login_required
def report_listing(request,slug):
    o=get_object_or_404(Opportunity,published=True,slug=slug)
    f=forms.Form(request.POST if request.method=='POST' else None)
    f.fields['reason']=forms.CharField(max_length=2000, min_length=10,widget=forms.Textarea)
    if request.method=='POST' and f.is_valid():
        ListingReport.objects.create(reporter=request.user,opportunity=o,reason=f.cleaned_data['reason'])
        messages.success(request,'Report sent to moderation.'); return redirect('detail',slug=slug)
    return render(request,'form.html',{'form':f,'title':'Report listing','action':'Send report'})

@login_required
def certificate(request,pk):
    a=get_object_or_404(Application,pk=pk,volunteer=request.user,status='accepted')
    total=Hours.objects.filter(application=a,approved=True).aggregate(s=Sum('hours'))['s']
    if not total:
        messages.info(request,'A certificate becomes available once the organizer approves at least one of your hour submissions.'); return redirect('dashboard')
    return render(request,'certificate.html',{'a':a,'total':total})

@login_required
def export_applications(request):
    import csv
    from django.http import HttpResponse
    if profile(request.user).role!='organizer': messages.info(request,'Only organizers can export applications.'); return redirect('dashboard')
    response=HttpResponse(content_type='text/csv'); response['Content-Disposition']='attachment; filename="applications.csv"'
    writer=csv.writer(response); writer.writerow(['Opportunity','Volunteer','Name','Email','Status','Submitted'])
    def safe(s):
        s=str(s); return "'"+s if s.lstrip().startswith(('=','+','-','@')) or s.startswith(('\t','\r','\n')) else s
    for a in Application.objects.filter(opportunity__owner=request.user).select_related('opportunity','volunteer'):
        writer.writerow([safe(a.opportunity.title),safe(a.volunteer.username),safe(a.volunteer.get_full_name()),safe(a.volunteer.email),a.get_status_display(),timezone.localtime(a.created).strftime('%Y-%m-%d %H:%M')])
    return response

@login_required
def activity(request):
    apps=Application.objects.filter(Q(volunteer=request.user)|Q(opportunity__owner=request.user)).select_related('opportunity','volunteer').order_by('-created')
    return render(request,'activity.html',{'apps':apps[:100]})
