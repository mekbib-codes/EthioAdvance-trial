from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password

from .models import User

import logging
import re

logger = logging.getLogger('app')

class BaseRegistrationForm(forms.ModelForm):
    """Base form containing common registration fields"""
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        strip=False,
        help_text=_("Enter a strong password"),
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        strip=False,
        help_text=_("Enter the same password as before"),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'gender']
    
    def __init__(self, *args, **kwargs):
        self.role = kwargs.pop('role', None)
        super().__init__(*args, **kwargs)
        if self.role:
            self.fields['role'] = forms.CharField(
                initial=self.role,
                widget=forms.HiddenInput(),
                required=True
            )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            logger.warning(f"Registration attempt with existing email: {email}")
            raise ValidationError(_("A user with that email already exists."))
        return email
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if password1:
            # First validate using Django's built-in validators
            try:
                validate_password(password1)
            except ValidationError as error:
                raise ValidationError(error.messages)
            
             # Add only what Django validators don't already check!
            if not re.search(r'[A-Z]', password1):
                raise ValidationError(_("Password must contain at least one uppercase letter."))

            if not re.search(r'[^A-Za-z0-9]', password1):
                raise ValidationError(_("Password must contain at least one special character."))
        
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            logger.warning("Password mismatch during registration")
            raise ValidationError(_("The two password fields didn't match."))
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            logger.info(f"New user created: {user.email} (role: {user.role})")
        return user
    
class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label=_("Email"), max_length=254)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning(f"Password reset attempt for non-existent email: {email}")
            raise ValidationError(_("No user with this email address exists."))
        return email
    
class SetNewPasswordForm(forms.Form):
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        strip=False,
        help_text=_("Enter a strong password"),
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        strip=False,
        help_text=_("Enter the same password as before"),
    )

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if password1:
            # First validate using Django's built-in validators
            try:
                validate_password(password1)
            except ValidationError as error:
                raise ValidationError(error.messages)
            
             # Add only what Django validators don't already check!
            if not re.search(r'[A-Z]', password1):
                raise ValidationError(_("Password must contain at least one uppercase letter."))

            if not re.search(r'[^A-Za-z0-9]', password1):
                raise ValidationError(_("Password must contain at least one special character."))
        
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            logger.warning("Password mismatch during registration")
            raise ValidationError(_("The two password fields didn't match."))
        
        return cleaned_data
        
    
    def save(self, user, commit=True):
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            logger.info(f"Password reset for: {user.email} (role: {user.role})")
        return user