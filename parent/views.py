from django.views.generic import TemplateView
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import View
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.contrib import messages


from .forms import ParentRegistrationForm
from accounts.views.base_registration import BaseRegistrationView
from accounts.models import User
from child.views import ParentRequiredMixin
from session.models import Session

import logging
logger = logging.getLogger('app')

class ParentDashboardView(ParentRequiredMixin, TemplateView):
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

class UpdateSessionStatusView(ParentRequiredMixin, View):

    def post(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(Session, id=session_id)

        # Validate the status
        status = self.kwargs.get("status")
        if status in ["approved", "rejected"]:
            session.status = status
            session.save()
            
            # Render only the updated session block to be replaced dynamically
            return render(request, "sessions/status_update/session_block.html", {"session": session})

        return HttpResponse("Invalid status", status=400)