from django import forms
from django.utils import timezone
from .models import Organization, Event, Location, Message
class OrganizationForm(forms.ModelForm):
    class Meta:
        model=Organization
        fields=['name','bio','city','website','verification_note','public']
class EventForm(forms.ModelForm):
    class Meta:
        model=Event
        fields=['title','starts','ends','venue']
        widgets={k:forms.DateTimeInput(attrs={'type':'datetime-local'},format='%Y-%m-%dT%H:%M') for k in ['starts','ends']}
    def clean(self):
        d=super().clean()
        if d.get('starts') and d.get('ends') and d['ends']<=d['starts']: self.add_error('ends','End must be after start.')
        return d
class LocationForm(forms.ModelForm):
    class Meta:
        model=Location; fields=['latitude','longitude','approximate']
class MessageForm(forms.ModelForm):
    class Meta:
        model=Message; fields=['body']
        widgets={'body':forms.Textarea(attrs={'rows':3})}
