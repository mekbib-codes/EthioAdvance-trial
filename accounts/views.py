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

from parent.forms import ParentRegistrationForm
from .services.otp import OTPService
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
                return redirect(self.get_register_redirect())

            is_valid, otp = OTPService.verify_otp(email, otp_code, self.otp_purpose)

            if not is_valid:
                logger.warning(f"Invalid OTP for {email}")
                error_message = _("Invalid OTP code for email: {email}. Please try again.").format(email=email)
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
        return redirect(register_url)
    
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