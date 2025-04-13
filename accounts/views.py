from django.shortcuts import render, redirect
from django.http import  HttpRequest
from django.urls import reverse
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import FormView, TemplateView
from django.core.cache import cache
from django.views import View

from parent.forms import ParentRegistrationForm
from .forms import PasswordResetRequestForm, SetNewPasswordForm
from .services.otp import OTPService
from .services.send_email import SendEmailService
from .models import User, OTP

import logging

logger = logging.getLogger('app')

def home(request: HttpRequest):
    return render(request, "accounts/home.html", {})


class RoleBasedLoginView(LoginView):
    template_name = 'forms/login_form.html'
    
    # Dictionary mapping for O(1) lookups
    ROLE_REDIRECTS = {
        User.Role.PARENT: ('parent:dashboard', {'parent_slug': 'user_slug'}),
        User.Role.TUTOR: ('tutor:dashboard',{'tutor_slug': 'user_slug'}),
        User.Role.CHILD: ('child:dashboard', {'child_slug': 'user_slug'}),
        User.Role.COMPANY: ('company:dashboard', {'company_slug': 'user_slug'}),
    }
    DEFAULT_REDIRECT = 'accounts:login'

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    messages.error(
                        self.request,
                        _(f"{error}"),
                        extra_tags='alert-danger'
                    )
                else:
                    label = form.fields[field].label
                    messages.error(
                        self.request,
                        _(f"{label}: {error}"),
                        extra_tags='alert-danger'
                    )
        return super().form_invalid(form)

    def form_valid(self, form):
        """Add success message on valid form submission"""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _("You have successfully logged in!"),
            extra_tags='alert-success'
        )
        return response
    
    def get_success_url(self):
        user = self.request.user

        # Defensive check in case user isn't authenticated
        if not user.is_authenticated:
            return reverse(self.DEFAULT_REDIRECT)
        
        try:
            route_info = self.ROLE_REDIRECTS.get(user.role)
            if not route_info:
                messages.info(
                    self.request,
                    _("Welcome! However, your user type doesn't have a dashboard yet."),
                    extra_tags='alert-info'
                )
                return reverse(self.DEFAULT_REDIRECT)
                
            route_name, kwargs = route_info
            # Replace 'user_slug' with actual slug
            kwargs = {k: user.slug if v == 'user_slug' else v 
                     for k, v in kwargs.items()}
            
            logger.info(f"User {user.email} ({user.role}) logged in")
            return reverse(route_name, kwargs=kwargs)
            
        except Exception as e:
            messages.error(
                self.request,
                _("Login successful but we encountered a redirect issue"),
                extra_tags='alert-danger'
            )
            logger.error(f"Login redirect failed for user ID {user.id} ({user.email}): {str(e)}")
            return reverse(self.DEFAULT_REDIRECT)

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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['role'] = self.role
        return kwargs

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
    
@method_decorator([never_cache, csrf_protect], name='dispatch')
class OTPVerificationView(TemplateView):
    """
    Handles OTP verification and final user creation
    """
    
    template_name = 'forms/otp_verification.html'
    otp_purpose = OTP.Purpose.REGISTRATION

    def get(self, request, *args, **kwargs):
        if 'registration_data' not in request.session:
            logger.warning("OTP verification accessed without registration data")
            return redirect(self.get_register_redirect())
        
        # Fetch email from session data
        registration_data = request.session.get('registration_data', {})
        email = registration_data.get('email', None)

        # Pass email to context to show in the template
        context = self.get_context_data(email=email)  # Ensure `email` is in context
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        try:
            # 1. Safely access session data
            registration_data = request.session.get('registration_data', {})
            if not registration_data:
                logger.error("Missing registration_data in session")
                return redirect(self.get_register_redirect())

            # 3. Verify OTP
            otp_code = request.POST.get('otp_code', '')
            email = registration_data.get('email')
            
            if not email:
                logger.error("Email missing in registration data")
                return redirect(self.get_register_redirect())

            # Rate-limiting: Check how many attempts the user has made
            attempt_key = f"otp_attempts:{email}"
            attempts = cache.get(attempt_key, 0)

            if attempts >= 5:  # Allow 5 attempts, then block
                logger.warning(f"Too many attempts for {email}")
                messages.error(request, _("Too many failed attempts. Please try again later."))
                return redirect("accounts:home")

            is_valid, otp = OTPService.verify_otp(email, otp_code, self.otp_purpose)

            if not is_valid:
                logger.warning(f"Invalid OTP for {email}")
                error_message = _(f"Invalid OTP code for email: {email}. Please try again.")
                messages.error(request, error_message)
                # Increment the attempts count
                cache.set(attempt_key, attempts + 1, timeout=600)  # Timeout of 10 minutes
                return self.render_to_response(self.get_context_data(error=error_message))
            
            # Reset the attempts if OTP is valid
            cache.delete(attempt_key)
            
            # 4. Create user
            form_class = self.get_registration_form_class()
            form = form_class(data=registration_data)
            
            if not form.is_valid():
                logger.error(f"Form errors: {form.errors.as_json()}")
                return redirect(self.get_register_redirect())
            
            try:
                user = form.save()
                
                # Optional: Send welcome email or other post-registration logic
                logger.info(f"New user registered: {user.email}")
                
                SendEmailService.send_welcome_message(request=request, user=user)
                # Clear session before redirect
                self.clean_session(request)
                
                messages.success(
                    request,
                    _("Registration successful! Please log in to continue."),
                    extra_tags='alert-success'
                )
                
                return redirect('accounts:login')  # Always use redirect() not reverse()

            except Exception as e:
                logger.error(f"Registration failed: {str(e)}", exc_info=True)
                messages.error(
                    request,
                    _("Registration failed. Please try again."),
                    extra_tags='alert-danger'
                )
                return redirect(self.get_register_redirect())

        except Exception as e:
            logger.critical(f"Unexpected error: {str(e)}", exc_info=True)
            return redirect(self.get_register_redirect())

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
                            #  'tutor': TutorRegistrationForm,
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

@method_decorator([never_cache, csrf_protect], name='dispatch')   
class PasswordResetRequestedView(FormView):

    template_name = 'forms/password_reset_request_form.html'
    form_class = PasswordResetRequestForm

    def form_valid(self, form):
        email = form.cleaned_data['email']        
        otp = OTPService.generate_otp(email, purpose=OTP.Purpose.PASSWORD_RESET)

        if not otp:
            messages.error(self.request, _("Failed to generate OTP. Try again later."))
            return self.form_invalid(form)
        
        user_data = {'email': email}
        self.request.session['password_reset_data'] = user_data

        messages.success(self.request, _("We’ve sent a verification code to your email!"))
        return redirect('accounts:password_reset_verify')
    
    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    messages.error(
                        self.request,
                        _(f"{error}"),
                        extra_tags='alert-danger'
                    )
                else:
                    label = form.fields[field].label
                    messages.error(
                        self.request,
                        _(f"{label}: {error}"),
                        extra_tags='alert-danger'
                    )
        return super().form_invalid(form)
    

@method_decorator([never_cache, csrf_protect], name='dispatch')
class PasswordResetOTPVerificationView(TemplateView):
    template_name = 'forms/password_reset_verify.html'
    otp_purpose = OTP.Purpose.PASSWORD_RESET

    def get(self, request, *args, **kwargs):
        if 'password_reset_data' not in request.session:
            messages.error(request, _("Password reset session expired. Please try again."))
            return redirect('accounts:reset_password')

        context = {'email': request.session.get('password_reset_data').get('email')}
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        user_data = request.session.get('password_reset_data')
        email = user_data.get('email')
        otp_code = request.POST.get('otp_code', '')

        if not email:
            messages.error(request, _("Session expired. Please try again."))
            return redirect('accounts:password_reset_request')

        # Rate-limiting: Check how many attempts the user has made
        attempt_key = f"otp_attempts:{email}"
        attempts = cache.get(attempt_key, 0)

        if attempts >= 5:  # Allow 5 attempts, then block
            logger.warning(f"Too many attempts for {email}")
            messages.error(request, _("Too many failed attempts. Please try again later."))
            return redirect("accounts:home")
        
        is_valid, otp = OTPService.verify_otp(email, otp_code, self.otp_purpose)
        
        if not is_valid:
            logger.warning(f"Invalid OTP for {email}")
            messages.error(request, _("Invalid code. Please check and try again."))
            # Increment the attempts count
            cache.set(attempt_key, attempts + 1, timeout=600)  # Timeout of 10 minutes
            return self.render_to_response({'email': email})
        
        # Reset the attempts if OTP is valid
        cache.delete(attempt_key)

        request.session['password_reset_verified'] = True
        return redirect('accounts:set_new_password')
    
@method_decorator([never_cache, csrf_protect], name='dispatch')
class SetNewPasswordView(FormView):
    template_name = 'forms/set_new_password.html'
    form_class = SetNewPasswordForm  # Password1 + Password2 fields

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('password_reset_verified'):
            messages.error(request, _("Verification required."))
            return redirect('accounts:reset_password')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user_data = self.request.session.get('password_reset_data')
        email = user_data.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(self.request, _("User not found. Please restart the process."))
            return redirect('accounts:reset_password')

        # Use your form's save method — clean and reusable
        form.save(user)

        # Clear session data after success
        for key in ['password_reset_data', 'password_reset_verified']:
            self.request.session.pop(key, None)

        logger.info(f"New passoword set to user with email {email}")
        messages.success(
            self.request,
            _("Your password has been reset successfully! You can now log in.")
        )
        return redirect('accounts:login')
    
    def form_invalid(self, form):
        print(form.errors.items())
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    messages.error(self.request, _(f"{error}"), extra_tags='alert-danger')
                else:
                    label = form.fields[field].label
                    messages.error(
                        self.request,
                        _(f"{label}: {error}"),
                        extra_tags='alert-danger'
                    )
        return super().form_invalid(form)
