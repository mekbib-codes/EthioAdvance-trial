from django.views.generic import ListView
from django.views import View
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.conf import settings

from child.models import Child
from .models import Report, Strength, Weakness, Goal, LearningMaterial, ChallengeEncountered,SuggestedSolution
from accounts.mixins import TutorRequiredMixin

import logging
from datetime import datetime, timedelta

from actions.models import Notification
from actions.utils import create_notification, create_activity_log

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

REPORT_KEY = getattr(settings, 'REPORT_KEY', 'report_draft')

class CreateReportView(TutorRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        child = get_object_or_404(Child, id=self.kwargs.get('child_id'))
        if child.tutor != request.user:
            logger.warning(f"Unauthorized report finalization attempt by {request.user.email} for child {child.id}")
            raise PermissionDenied("You are not allowed to finalize reports for this student.")

        report_data = request.session.get(REPORT_KEY)

        if not report_data:
            logger.error(f"Report data missing in session for {request.user.email} and child {child.id}")
            messages.error(request, "No report data found. Please complete the report steps first.")
            return redirect('tutor:child_reports_dashboard', child_id=child.id)

        try:
            # Convert from_date and to_date to datetime objects
            from_date = datetime.fromisoformat(report_data.get('from_date')) if report_data.get('from_date') else None
            to_date = datetime.fromisoformat(report_data.get('to_date')) if report_data.get('to_date') else None

            # Convert average_duration_per_session to timedelta object
            avg_duration_str = report_data.get('average_duration_per_session')
            average_duration_per_session = None
            if avg_duration_str:
                hours, minutes, seconds = map(int, avg_duration_str.split(':'))
                average_duration_per_session = timedelta(hours=hours, minutes=minutes, seconds=seconds)

            report = Report.objects.create(
                child=child,
                tutor=request.user,
                from_date=from_date,
                to_date=to_date,
                total_sessions_conducted=report_data.get('total_sessions_conducted'),
                average_duration_per_session=average_duration_per_session,
                child_participation=report_data.get('child_participation'),
                number_of_quizzes_prepared=report_data.get('number_of_quizzes_prepared'),
                average_quiz_score=report_data.get('average_quiz_score'),
                completion_percentage=report_data.get('completion_percentage'),
                completion_notes=report_data.get('completion_notes'),
                number_of_mock_exams_prepared=report_data.get('number_of_mock_exams_prepared'),
                mock_exam_result_overview=report_data.get('mock_exam_result_overview'),
                mock_exam_strengths=report_data.get('mock_exam_strengths'),
                mock_exam_improvement_areas=report_data.get('mock_exam_improvement_areas'),
            )

            # Handle many-to-many fields
            for field_name, model_class in [
                ('strengths', Strength),
                ('weaknesses', Weakness),
                ('goals_achieved', Goal),
                ('learning_material_prepared', LearningMaterial),
                ('challenges_encountered', ChallengeEncountered),
                ('suggested_solutions', SuggestedSolution)
            ]:
                items = report_data.get(field_name, [])
                for item in items:
                    obj, _ = model_class.objects.get_or_create(name=item)
                    getattr(report, field_name).add(obj)
                
            # Create a notification for the parent and company
            parent = child.parent
            company = parent.profile.company
            recipients = [parent, company]

            create_notification(
                actor=request.user,
                verb=f'created a report for {child.get_full_name()}.',
                content_object=report,
                child=child,
                recipients=recipients,
                extra_data={
                    'parent_link': "parent:child_reports_dashboard",
                    'parent_link_kwargs': {'child_id': child.id},
                    'company_link': 'company:child_reports_dashboard',
                    'company_link_kwargs': {'child_id': child.id},
                },
                notification_type=Notification.NotificationTypes.INFO
            )

            # Log the activity
            create_activity_log(
                user=self.request.user,
                action=f"Created report for { self.child.get_full_name() }",
                related_object=report,
                link='tutor:child_reports_dashboard',
                kwargs={'child_id': self.child.id}
            )

            logger.info(f"Report successfully created by {request.user.email} for child {child.id}")
            messages.success(request, f"Report for {child.get_full_name()} created successfully.")

            # Clear session data to avoid duplicate saves
            request.session.pop(REPORT_KEY, None)

        except Exception as e:
            logger.error(f"Error creating report for {request.user.email}: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while finalizing the report. Please contact support.")
            return redirect('tutor:child_reports_dashboard', child_id=child.id)

        return redirect('tutor:child_reports_dashboard', child_id=child.id)
