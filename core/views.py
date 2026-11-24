from django import forms
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q,Sum
from django.db import transaction
from django.http import HttpResponseForbidden,JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.text import slugify
from django.core.paginator import Paginator
from uuid import uuid4
from .models import *
from .forms import *
def active(): return Opportunity.objects.filter(published=True).filter(Q(deadline__isnull=True)|Q(deadline__gte=timezone.localdate()))
def profile(user): return Profile.objects.get_or_create(user=user)[0]
def home(request): return render(request,'home.html',{'opportunities':active()[:3],'articles':Article.objects.filter(published=True)[:3],'categories':Opportunity.CATEGORIES})
def explore(request):
    qs=active(); q=request.GET.get('q','').strip(); category=request.GET.get('category',''); city=request.GET.get('city',''); mode=request.GET.get('mode','')
    if q: qs=qs.filter(Q(title__icontains=q)|Q(description__icontains=q)|Q(skills__icontains=q)|Q(organization__icontains=q))
    if category: qs=qs.filter(category=category)
    if city: qs=qs.filter(city__icontains=city)
    if mode: qs=qs.filter(mode=mode)
    if request.GET.get('sort')=='title': qs=qs.order_by('title')
    page=Paginator(qs,9).get_page(request.GET.get('page')); params=request.GET.copy(); params.pop('page',None)
    return render(request,'explore.html',{'page':page,'categories':Opportunity.CATEGORIES,'params':params.urlencode()})
def detail(request,slug):
    o=get_object_or_404(Opportunity,published=True,slug=slug)
    saved=request.user.is_authenticated and Bookmark.objects.filter(user=request.user,opportunity=o).exists()
    return render(request,'detail.html',{'o':o,'saved':saved,'closed':not active().filter(pk=o.pk).exists()})
def signup(request):
    f=Signup(request.POST or None)
    if request.method=='POST' and f.is_valid():
        with transaction.atomic():
            u=f.save(); Profile.objects.create(user=u,role=f.cleaned_data['role'])
        login(request,u); return redirect('profile')
    return render(request,'form.html',{'form':f,'title':'Join the community','action':'Create account'})
def form_page(request,form,title,action,success):
    if request.method=='POST' and form.is_valid():
        form.save(); messages.success(request,'Saved successfully.'); return redirect(success)
    return render(request,'form.html',{'form':form,'title':title,'action':action})
@login_required
def edit_profile(request): return form_page(request,ProfileForm(request.POST or None,instance=profile(request.user)),'Your volunteer profile','Save profile','dashboard')
@login_required
def apply(request,slug):
    o=get_object_or_404(active(),slug=slug)
    if profile(request.user).role!='volunteer': return HttpResponseForbidden('Volunteer account required.')
    if Application.objects.filter(volunteer=request.user,opportunity=o).exists(): messages.info(request,'You already applied.'); return redirect('dashboard')
    f=ApplicationForm(request.POST or None)
    if request.method=='POST' and f.is_valid():
        Application.objects.get_or_create(volunteer=request.user,opportunity=o,defaults={'motivation':f.cleaned_data['motivation']}); messages.success(request,'Application submitted.'); return redirect('dashboard')
    return render(request,'form.html',{'form':f,'title':'Apply: '+o.title,'action':'Submit application'})
@login_required
@require_POST
def bookmark(request,slug):
    o=get_object_or_404(Opportunity,published=True,slug=slug); b,created=Bookmark.objects.get_or_create(user=request.user,opportunity=o)
    if not created: b.delete()
    return redirect('detail',slug=slug)
@login_required
def dashboard(request):
    p=profile(request.user); apps=Application.objects.filter(volunteer=request.user).select_related('opportunity'); saved=Opportunity.objects.filter(bookmark__user=request.user,published=True)
    words={w.strip().lower() for w in (p.interests+','+p.skills).replace(';',',').split(',') if w.strip()}
    def score(o): return sum(w in (o.category+' '+o.skills+' '+o.title).lower() for w in words)+int(bool(p.city and p.city.lower()==o.city.lower()))
    matches=sorted(active()[:200],key=score,reverse=True)[:3]
    return render(request,'dashboard.html',{'p':p,'apps':apps,'saved':saved,'matches':matches,'total':Hours.objects.filter(application__volunteer=request.user,approved=True).aggregate(s=Sum('hours'))['s'] or 0,'owned':Opportunity.objects.filter(owner=request.user),'incoming':Application.objects.filter(opportunity__owner=request.user).select_related('volunteer','opportunity'),'logs':Hours.objects.filter(application__volunteer=request.user),'review_logs':Hours.objects.filter(application__opportunity__owner=request.user)})
@login_required
@require_POST
def withdraw(request,pk):
    with transaction.atomic():
        a=get_object_or_404(Application,pk=pk,volunteer=request.user)
        Opportunity.objects.select_for_update().get(pk=a.opportunity_id)
        a.refresh_from_db()
        if a.status=='pending': a.status='withdrawn'; a.save(update_fields=['status'])
    return redirect('dashboard')
@login_required
def publish(request):
    if profile(request.user).role!='organizer': return HttpResponseForbidden('Organizer account required.')
    f=OpportunityForm(request.POST or None)
    if request.method=='POST' and f.is_valid():
        o=f.save(commit=False); o.owner=request.user; o.image='img/'+{'Education': 'education', 'Community': 'community', 'Environment': 'environment', 'Animals': 'animals', 'Food security': 'food-security', 'Health': 'health', 'Sports': 'sports', 'Disaster relief': 'disaster-relief', 'Technology': 'technology'}.get(o.category,'community')+'.svg'; o.slug=slugify(o.title)[:100]+'-'+uuid4().hex[:8]; o.save(); messages.success(request,'Submitted for administrator review.'); return redirect('dashboard')
    return render(request,'form.html',{'form':f,'title':'Create an opportunity','action':'Submit for review'})
@login_required
@require_POST
def review(request,pk):
    with transaction.atomic():
        a=get_object_or_404(Application,pk=pk,opportunity__owner=request.user)
        o=Opportunity.objects.select_for_update().get(pk=a.opportunity_id)
        a.refresh_from_db(); status=request.POST.get('status')
        if a.status=='pending' and status in ['accepted','declined']:
            if status=='accepted' and o.applications.filter(status='accepted').count()>=o.slots: messages.error(request,'No slots remaining.')
            else: a.status=status; a.save(update_fields=['status'])
    return redirect('dashboard')
@login_required
def log_hours(request,pk):
    a=get_object_or_404(Application,pk=pk,volunteer=request.user,status='accepted'); f=HoursForm(request.POST or None)
    if request.method=='POST' and f.is_valid():
        h=f.save(commit=False); h.application=a; h.save(); return redirect('dashboard')
    return render(request,'form.html',{'form':f,'title':'Log volunteer hours','action':'Submit hours'})
@login_required
@require_POST
def approve_hours(request,pk):
    h=get_object_or_404(Hours,pk=pk,application__opportunity__owner=request.user,application__status='accepted'); h.approved=True; h.save(update_fields=['approved']); return redirect('dashboard')
def blog(request):
    qs=Article.objects.filter(published=True).order_by('-created')
    q=request.GET.get('q','').strip(); category=request.GET.get('category','')
    if q: qs=qs.filter(Q(title__icontains=q)|Q(summary__icontains=q)|Q(body__icontains=q))
    if category: qs=qs.filter(category=category)
    return render(request,'blog.html',{'articles':qs,'categories':Article.objects.filter(published=True).order_by('category').values_list('category',flat=True).distinct()})
def article(request,slug): return render(request,'article.html',{'article':get_object_or_404(Article,published=True,slug=slug)})
def contact(request): return form_page(request,ContactForm(request.POST or None),'Get in touch','Send message','contact')
@require_POST
def subscribe(request):
    f=SubscribeForm(request.POST)
    if f.is_valid(): Subscriber.objects.get_or_create(email=f.cleaned_data['email'].lower()); messages.success(request,'You are on the newsletter list.')
    else: messages.error(request,'Enter a valid email.')
    return redirect('home')
def about(request): return render(request,'about.html')
def api(request): return JsonResponse({'opportunities':list(active().values('title','slug','organization','category','city','mode','summary','commitment','demo')[:100])})
def health(request): return JsonResponse({'status':'ok'})

@login_required
def report_listing(request,slug):
    o=get_object_or_404(Opportunity,published=True,slug=slug)
    f=forms.Form(request.POST or None)
    f.fields['reason']=forms.CharField(max_length=2000, min_length=10,widget=forms.Textarea)
    if request.method=='POST' and f.is_valid():
        ListingReport.objects.create(reporter=request.user,opportunity=o,reason=f.cleaned_data['reason'])
        messages.success(request,'Report sent to moderation.'); return redirect('detail',slug=slug)
    return render(request,'form.html',{'form':f,'title':'Report listing','action':'Send report'})

@login_required
def certificate(request,pk):
    a=get_object_or_404(Application,pk=pk,volunteer=request.user,status='accepted')
    total=Hours.objects.filter(application=a,approved=True).aggregate(s=Sum('hours'))['s']
    if not total: return HttpResponseForbidden('Approved hours are required.')
    return render(request,'certificate.html',{'a':a,'total':total})

@login_required
def export_applications(request):
    import csv
    from django.http import HttpResponse
    if profile(request.user).role!='organizer': return HttpResponseForbidden()
    response=HttpResponse(content_type='text/csv'); response['Content-Disposition']='attachment; filename="applications.csv"'
    writer=csv.writer(response); writer.writerow(['Opportunity','Volunteer','Status','Submitted'])
    def safe(s):
        s=str(s); return "'"+s if s.lstrip().startswith(('=','+','-','@')) or s.startswith(('\t','\r','\n')) else s
    for a in Application.objects.filter(opportunity__owner=request.user).select_related('opportunity','volunteer'):
        writer.writerow([safe(a.opportunity.title),safe(a.volunteer.username),a.status,a.created.isoformat()])
    return response

@login_required
def activity(request):
    apps=Application.objects.filter(Q(volunteer=request.user)|Q(opportunity__owner=request.user)).select_related('opportunity','volunteer').order_by('-created')
    return render(request,'activity.html',{'apps':apps[:100]})
