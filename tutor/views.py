from django.views.generic import TemplateView
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext as _
from django.conf import settings

from accounts.mixins import CompanyRequiredMixin, TutorRequiredMixin
from accounts.views.base_registration import BaseRegistrationView
from accounts.models import User
from .forms import TutorRegistrationForm, SessionCreationForm
from child.views import BaseChildrenDashboardView
from session.views import BaseSessionsDashboardView
from session.models import Session
from child.models import Child
from report.views import BaseReportsDashboardView, BaseReportStepView
from report.forms import ReportSummaryForm, SessionInsightForm, QuizAssignmentForm, MockExamForm, ChallengesAndSolutionsForm

import logging
logger = logging.getLogger('app')

class TutorDashboardView(TutorRequiredMixin, TemplateView):
    template_name = 'tutor/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            tutor = self.request.user

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

class ReportSummaryStepView(BaseReportStepView):
    template_name = 'tutor/reports/create_forms/summary.html'
    form_class = ReportSummaryForm
    success_url_name = 'tutor:create_sessions_insight_step'

    def process_form_data(self, cleaned_data):
        # Save the form data to the session
        self.request.session[REPORT_KEY] = cleaned_data
        self.request.session.modified = True

class SessionInsightStepView(BaseReportStepView):
    template_name = 'tutor/reports/create_forms/sessions_insight.html'
    form_class = SessionInsightForm
    success_url_name = 'tutor:create_quiz_assignment_step'

    def process_form_data(self, cleaned_data):
        # Update session data with session insights
        report_data = self.request.session.get(REPORT_KEY, {})
        report_data.update({
            'strengths': cleaned_data['strengths'],
            'weaknesses': cleaned_data['weaknesses'],
            'goals_achieved': cleaned_data['goals_achieved'],
            'learning_material_prepared': cleaned_data['learning_material_prepared'],
            'child_participation': cleaned_data['child_participation'],
        })
        self.request.session[REPORT_KEY] = report_data
        self.request.session.modified = True

class QuizAssignmentInsightStepView(BaseReportStepView):
    template_name = 'tutor/reports/create_forms/quiz_and_assignments.html'
    form_class = QuizAssignmentForm
    success_url_name = 'tutor:create_mock_exam_step'

    def process_form_data(self, cleaned_data):
        # Update session data with quiz and assignment insights
        report_data = self.request.session.get(REPORT_KEY, {})
        report_data.update({
            'number_of_quizzes_prepared': cleaned_data['number_of_quizzes_prepared'],
            'average_quiz_score': cleaned_data['average_quiz_score'],
            'completion_percentage': cleaned_data['completion_percentage'],
            'completion_notes': cleaned_data['completion_notes'],
        })
        self.request.session[REPORT_KEY] = report_data
        self.request.session.modified = True

class MockExamInsightStepView(BaseReportStepView):
    template_name = 'tutor/reports/create_forms/mock_exam_insight.html'
    form_class = MockExamForm
    success_url_name = 'tutor:create_challenges_and_solutions_step'

    def process_form_data(self, cleaned_data):
        report_data = self.request.session.get(REPORT_KEY, {})
        report_data.update({
            'number_of_mock_exams_prepared': cleaned_data['number_of_mock_exams_prepared'],
            'mock_exam_result_overview': cleaned_data['mock_exam_result_overview'],
            'mock_exam_strengths': cleaned_data['mock_exam_strengths'],
            'mock_exam_improvement_areas': cleaned_data['mock_exam_improvement_areas'],
        })
        self.request.session[REPORT_KEY] = report_data
        self.request.session.modified = True

class ChallengesAndSolutionsStepView(BaseReportStepView):
    template_name = 'tutor/reports/create_forms/challenges_and_solutions.html'
    form_class = ChallengesAndSolutionsForm
    success_url_name = 'tutor:child_reports_dashboard'  # assuming dashboard is next!

    def process_form_data(self, cleaned_data):
        report_data = self.request.session.get(REPORT_KEY, {})
        report_data.update({
            'challenges_encountered': cleaned_data['challenges_encountered'],
            'suggested_solutions': cleaned_data['suggested_solutions'],
        })
        self.request.session[REPORT_KEY] = report_data
        self.request.session.modified = True
