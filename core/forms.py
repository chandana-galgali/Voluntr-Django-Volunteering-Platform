from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile,Opportunity,Application,Hours,Contact,Subscriber
from django.utils import timezone
class Signup(UserCreationForm):
    email=forms.EmailField()
    role=forms.ChoiceField(choices=Profile._meta.get_field('role').choices)
    class Meta(UserCreationForm.Meta): fields=['username','email']
    def clean_email(self):
        email=self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists(): raise forms.ValidationError('Email already registered.')
        return email
class ProfileForm(forms.ModelForm):
    class Meta: model=Profile; fields=['city','skills','interests']
class OpportunityForm(forms.ModelForm):
    class Meta:
        model=Opportunity; fields=['title','organization','category','city','mode','summary','description','skills','commitment','slots','deadline']; widgets={'deadline':forms.DateInput(attrs={'type':'date'})}
    def clean_deadline(self):
        d=self.cleaned_data['deadline']
        if d and d<timezone.localdate(): raise forms.ValidationError('Choose a future date.')
        return d
class ApplicationForm(forms.ModelForm):
    class Meta: model=Application; fields=['motivation']
    def clean_motivation(self):
        v=self.cleaned_data['motivation'].strip()
        if len(v)<20: raise forms.ValidationError('Please enter at least 20 characters.')
        return v
class HoursForm(forms.ModelForm):
    class Meta: model=Hours; fields=['date','hours','note']; widgets={'date':forms.DateInput(attrs={'type':'date'})}
    def clean_date(self):
        d=self.cleaned_data['date']
        if d>timezone.localdate(): raise forms.ValidationError('Cannot log future hours.')
        return d
class ContactForm(forms.ModelForm):
    class Meta: model=Contact; fields=['name','email','message']
class SubscribeForm(forms.Form): email=forms.EmailField()
