from django.views.generic import ListView
from django.core.exceptions import PermissionDenied

from child.models import Child
from .models import Session
from accounts.mixins import ParentorTutorRequiredMixin

import logging

logger = logging.getLogger('app')

from django.views.generic import ListView
from django.core.exceptions import PermissionDenied
from child.models import Child
from .models import Session

class BaseSessionsDashboardView(ListView):
    model = Session
    template_name = None # Override in subclass
    context_object_name = 'sessions'
    paginate_by = 5

    def get_child(self):
        """Fetch the child object based on the URL parameter."""
        child_id = self.kwargs.get('child_id')
        try:
            child = Child.objects.get(id=child_id)
        except Child.DoesNotExist:
            raise PermissionDenied("You don't have permission to view sessions for this child.")
        return child

    def get_queryset(self):
        """Fetch sessions for the child."""
        child = self.get_child()
        return Session.objects.filter(child=child).select_related('tutor', 'child').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['child'] = self.get_child()
        context['active_section'] = 'sessions'
        return context