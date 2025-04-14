from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import FormView
from django.views.decorators.debug import sensitive_post_parameters
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext as _

import logging

from accounts.models import OTP
from accounts.services.otp import OTPService
logger = logging.getLogger('app')


@method_decorator([never_cache, csrf_protect], name='dispatch')
class BaseRegistrationView(FormView):
    """
    Base view for user registration with OTP verification
    Subclass should specify:
    - form_class
    - role
    - template_name
    - register_url
    """
    otp_purpose = OTP.Purpose.REGISTRATION
    form_class = None  # Must be overridden
    role = None  # Must be overridden
    template_name = None  # Must be overridden
    register_url = None # Must be overridden

    @method_decorator(sensitive_post_parameters('password1', 'password2'))
    def dispatch(self, request, *args, **kwargs):
        logger.info(f"Dispatching {self.__class__.__name__} for role: {self.role}")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Convert date objects to ISO format strings
        cleaned_data = form.cleaned_data.copy()
        if 'date_of_birth' in cleaned_data and hasattr(cleaned_data['date_of_birth'], 'isoformat'):
            cleaned_data['date_of_birth'] = cleaned_data['date_of_birth'].isoformat()
        
        # Store form data, registration URL, and user type url in session
        self.request.session['registration_data'] = cleaned_data
        self.request.session['register_url'] = self.register_url
        self.request.session['user_type'] = self.role.name.lower()
        
        # Generate and send OTP
        email = form.cleaned_data['email']
        otp = OTPService.generate_otp(email, self.otp_purpose)
        
        if not otp:
            logger.error(f"Failed to generate OTP for {email}")
            form.add_error(None, _("OTP generation failed. Please try again."))
            return self.form_invalid(form)
        
        logger.info(f"OTP generated for {email}, redirecting to verification")
        return redirect('accounts:otp_verification')
    
    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    logger.warning(f"Form error: {error}")
                    messages.error(
                        self.request,
                        _(f"{error}"),
                        extra_tags='alert-danger'
                    )
                else:
                    logger.warning(f"Field error - {field}: {error}")
                    label = form.fields[field].label
                    messages.error(
                        self.request,
                        _(f"{label}: {error}"),
                        extra_tags='alert-danger'
                    )
        return super().form_invalid(form)