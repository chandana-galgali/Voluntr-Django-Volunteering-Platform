from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator,MaxValueValidator
class Profile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    city=models.CharField(max_length=100,blank=True)
    skills=models.TextField(blank=True)
    interests=models.CharField(max_length=250,blank=True,help_text='Comma-separated causes')
    role=models.CharField(max_length=20,choices=[('volunteer','Volunteer'),('organizer','Organizer')],default='volunteer')
    def __str__(self): return f'{self.user} ({self.role})'
    bio=models.TextField(max_length=1000,blank=True)
    def interest_list(self): return [x.strip() for x in self.interests.split(',') if x.strip()]
class Opportunity(models.Model):
    CATEGORIES=[(x,x) for x in ['Education','Environment','Animals','Food security','Community','Health','Disaster relief','Technology','Sports']]
    title=models.CharField(max_length=160)
    slug=models.SlugField(unique=True)
    organization=models.CharField(max_length=150)
    owner=models.ForeignKey(User,null=True,blank=True,on_delete=models.SET_NULL)
    category=models.CharField(max_length=40,choices=CATEGORIES)
    city=models.CharField(max_length=100)
    mode=models.CharField(max_length=20,choices=[('On-site','On-site'),('Remote','Remote'),('Hybrid','Hybrid')],default='On-site')
    summary=models.CharField(max_length=250)
    description=models.TextField()
    skills=models.CharField(max_length=250,blank=True)
    commitment=models.CharField(max_length=100)
    slots=models.PositiveIntegerField(default=10,validators=[MinValueValidator(1)])
    deadline=models.DateField(null=True,blank=True)
    image=models.CharField(max_length=150,default='img/hero.jpg')
    published=models.BooleanField(default=False)
    closed=models.BooleanField(default=False,help_text='Closed listings stay visible but no longer accept applications.')
    demo=models.BooleanField(default=False)
    created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created']; verbose_name_plural='opportunities'
    def __str__(self): return self.title
class Application(models.Model):
    volunteer=models.ForeignKey(User,on_delete=models.CASCADE)
    opportunity=models.ForeignKey(Opportunity,on_delete=models.CASCADE,related_name='applications')
    motivation=models.TextField()
    status=models.CharField(max_length=20,choices=[('pending','Pending'),('accepted','Accepted'),('declined','Rejected'),('withdrawn','Withdrawn')],default='pending')
    created=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['volunteer','opportunity'],name='unique_application')]; ordering=['-created']
    def __str__(self): return f'{self.volunteer} → {self.opportunity}'
class Bookmark(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    opportunity=models.ForeignKey(Opportunity,on_delete=models.CASCADE)
    class Meta: constraints=[models.UniqueConstraint(fields=['user','opportunity'],name='unique_bookmark')]
    def __str__(self): return f'{self.user} ★ {self.opportunity}'
class Hours(models.Model):
    application=models.ForeignKey(Application,on_delete=models.CASCADE)
    date=models.DateField()
    hours=models.DecimalField(max_digits=4,decimal_places=1,validators=[MinValueValidator(0.5),MaxValueValidator(24)])
    note=models.CharField(max_length=250)
    approved=models.BooleanField(default=False)
    rejected=models.BooleanField(default=False)
    created=models.DateTimeField(auto_now_add=True,null=True)
    class Meta: ordering=['-date','-id']; verbose_name='hours submission'; verbose_name_plural='volunteer hours'
    @property
    def status(self): return 'Approved' if self.approved else 'Rejected' if self.rejected else 'Pending review'
class Article(models.Model):
    title=models.CharField(max_length=180)
    slug=models.SlugField(unique=True)
    category=models.CharField(max_length=60)
    summary=models.CharField(max_length=250)
    body=models.TextField()
    image=models.CharField(max_length=150,default='img/hero.jpg')
    created=models.DateTimeField(auto_now_add=True)
    published=models.BooleanField(default=True)
    def __str__(self): return self.title
class Contact(models.Model):
    class Meta: ordering=['-created']; verbose_name='contact message'
    def __str__(self): return f'{self.name} <{self.email}>'
    name=models.CharField(max_length=100)
    email=models.EmailField()
    message=models.TextField()
    created=models.DateTimeField(auto_now_add=True)
class Subscriber(models.Model):
    class Meta: ordering=['-created']; verbose_name='newsletter subscriber'
    def __str__(self): return self.email
    email=models.EmailField(unique=True)
    created=models.DateTimeField(auto_now_add=True)

class ListingReport(models.Model):
    reporter=models.ForeignKey(User,on_delete=models.CASCADE)
    opportunity=models.ForeignKey(Opportunity,on_delete=models.CASCADE)
    reason=models.TextField(max_length=2000)
    resolved=models.BooleanField(default=False)
    created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['resolved','-created']
    def __str__(self): return f'Report on {self.opportunity}'
