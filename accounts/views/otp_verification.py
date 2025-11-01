from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.core.cache import cache
from django.contrib import messages
from django.utils.translation import gettext as _
from django.urls import reverse
from django.views import View


import logging

from accounts.models import OTP
from accounts.services.otp import OTPService
from accounts.services.user_registration import UserRegistrationService
from parent.forms import ParentRegistrationForm
from tutor.forms import TutorRegistrationForm

logger = logging.getLogger('app')


@method_decorator([never_cache, csrf_protect], name='dispatch')
class OTPVerificationView(TemplateView):
    """
    Handles only OTP verification, delegates user creation to service
    """
    template_name = 'forms/otp_verification.html'
    otp_purpose = OTP.Purpose.REGISTRATION

    def get(self, request, *args, **kwargs):
        if 'registration_data' not in request.session:
            logger.warning("OTP verification accessed without registration data")
            return redirect(self.get_register_redirect())
        
        context = self.get_context_data(
            email=request.session['registration_data'].get('email')
        )
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        try:
            # Validate session and input
            registration_data = self._validate_session_data(request)
            if not registration_data:
                return redirect(self.get_register_redirect())

            email = registration_data.get('email')
            otp_code = request.POST.get('otp_code', '')

            # Rate limiting check
            if not self._check_rate_limit(request, email):
                return redirect("accounts:home")

            # OTP verification
            if not self._verify_otp(request, email, otp_code):
                return self.render_to_response(self.get_context_data())

            # User creation via service
            return self._handle_registration_flow(request, registration_data)

        except Exception as e:
            logger.critical(f"Unexpected error: {str(e)}", exc_info=True)
            messages.error(request, _("An error occurred. Please try again."))
            return redirect(self.get_register_redirect())

    def _validate_session_data(self, request):
        """Validate and return registration data from session"""
        registration_data = request.session.get('registration_data')
        if not registration_data:
            logger.error("Missing registration_data in session")
            messages.error(request, _("Session expired. Please register again."))
        return registration_data
    
    def _check_rate_limit(self, request, email):
        """Check and enforce rate limiting"""
        attempt_key = f"otp_attempts:{email}"
        attempts = cache.get(attempt_key, 0)
        
        if attempts >= 5:
            logger.warning(f"Too many attempts for {email}")
            messages.error(request, _("Too many failed attempts. Please try again later."))
            return False
        return True
    
    def _verify_otp(self, request, email, otp_code):
        """Handle OTP verification logic"""
        is_valid, otp = OTPService.verify_otp(email, otp_code, self.otp_purpose)
        
        if not is_valid:
            logger.warning(f"Invalid OTP for {email}")
            messages.error(request, _("Invalid OTP code. Please try again."))
            attempt_key = f"otp_attempts:{email}"
            
            # Initialize the key if it doesn't exist, or increment if it does
            if not cache.get(attempt_key):
                cache.set(attempt_key, 1, 600)  # Set with initial value 1 and 10 minute timeout
            else:
                cache.incr(attempt_key)
            
            return False
        
        cache.delete(f"otp_attempts:{email}")
        return True
    
    def _handle_registration_flow(self, request, registration_data):
        """Orchestrate the registration flow using the service"""
        form_class = self.get_registration_form_class()

        # Initialize form with request if needed
        form_kwargs = {'data': registration_data}
        if hasattr(form_class, 'requires_request_context'):
            form_kwargs['request'] = request
            
        form = form_class(**form_kwargs)

         # Use generic service
        user, error = UserRegistrationService.create_user(form, request=request)

        if error or not user:
            logger.error(f"Registration failed: {error}")
            messages.error(request, error)
            return redirect(self.get_register_redirect())

        # Handle post-registration tasks
        UserRegistrationService.post_registration_tasks(request, user)
        
        messages.success(
            request,
            _("Registration successful! Please log in to continue."),
            extra_tags='alert-success'
        )
        return redirect('accounts:login')
    
    def clean_session(self, request):
        """Safely remove registration session data"""
        try:
            for key in ['registration_data', 'register_url', 'success_redirect_name']:
                if key in request.session:
                    del request.session[key]
            request.session.save()
        except Exception as e:
            logger.error(f"Error cleaning session: {str(e)}")

    def get_register_redirect(self):
        """Get the appropriate registration redirect URL"""
        register_url = self.request.session.get('register_url')
        return register_url
    
    def get_registration_form_class(self):
        """
        Returns the appropriate form class based on the registration URL stored in session
        """
        REGISTER_FORM_MAP = {'parent': ParentRegistrationForm,
                             'tutor': TutorRegistrationForm,
                             # Add more roles here as needed
                             }
        key = self.request.session.get('user_type')
        return REGISTER_FORM_MAP.get(key)
    
class OTPResendView(View):
    """
    View for resending OTP for various purposes (registration, password reset, etc.).
    """
    def get(self, request, *args, **kwargs):
        # Retrieve the purpose from the URL or session
        otp_purpose = self.kwargs.get('purpose').upper()  # e.g. 'registration' or 'password_reset'
        if not otp_purpose:
            messages.error(request, _("No OTP purpose specified."))
            return redirect(reverse('accounts:home'))

        # Ensure that the OTP purpose is valid
        if otp_purpose not in [OTP.Purpose.REGISTRATION, OTP.Purpose.PASSWORD_RESET, OTP.Purpose.EMAIL_CHANGE]:
            messages.error(request, _("Invalid OTP purpose."))
            return redirect(reverse('accounts:home'))

        # Fetch the session data based on the OTP purpose
        session_key = f'{otp_purpose}_data'.lower()
        user_data = request.session.get(session_key)

        if not user_data:
            messages.error(request, _("No data found for this process. Please try again."))
            return redirect(reverse('accounts:home'))  # You can modify this redirect based on the purpose

        email = user_data.get('email')
        if not email:
            messages.error(request, _("Email not found in session. Please try again."))
            return redirect(reverse('accounts:home'))  # You can modify this redirect based on the purpose

        # Send the OTP for the given purpose
        otp = OTPService.generate_otp(email, otp_purpose)
        if otp:
            messages.success(request, _("A new OTP has been sent to your email."))
        else:
            messages.error(request, _("Failed to send OTP. Please try again later."))

        redirect_based_on_purpose_map = {
            OTP.Purpose.REGISTRATION: 'accounts:otp_verification',
            OTP.Purpose.PASSWORD_RESET: 'accounts:password_reset_verify',
            # OTP.Purpose.EMAIL_CHANGE: 'accounts:email_change_verify'
        }
        
        return redirect(redirect_based_on_purpose_map.get(otp_purpose))