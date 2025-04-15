from django.views.generic import ListView
from django.core.exceptions import PermissionDenied

from child.views import ParentRequiredMixin
from child.models import Child
from .models import Session

import logging

logger = logging.getLogger('app')

class ChildSessionsDashboard(ParentRequiredMixin, ListView):
    model = Session
    template_name = 'sessions/dashboards/child_sessions_dashboard.html'
    context_object_name = 'sessions'
    paginate_by = 5  # Optional: Add pagination if needed

    def get_queryset(self):
        # Get the child object based on the URL parameter
        child_id = self.kwargs.get('child_id')
        try:
            child = Child.objects.get(id=child_id, parent=self.request.user)
        except Child.DoesNotExist:
            logger.warning(f"Permission denied for user {self.request.user} to access child {child_id}.")
            raise PermissionDenied("You don't have permission to view sessions for this child.")

        # Return sessions associated with the child
        return Session.objects.filter(child=child).select_related('tutor', 'child').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the child object to the context
        child_id = self.kwargs.get('child_id')
        context['child'] = Child.objects.get(id=child_id, parent=self.request.user)
        context['parent'] = self.request.user
        context['active_section'] = 'sessions'
        return context