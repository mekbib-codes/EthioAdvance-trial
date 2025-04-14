from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import FormView
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.views.generic import TemplateView
from django.core.cache import cache

import logging

from accounts.forms import PasswordResetRequestForm, SetNewPasswordForm
from accounts.models import OTP, User
from accounts.services.otp import OTPService

logger = logging.getLogger('app')

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
