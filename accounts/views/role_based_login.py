from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext as _

import logging

from accounts.models import User

logger = logging.getLogger('app')

class RoleBasedLoginView(LoginView):
    template_name = 'forms/login_form.html'
    
    # Dictionary mapping for O(1) lookups
    ROLE_REDIRECTS = {
        User.Role.PARENT: ('parent:dashboard'),
        User.Role.TUTOR: ('tutor:dashboard'),
        User.Role.COMPANY: ('company:dashboard'),
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
            success_url = self.ROLE_REDIRECTS.get(user.role)
            if not success_url:
                messages.info(
                    self.request,
                    _("Welcome! However, your user type doesn't have a dashboard yet."),
                    extra_tags='alert-info'
                )
                return reverse(self.DEFAULT_REDIRECT)
            logger.info(f"User {user.email} ({user.role}) logged in")
            return reverse(success_url)
            
        except Exception as e:
            messages.error(
                self.request,
                _("Login successful but we encountered a redirect issue"),
                extra_tags='alert-danger'
            )
            logger.error(f"Login redirect failed for user ID {user.id} ({user.email}): {str(e)}")
            return reverse(self.DEFAULT_REDIRECT)