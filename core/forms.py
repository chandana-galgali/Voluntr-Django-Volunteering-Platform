import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile,Opportunity,Application,Hours,Contact,Subscriber
from django.utils import timezone

NAME_RE=re.compile(r"^[^\W\d_]+(?:[ '.\-][^\W\d_]+)*\.?$")

def clean_person_name(value,label):
    value=' '.join((value or '').split())
    if value and not NAME_RE.match(value): raise forms.ValidationError(f'{label} can only contain letters, spaces, apostrophes, dots and hyphens.')
    return value

class Signup(UserCreationForm):
    first_name=forms.CharField(max_length=150,required=False)
    last_name=forms.CharField(max_length=150,required=False)
    email=forms.EmailField()
    role=forms.ChoiceField(choices=Profile._meta.get_field('role').choices,label='I want to',widget=forms.RadioSelect,initial='volunteer')
    class Meta(UserCreationForm.Meta): fields=['username','first_name','last_name','email']
    field_order=['role','first_name','last_name','username','email','password1','password2']
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['username'].help_text='Letters, numbers and @ . + - _ only.'
        self.fields['password2'].label='Confirm password'; self.fields['password2'].help_text=''
        self.fields['email'].widget.attrs.update(autocomplete='email')
        self.fields['role'].choices=[('volunteer','Volunteer — Find causes, apply and log your hours'),('organizer','Organizer — Post opportunities and manage volunteers')]
    def clean_first_name(self): return clean_person_name(self.cleaned_data.get('first_name'),'First name')
    def clean_last_name(self): return clean_person_name(self.cleaned_data.get('last_name'),'Last name')
    def clean_email(self):
        email=self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists(): raise forms.ValidationError('Email already registered. Sign in or reset your password instead.')
        return email
    def clean_username(self):
        username=self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists(): raise forms.ValidationError('That username is taken. Please choose another.')
        return username

class ProfileForm(forms.ModelForm):
    first_name=forms.CharField(max_length=150,required=False)
    last_name=forms.CharField(max_length=150,required=False)
    interests=forms.MultipleChoiceField(choices=Opportunity.CATEGORIES,required=False,widget=forms.CheckboxSelectMultiple,label='Causes I care about')
    class Meta:
        model=Profile; fields=['first_name','last_name','bio','city','skills','interests']
        labels={'skills':'Skills (comma-separated)','city':'City'}
        widgets={'bio':forms.Textarea(attrs={'rows':4,'maxlength':1000,'placeholder':'A few lines about you and why you volunteer'}),'skills':forms.Textarea(attrs={'rows':2,'placeholder':'e.g. teaching, first aid, design'})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        user=self.instance.user
        self.fields['first_name'].initial=user.first_name; self.fields['last_name'].initial=user.last_name
        valid={v for v,_ in Opportunity.CATEGORIES}
        self.initial['interests']=[x for x in self.instance.interest_list() if x in valid]
    def clean_first_name(self): return clean_person_name(self.cleaned_data.get('first_name'),'First name')
    def clean_last_name(self): return clean_person_name(self.cleaned_data.get('last_name'),'Last name')
    def clean_city(self):
        city=' '.join(self.cleaned_data.get('city','').split())
        if city and not re.match(r"^[^\W\d_][\w .,'\-()]*$",city): raise forms.ValidationError('Enter a valid city name.')
        return city
    def clean_skills(self):
        skills=[s.strip() for s in self.cleaned_data.get('skills','').replace(';',',').split(',') if s.strip()]
        if any(len(s)>60 for s in skills): raise forms.ValidationError('Keep each skill under 60 characters.')
        return ', '.join(dict.fromkeys(skills))
    def clean_interests(self): return ','.join(self.cleaned_data.get('interests') or [])
    def save(self,commit=True):
        profile=super().save(commit=False)
        user=profile.user; user.first_name=self.cleaned_data['first_name']; user.last_name=self.cleaned_data['last_name']
        if commit: user.save(update_fields=['first_name','last_name']); profile.save()
        return profile

class OpportunityForm(forms.ModelForm):
    class Meta:
        model=Opportunity; fields=['title','organization','category','city','mode','summary','description','skills','commitment','slots','deadline']; widgets={'deadline':forms.DateInput(attrs={'type':'date'}),'summary':forms.TextInput(attrs={'maxlength':250})}
        help_texts={'summary':'One sentence shown on listing cards.','commitment':'e.g. 2–4 hours/week','city':'Use the city name (e.g. Mumbai) so the listing appears on the map.'}
    def clean_deadline(self):
        d=self.cleaned_data['deadline']
        if d and d<timezone.localdate() and (not self.instance.pk or d!=self.instance.deadline): raise forms.ValidationError('Choose a future date.')
        return d
    def clean_title(self):
        t=' '.join(self.cleaned_data['title'].split())
        if len(t)<5: raise forms.ValidationError('Use a descriptive title (at least 5 characters).')
        return t
class ApplicationForm(forms.ModelForm):
    class Meta: model=Application; fields=['motivation']; labels={'motivation':'Why would you like to volunteer for this role?'}
    def clean_motivation(self):
        v=self.cleaned_data['motivation'].strip()
        if len(v)<20: raise forms.ValidationError('Please enter at least 20 characters.')
        return v
class HoursForm(forms.ModelForm):
    class Meta: model=Hours; fields=['date','hours','note']; widgets={'date':forms.DateInput(attrs={'type':'date'}),'hours':forms.NumberInput(attrs={'min':'0.5','max':'24','step':'0.5'})}; labels={'note':'What did you do?'}
    def clean_date(self):
        d=self.cleaned_data['date']
        if d>timezone.localdate(): raise forms.ValidationError('Cannot log future hours.')
        return d
class ContactForm(forms.ModelForm):
    class Meta: model=Contact; fields=['name','email','message']
    def clean_message(self):
        m=self.cleaned_data['message'].strip()
        if len(m)<10: raise forms.ValidationError('Please write at least 10 characters.')
        return m
class SubscribeForm(forms.Form): email=forms.EmailField()
