from django.views.generic import TemplateView
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import CreateView
from django.views import View
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from django.shortcuts import render, redirect
from django.conf import settings

from accounts.mixins import CompanyRequiredMixin, TutorRequiredMixin
from accounts.views.base_registration import BaseRegistrationView
from accounts.models import User
from .forms import TutorRegistrationForm, SessionCreationForm
from child.views import BaseChildrenDashboardView
from session.views import BaseSessionsDashboardView
from session.models import Session
from child.models import Child
from report.views import BaseReportsDashboardView
from report.forms import ReportSummaryForm, SessionInsightForm
from report.models import Strength, Weakness, Goal, LearningMaterial

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

REPORT_KEY = getattr(settings, 'REPORT_KEY', 'report_draft')

class ReportSummaryStepView(TutorRequiredMixin, View):
    template_name = 'tutor/reports/create_forms/summary.html'

    def dispatch(self, request, *args, **kwargs):
        # Fetch the child object and ensure it is assigned to the tutor
        self.child = get_object_or_404(Child, id=self.kwargs.get('child_id'))
        if self.child.tutor != self.request.user:
            logger.warning(f"Unauthorized report creation attempt by {request.user.email} for child {self.child.id}")
            raise PermissionDenied("You can only create reports for your assigned students.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Handle GET requests to display the form."""
        form = ReportSummaryForm()
        return render(request, self.template_name, {
            'form': form,
            'child': self.child
        })

    def post(self, request, *args, **kwargs):
        """Handle POST requests to process the form."""
        form = ReportSummaryForm(request.POST)
        if form.is_valid():
            try:
                # Save the form data to the session
                request.session[REPORT_KEY] = form.cleaned_data
                request.session.modified = True

                # Log success and show a success message
                logger.info(f"Report summary saved to session by {request.user.email} for child {self.child.id}")
                messages.success(request, f"Report summary for {self.child.get_full_name()} saved successfully.")
                return redirect(self.get_success_url())
            except Exception as e:
                # Log error and show an error message
                logger.error(f"Error saving report summary by {request.user.email} for child {self.child.id}: {str(e)}", exc_info=True)
                messages.error(request, "An error occurred while saving the report summary. Please try again.")
        else:
            # Handle form errors
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        logger.warning(f"Form error: {error}")
                        messages.error(request, _(f"{error}"), extra_tags='alert-danger')
                    else:
                        logger.warning(f"Field error - {field}: {error}")
                        label = form.fields[field].label
                        messages.error(request, _(f"{label}: {error}"), extra_tags='alert-danger')

        # Render the form again with errors
        return render(request, self.template_name, {
            'form': form,
            'child': self.child
        })

    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = {
            'child': self.child,
            'active_section': 'reports'
        }
        return context

    def get_success_url(self):
        """Redirect to the next step in the report creation process."""
        return reverse_lazy('tutor:create_sessions_insight_step', kwargs={'child_id': self.child.id})
    

class SessionInsightStepView(TutorRequiredMixin, View):
    template_name = 'tutor/reports/create_forms/sessions_insight.html'

    def dispatch(self, request, *args, **kwargs):
        self.child = get_object_or_404(Child, id=self.kwargs.get('child_id'))
        if self.child.tutor != self.request.user:
            logger.warning(f"Unauthorized insight attempt by {request.user.email} for child {self.child.id}")
            raise PermissionDenied("You can only add insights for your assigned students.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = SessionInsightForm()
        return render(request, self.template_name, {'form': form, 'child': self.child})

    def post(self, request, *args, **kwargs):
        form = SessionInsightForm(request.POST)
        if form.is_valid():
            try:
                cleaned = form.cleaned_data
                request.session[REPORT_KEY] = self._prepare_report_data(cleaned)
                request.session.modified = True

                logger.info(f"Session insight saved to session by {request.user.email} for child {self.child.id}")
                logger.debug(f"Report data - {request.session[REPORT_KEY]}")
                messages.success(request, f"Session insights for {self.child.get_full_name()} saved successfully.")
                return redirect(self.get_success_url())
            except Exception as e:
                logger.error(f"Error processing insights for {request.user.email}: {str(e)}", exc_info=True)
                messages.error(request, "An error occurred while saving the session insights. Please try again.")
        else:
            self._handle_form_errors(form)

        return render(request, self.template_name, {'form': form, 'child': self.child})

    def _prepare_report_data(self, cleaned_data):
        # Stores plain text in the session, no PK conversions.
        return {
            'strengths': cleaned_data['strengths'],
            'weaknesses': cleaned_data['weaknesses'],
            'goals_achieved': cleaned_data['goals_achieved'],
            'learning_material_prepared': cleaned_data['learning_material_prepared'],
            'child_participation': cleaned_data['child_participation'],
        }

    def _handle_form_errors(self, form):
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
        return reverse_lazy('tutor:child_reports_dashboard', kwargs={'child_id': self.child.id})
