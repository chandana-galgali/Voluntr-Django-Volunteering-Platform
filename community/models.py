from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from uuid import uuid4

U = settings.AUTH_USER_MODEL
class Account(models.Model):
    user = models.OneToOneField(U, on_delete=models.CASCADE, related_name='voluntr_account')
    verified_email = models.EmailField(blank=True)
    last_verification = models.DateTimeField(null=True, blank=True)
    google_subject = models.CharField(max_length=255, unique=True, null=True, blank=True)

class LoginAttempt(models.Model):
    key = models.CharField(max_length=64, unique=True)
    count = models.PositiveIntegerField(default=0)
    until = models.DateTimeField(default=timezone.now)

class Organization(models.Model):
    owner = models.OneToOneField(U, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    bio = models.TextField(max_length=3000)
    city = models.CharField(max_length=100)
    website = models.URLField(blank=True)
    verification_note = models.TextField(max_length=2000, blank=True, help_text='Private evidence or registration reference for the administrator. Do not include sensitive personal IDs.')
    verified = models.BooleanField(default=False)
    public = models.BooleanField(default=False)
    def __str__(self): return self.name

class Location(models.Model):
    opportunity = models.OneToOneField('core.Opportunity', on_delete=models.CASCADE, related_name='map_location')
    latitude = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])
    approximate = models.BooleanField(default=True)

class Event(models.Model):
    opportunity = models.ForeignKey('core.Opportunity', on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=150)
    starts = models.DateTimeField()
    ends = models.DateTimeField()
    venue = models.CharField(max_length=220, blank=True)
    cancelled = models.BooleanField(default=False)
    checkin_key = models.UUIDField(default=uuid4, editable=False)
    class Meta: ordering = ['starts']
    def __str__(self): return self.title

class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    volunteer = models.ForeignKey(U, on_delete=models.CASCADE)
    checked_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['event','volunteer'], name='unique_event_attendance')]

class Notification(models.Model):
    user = models.ForeignKey(U, on_delete=models.CASCADE)
    text = models.CharField(max_length=250)
    link = models.CharField(max_length=250, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    class Meta: ordering = ['-created']

class Message(models.Model):
    application = models.ForeignKey('core.Application', on_delete=models.CASCADE, related_name='conversation_messages')
    sender = models.ForeignKey(U, on_delete=models.CASCADE)
    body = models.TextField(max_length=2000)
    created = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['created']

class Reminder(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(U, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['event','user'], name='unique_event_reminder')]
