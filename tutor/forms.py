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

class TutorProfileUpdateForm(forms.ModelForm):
    # Fields from the Parent (proxy for User) model
    first_name = forms.CharField(max_length=255, required=True, label="First Name")
    last_name = forms.CharField(max_length=255, required=True, label="Last Name")
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date of Birth"
    )
    gender = forms.ChoiceField(
        choices=User.Gender.choices,
        required=False,
        label="Gender"
    )
    phone_number = forms.CharField(max_length=15, required=False, label="Phone Number")

    class Meta:
        model = TutorProfile
        fields = [
            'avatar', 'qualification', 'years_of_experience', 'bio', 'address'
        ]

    def __init__(self, *args, **kwargs):
        tutor = kwargs.pop('tutor', None)  # Pass the tutor instance explicitly
        super().__init__(*args, **kwargs)

        # Prepopulate fields from the tutor (proxy for User) model
        if tutor:
            self.fields['first_name'].initial = tutor.first_name
            self.fields['last_name'].initial = tutor.last_name
            self.fields['date_of_birth'].initial = tutor.date_of_birth
            self.fields['gender'].initial = tutor.gender
            self.fields['phone_number'].initial = tutor.phone_number

    def save(self, commit=True):
        # Save ParentProfile fields
        profile = super().save(commit=False)

        # Save Parent (proxy for User) fields
        tutor = self.instance.user
        tutor.first_name = self.cleaned_data['first_name']
        tutor.last_name = self.cleaned_data['last_name']
        tutor.date_of_birth = self.cleaned_data['date_of_birth']
        tutor.gender = self.cleaned_data['gender']
        tutor.phone_number = self.cleaned_data['phone_number']

        if commit:
            tutor.save()
            profile.save()

        return profile
    
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