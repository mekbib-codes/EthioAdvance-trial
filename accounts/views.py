from django.shortcuts import render
from django.http import  HttpRequest
from django.urls import reverse
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.utils.translation import gettext as _


from .models import User

import logging

logger = logging.getLogger('app')

def home(request: HttpRequest):
    return render(request, "accounts/home.html", {})


class RoleBasedLoginView(LoginView):
    template_name = 'accounts/login.html'
    
    # Dictionary mapping for O(1) lookups
    ROLE_REDIRECTS = {
        User.Role.PARENT: ('parent:dashboard', {'parent_slug': 'user_slug'}),
        User.Role.TUTOR: 'tutor:dashboard',
        User.Role.CHILD: 'child:dashboard',
        User.Role.COMPANY: 'company:dashboard',
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