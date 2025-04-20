from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Child

import logging

logger = logging.getLogger('app')

class ChildRegistrationForm(forms.ModelForm):

    class Meta:
        model = Child
        fields = [
            'first_name', 
            'last_name',
            'date_of_birth',
            'gender',
            'grade_level',
            'school',
            'special_needs',
            'academic_interests',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'special_needs': forms.Textarea(attrs={'rows': 3}),
            'academic_interests': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'date_of_birth': 'Format: YYYY-MM-DD',
        }

    def __init__(self, *args, **kwargs):
        self.parent = kwargs.pop('parent', None)
        super().__init__(*args, **kwargs)
        
        # Set date limits for date picker
        today = timezone.now().date()
        max_date = today.strftime('%Y-%m-%d')
        min_date = (today - timezone.timedelta(days=18*365)).strftime('%Y-%m-%d')
        self.fields['date_of_birth'].widget.attrs.update({
            'max': max_date,
            'min': min_date
        })

    def clean_date_of_birth(self):
        dob = self.cleaned_data['date_of_birth']
        today = timezone.now().date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        if age > 18:
            raise ValidationError("Child must be under 18 years old.")
        if age < 4:
            raise ValidationError("Child must be at least 4 years old.")
            
        return dob

    def save(self, commit=True):
        child = super().save(commit=False)
        child.parent = self.parent
        if commit:
            child.save()
        return child

class ChildUpdateForm(forms.ModelForm):
    class Meta:
        model = Child
        # Exclude parent, tutor, and boolean fields
        exclude = ['parent', 'tutor', 'is_active']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'special_needs': forms.Textarea(attrs={'rows': 3, 'class': 'form-input'}),
            'academic_interests': forms.Textarea(attrs={'rows': 3, 'class': 'form-input'}),
        }