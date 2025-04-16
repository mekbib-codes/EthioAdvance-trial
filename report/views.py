from django.shortcuts import render
from django.views.generic import ListView
from django.core.exceptions import PermissionDenied
from child.models import Child
from .models import Report

class BaseReportsDashboardView(ListView):
    model = Report
    template_name = None  # Override in subclass
    context_object_name = 'reports'
    paginate_by = 1

    def get_child(self):
        """Fetch the child object based on the URL parameter."""
        child_id = self.kwargs.get('child_id')
        try:
            child = Child.objects.get(id=child_id)
        except Child.DoesNotExist:
            raise PermissionDenied("You don't have permission to view reports for this child.")
        return child

    def get_queryset(self):
        """Fetch reports for the child."""
        child = self.get_child()
        return Report.objects.filter(child=child).select_related(
            'tutor', 'child'
        ).prefetch_related(
            'strengths', 'weaknesses', 'goals_achieved', 'learning_material_prepared', 'challenges_encountered', 'suggested_solutions'
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['child'] = self.get_child()
        context['active_section'] = 'reports'
        return context
