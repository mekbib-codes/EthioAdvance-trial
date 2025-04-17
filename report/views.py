from django.views.generic import ListView
from django.views import View
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _

from child.models import Child
from .models import Report
from accounts.mixins import TutorRequiredMixin

import logging
logger = logging.getLogger('app')

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

class BaseReportStepView(TutorRequiredMixin, View):
    template_name = None  # Must be defined in subclasses
    form_class = None  # Must be defined in subclasses
    success_url_name = None  # Must be defined in subclasses

    def dispatch(self, request, *args, **kwargs):
        # Fetch the child object and ensure it is assigned to the tutor
        self.child = get_object_or_404(Child, id=self.kwargs.get('child_id'))
        if self.child.tutor != self.request.user:
            logger.warning(f"Unauthorized access attempt by {request.user.email} for child {self.child.id}")
            raise PermissionDenied("You can only access reports for your assigned students.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Handle GET requests to display the form."""
        form = self.form_class()
        return render(request, self.template_name, {
            'form': form,
            'child': self.child
        })

    def post(self, request, *args, **kwargs):
        """Handle POST requests to process the form."""
        form = self.form_class(request.POST)
        if form.is_valid():
            try:
                self.process_form_data(form.cleaned_data)
                logger.info(f"Data saved to session by {request.user.email} for child {self.child.id}")
                messages.success(request, f"Data for {self.child.get_full_name()} saved successfully.")
                return redirect(self.get_success_url())
            except Exception as e:
                logger.error(f"Error processing data for {request.user.email}: {str(e)}", exc_info=True)
                messages.error(request, "An error occurred while saving the data. Please try again.")
        else:
            self.handle_form_errors(form)

        return render(request, self.template_name, {
            'form': form,
            'child': self.child
        })

    def process_form_data(self, cleaned_data):
        """Process and save form data to the session. Must be implemented in subclasses."""
        raise NotImplementedError("Subclasses must implement the process_form_data method.")

    def handle_form_errors(self, form):
        """Handle form errors and display messages."""
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    logger.warning(f"Form error: {error}")
                    messages.error(self.request, _(f"{error}"), extra_tags='alert-danger')
                else:
                    logger.warning(f"Field error - {field}: {error}")
                    label = form.fields[field].label
                    messages.error(self.request, _(f"{label}: {error}"), extra_tags='alert-danger')

    def get_success_url(self):
        """Redirect to the next step in the report creation process."""
        return reverse_lazy(self.success_url_name, kwargs={'child_id': self.child.id})