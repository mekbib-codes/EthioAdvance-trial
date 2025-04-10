import logging
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import User

logger = logging.getLogger(__name__)

class BaseRegistrationForm(forms.ModelForm):
    """Base form containing common registration fields"""
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput,
        strip=False,
        help_text=_("Enter a strong password"),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
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