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
    # Profile fields (all optional except company)
    occupation = forms.CharField(required=False, max_length=100)
    address = forms.CharField(required=False, widget=forms.Textarea)
    emergency_contact = forms.CharField(required=False, max_length=20)
    preferred_communication = forms.ChoiceField(
        choices=ParentProfile._meta.get_field('preferred_communication').choices,
        initial='EMAIL',
        required=False
    )

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
                'occupation': self.cleaned_data.get('occupation'),
                'address': self.cleaned_data.get('address'),
                'emergency_contact': self.cleaned_data.get('emergency_contact'),
                'preferred_communication': self.cleaned_data.get('preferred_communication', 'EMAIL'),
        }

            try:
                ParentProfile.objects.create(**profile_data)
                logger.info(f"Parent profile created for user {user.email}")
            except Exception as e:
                logger.error(f"Failed to create parent profile for {user.email}: {str(e)}")
                raise ValidationError(_("Failed to create parent profile"))

            return user