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

        self.fields['date_of_birth'].widget.attrs.update({
            'max': timezone.now().date().strftime('%Y-%m-%d')
        })

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