from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied

from accounts.decorators import parent_required
from .forms import ParentRegistrationForm
from accounts.views.base_registration import BaseRegistrationView
from accounts.models import User
import logging
logger = logging.getLogger('app')

@method_decorator(parent_required, name='dispatch')
class ParentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'parent/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            parent = self.request.user

            context.update({
                'parent': parent,
                'active_section': 'dashboard',
            })
            
            logger.info(
                f"Parent dashboard accessed by {parent.email} "
                f"(ID: {parent.pk})"
            )
            return context
            
        except Exception as e:
            logger.error(
                f"Parent dashboard error for {self.request.user.email}: {str(e)}",
                exc_info=True
            )
            raise PermissionDenied("Error loading dashboard")


class ParentRegistrationView(BaseRegistrationView):
    form_class = ParentRegistrationForm
    role = User.Role.PARENT
    template_name = 'registration/parent_register_form.html'
    register_url = 'parent:register'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['role'] = self.role  # Explicitly pass the role
        return kwargs
