import logging
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from accounts.forms import BaseRegistrationForm

from .models import TutorProfile
from company.models import Company
from accounts.models import User
from .models import TutorProfile
from session.models import Session

logger = logging.getLogger('app')

class TutorRegistrationForm(BaseRegistrationForm):
    qualification = forms.CharField(max_length=100)
    years_of_experience = forms.IntegerField()
    address = forms.CharField(required=False, widget=forms.Textarea)
    bio = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial company (latest created)
        self.company = Company.objects.last()
        if not self.company:
            logger.error("No company exists in database for tutor registration")
            raise ValidationError(_("System configuration error - no company exists"))
        
        # Add hidden role field to the form
        self.fields['role'] = forms.CharField(
            initial=User.Role.TUTOR,
            widget=forms.HiddenInput(),
            required=False
        )

    def save(self, commit=True):
        # First save the User
        user = super().save(commit=False)
        user.role = User.Role.TUTOR

        if commit:
            user.save()
            # Then create TutorProfile
            profile_data = {
                'user': user,
                'company': self.company,
                'qualification': self.cleaned_data.get('qualification'),
                'years_of_experience': self.cleaned_data.get('years_of_experience'),
                'address': self.cleaned_data.get('address'),
                'bio': self.cleaned_data.get('bio'),
        }

            try:
                TutorProfile.objects.create(**profile_data)
                logger.info(f"Tutor profile created for user {user.email}")
            except Exception as e:
                logger.error(f"Failed to create tutor profile for {user.email}: {str(e)}")
                raise ValidationError(_("Failed to create tutor profile"))

            return user

class SessionCreationForm(forms.ModelForm):

    class Meta:
        model = Session
        fields = ["start_time", "end_time", "session_subject", "session_summary"]  # Exclude tutor & status

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if end_time and start_time and end_time <= start_time:
            raise forms.ValidationError("End time must be after start time.")

        return cleaned_data