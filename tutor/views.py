from django.views.generic import TemplateView
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _

from accounts.mixins import CompanyRequiredMixin, TutorRequiredMixin
from accounts.views.base_registration import BaseRegistrationView
from accounts.models import User
from .forms import TutorRegistrationForm, SessionCreationForm
from child.views import BaseChildrenDashboardView
from session.views import BaseSessionsDashboardView
from session.models import Session
from child.models import Child
from report.views import BaseReportsDashboardView

import logging
logger = logging.getLogger('app')

class TutorDashboardView(TutorRequiredMixin, TemplateView):
    template_name = 'tutor/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            tutor = self.request.user
            total_students = tutor.students.count()
            total_sessions = Session.objects.filter(tutor=tutor).count()
            pending_sessions = Session.objects.filter(tutor=tutor, status=Session.Status.PENDING).count()
            approved_sessions = Session.objects.filter(tutor=tutor, status=Session.Status.APPROVED).count()
            rejected_sessions = Session.objects.filter(tutor=tutor, status=Session.Status.REJECTED).count()

            context.update({
                'tutor': tutor,
                'active_section': 'dashboard',
            })
            
            logger.info(
                f"Tutor dashboard accessed by {tutor.email} "
                f"(ID: {tutor.pk})"
            )
            return context
            
        except Exception as e:
            logger.error(
                f"Tutor dashboard error for {self.request.user.email}: {str(e)}",
                exc_info=True
            )
            raise PermissionDenied("Error loading dashboard")


class TutorRegistrationView(CompanyRequiredMixin, BaseRegistrationView):
    form_class = TutorRegistrationForm # Replace with actual form class
    role = User.Role.TUTOR 
    template_name = 'registration/tutor_register_form.html'
    register_url = 'tutor:register'

class StudentsDashboardView(TutorRequiredMixin, BaseChildrenDashboardView):
    template_name = 'tutor/students/dashboard.html'  # Tutor-specific template
    paginate_by = 4

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(tutor=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tutor'] = self.request.user
        context['active_section'] = 'students'
        return context

class TutorSessionsDashboardView(TutorRequiredMixin, BaseSessionsDashboardView):
    template_name = 'tutor/sessions/dashboard.html'  # Tutor-specific template

    def get_child(self):
        """Fetch the child object and ensure it is assigned to the tutor."""
        child = super().get_child()
        if child.tutor != self.request.user:
            raise PermissionDenied("You don't have permission to view sessions for this child.")
        return child

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tutor'] = self.request.user
        return context
    
class CreateSessionView(TutorRequiredMixin, CreateView):
    model = Session
    form_class = SessionCreationForm
    template_name = 'forms/create_session.html'

    def dispatch(self, request, *args, **kwargs):
        # Fetch the child object and ensure it is assigned to the tutor
        self.child = get_object_or_404(Child, id=self.kwargs.get('child_id'))
        if self.child.tutor != self.request.user:
            logger.warning(f"Unauthorized session creation attempt by {request.user.email} for child {self.child.id}")
            raise PermissionDenied("You can only create sessions for your assigned students.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Assign the child and tutor to the session
        form.instance.child = self.child
        form.instance.tutor = self.request.user
        try:
            response = super().form_valid(form)
            messages.success(self.request, f"Session for {self.child.get_full_name()} created successfully.")
            logger.info(f"Session created successfully by {self.request.user.email} for child {self.child.id}")
            return response
        except Exception as e:
            logger.error(f"Error creating session by {self.request.user.email} for child {self.child.id}: {str(e)}", exc_info=True)
            messages.error(self.request, "An error occurred while creating the session. Please try again.")
            return self.form_invalid(form)

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['child'] = self.child
        context['active_section'] = 'sessions'
        return context
    
    def get_success_url(self):
        # Redirect to the tutor's sessions dashboard or another relevant page
        return reverse_lazy('tutor:child_sessions_dashboard', kwargs={'child_id': self.child.id})
    
class TutorReportsDashboardView(TutorRequiredMixin, BaseReportsDashboardView):
    template_name = 'tutor/reports/dashboard.html'  # Tutor-specific template

    def get_child(self):
        """Fetch the child object and ensure it belongs to the tutor."""
        child = super().get_child()
        if child.tutor != self.request.user:
            raise PermissionDenied("You don't have permission to view reports for this child.")
        return child

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tutor'] = self.request.user
        return context