# parents/forms.py
import logging
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from accounts.forms import BaseRegistrationForm

from .models import ParentProfile
from company.models import Company
from accounts.models import User

logger = logging.getLogger('app')

class ParentRegistrationForm(BaseRegistrationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial company (latest created)
        self.company = Company.objects.last()
        if not self.company:
            logger.error("No company exists in database for parent registration")
            raise ValidationError(_("System configuration error - no company exists"))
        
        # Add hidden role field to the form
        self.fields['role'] = forms.CharField(
            initial=User.Role.PARENT,
            widget=forms.HiddenInput(),
            required=False
        )

    def save(self, commit=True):
        # First save the User (handled by parent class)
        user = super().save(commit=False)
        user.role = User.Role.PARENT

        if commit:
            user.save()
            # Then create ParentProfile
            profile_data = {
                'user': user,
                'company': self.company,
        }

            try:
                ParentProfile.objects.create(**profile_data)
                logger.info(f"Parent profile created for user {user.email}")
            except Exception as e:
                logger.error(f"Failed to create parent profile for {user.email}: {str(e)}")
                raise ValidationError(_("Failed to create parent profile"))

            return user

class ParentProfileUpdateForm(forms.ModelForm):
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
        model = ParentProfile
        fields = [
            'avatar', 'occupation', 'address', 'emergency_contact', 'preferred_communication'
        ]

    def __init__(self, *args, **kwargs):
        parent = kwargs.pop('parent', None)  # Pass the parent instance explicitly
        super().__init__(*args, **kwargs)

        # Prepopulate fields from the Parent (proxy for User) model
        if parent:
            self.fields['first_name'].initial = parent.first_name
            self.fields['last_name'].initial = parent.last_name
            self.fields['date_of_birth'].initial = parent.date_of_birth
            self.fields['gender'].initial = parent.gender
            self.fields['phone_number'].initial = parent.phone_number

    def save(self, commit=True):
        # Save ParentProfile fields
        profile = super().save(commit=False)

        # Save Parent (proxy for User) fields
        parent = self.instance.user
        parent.first_name = self.cleaned_data['first_name']
        parent.last_name = self.cleaned_data['last_name']
        parent.date_of_birth = self.cleaned_data['date_of_birth']
        parent.gender = self.cleaned_data['gender']
        parent.phone_number = self.cleaned_data['phone_number']

        if commit:
            parent.save()  # Save Parent (proxy for User) model
            profile.save()  # Save ParentProfile model

        return profile