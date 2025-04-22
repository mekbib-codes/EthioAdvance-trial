from django.views.generic import TemplateView
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import CreateView, UpdateView
from django.urls import reverse_lazy
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.translation import gettext as _
from django.conf import settings
from django.db.models import Count, Q

from accounts.mixins import CompanyRequiredMixin, TutorRequiredMixin
from accounts.views.base_registration import BaseRegistrationView
from accounts.models import User
from .forms import TutorRegistrationForm, SessionCreationForm, TutorProfileUpdateForm
from child.views import BaseChildrenDashboardView, PaymentDashboardView
from session.views import BaseSessionsDashboardView
from session.models import Session
from child.models import Child
from tutor.models import Tutor, TutorProfile
from report.views import BaseReportsDashboardView, BaseReportStepView
from report.forms import ReportSummaryForm, SessionInsightForm, QuizAssignmentForm, MockExamForm, ChallengesAndSolutionsForm
from payment.models import TutorPayments

from actions.models import Notification
from actions.utils import create_notification

import logging
from uuid import uuid4

logger = logging.getLogger('app')

class TutorDashboardView(TutorRequiredMixin, TemplateView):
    template_name = 'tutor/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            tutor = Tutor.objects.select_related("tutor_profile").get(id=self.request.user.id)

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

class TutorProfileDashboardView(TutorRequiredMixin, TemplateView):
    template_name = "tutor/profile/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tutor = Tutor.objects.select_related("tutor_profile").get(id=self.request.user.id)

        # Fetch the tutor's profile
        profile = getattr(tutor, "tutor_profile", None)

        # Fetch all students associated with the tutor and annotate session counts
        students = tutor.students.prefetch_related(
            "sessions",  # Prefetch sessions for each child
        ).annotate(
            total_sessions=Count("sessions"),
        )

        # Fetch all sessions associated with the tutor's students
        sessions = Session.objects.filter(child__in=students).select_related("child")

        # Fetch all earning made by the tutor
        earnings = tutor.tutor_payments.select_related("child")
        total_earning = sum([earning.amount for earning in earnings])
        # Aggregate session counts
        session_counts = sessions.aggregate(
            total_sessions=Count("id"),
            pending_sessions=Count("id", filter=Q(status=Session.Status.PENDING)),
            approved_sessions=Count("id", filter=Q(status=Session.Status.APPROVED)),
            rejected_sessions=Count("id", filter=Q(status=Session.Status.REJECTED)),
        )

        context.update({
            "tutor": tutor,
            "profile": profile,
            "children": students,
            "sessions": sessions,
            "earnings": earnings,
            'total_earning': total_earning,
            "session_counts": session_counts,
            "active_section": "profile",
        })

        return context

class TutorProfileUpdateView(TutorRequiredMixin, UpdateView):
    model = TutorProfile
    form_class = TutorProfileUpdateForm
    template_name = "tutor/profile/update.html"
    success_url = reverse_lazy("tutor:profile_dashboard")  # Redirect to the profile dashboard after update

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tutor'] = self.request.user
        return kwargs

    def get_object(self, queryset=None):
        # Ensure the logged-in user can only update their own profile
        return TutorProfile.objects.get(user=self.request.user)

    def form_valid(self, form):
        try:
            # Save the form and add a success message
            response = super().form_valid(form)
            messages.success(self.request, "Your profile has been updated successfully.")
            logger.info(f"Profile updated successfully for tutor: {self.request.user.get_full_name()} (ID: {self.request.user.id})")
            return response
        except Exception as e:
            # Log any unexpected errors
            logger.error(f"Error updating profile for tutor: {self.request.user.get_full_name()} (ID: {self.request.user.id}): {str(e)}", exc_info=True)
            messages.error(self.request, "An unexpected error occurred while updating your profile. Please try again later.")
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Add an error message if the form is invalid
        messages.error(self.request, "There was an error updating your profile. Please check the form and try again.")
        logger.warning(f"Profile update failed for tutor: {self.request.user.get_full_name()} (ID: {self.request.user.id}). Validation errors: {form.errors}")
        return super().form_invalid(form)
    
class StudentsDashboardView(TutorRequiredMixin, BaseChildrenDashboardView):
    template_name = 'tutor/students/dashboard.html'  # Tutor-specific template
    paginate_by = 4

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(tutor = Tutor.objects.select_related("tutor_profile").get(id=self.request.user.id))

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
        context['tutor'] = tutor = Tutor.objects.select_related("tutor_profile").get(id=self.request.user.id)
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

            # Notify the parent and company
            parent = self.child.parent
            company = parent.profile.company
            recipents = [parent, company]

            create_notification(actor=self.request.user,
                                verb=f'created {form.instance.session_subject } session with duration of { form.instance.formatted_duration() }.',
                                content_object=form.instance,
                                child=self.child,
                                recipients=recipents,
                                extra_data={
                },
                notification_type=Notification.NotificationTypes.INFO)
            

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
    success_url_name = 'report:create'

    def process_form_data(self, cleaned_data):
        report_data = self.request.session.get(REPORT_KEY, {})
        report_data.update({
            'challenges_encountered': cleaned_data['challenges_encountered'],
            'suggested_solutions': cleaned_data['suggested_solutions'],
        })
        self.request.session[REPORT_KEY] = report_data
        self.request.session.modified = True

class TutorPaymentDashboardView(TutorRequiredMixin, PaymentDashboardView):
    template_name = 'tutor/payment/dashboard.html'
    paginate_by = 6

    def get_queryset(self):
        tutor = self.request.user
        children = tutor.students.all()

        return children
    
    def get_context_data(self, **kwargs):
        """
        Add additional context data for the payment dashboard.
        """
        context = super().get_context_data(**kwargs)
        tutor = self.request.user
        children = tutor.students.all()

        context.update({
            'tutor': tutor,
            'children': children,
            'active_section': 'payment',
        })

        logger.info(f"Tutor Payment dashboard accessed by {tutor.get_full_name()}")
        return context
    
class TutorRequestPaymentView(View):
    """
    A view that allows tutors to request a payment.
    """
    def post(self, request, child_id, *args, **kwargs):
        try:
            # Fetch the child object and ensure it is assigned to the tutor
            child = get_object_or_404(Child, id=child_id, tutor=request.user)

            # Get the amount and session IDs from the request
            amount = request.POST.get('amount')
            session_ids = request.POST.getlist('sessions')

            # Validate the amount
            if not amount or float(amount) <= 0:
                messages.error(request, _("Invalid amount specified."))
                return redirect(reverse_lazy('tutor:payment_dashboard'))

            # Fetch the sessions
            sessions = Session.objects.filter(id__in=session_ids, child=child, tutor=request.user)

            if not sessions.exists():
                messages.error(request, _("No valid sessions found for this payment request."))
                return redirect(reverse_lazy('tutor:payment_dashboard'))
            
            tutor = Tutor.objects.get(id=request.user.id)
            # Create the TutorPayments record
            payment = TutorPayments.objects.create(
                tx_ref=str(uuid4()),  # Generate a unique transaction reference
                child=child,
                tutor=tutor,
                amount=amount,
                status=TutorPayments.STATUS.PENDING,  # Set status to pending
            )
            payment.sessions.set(sessions)  # Link the sessions to the payment

            # Notify the company
            company = tutor.profile.company
            create_notification(
                actor=tutor,
                verb=f"requested a payment of ${amount} for {child.get_full_name()}.",
                content_object=payment,
                child=child,
                recipients=[company],  # Notify only the company
                extra_data={
                    "payment_reference": payment.tx_ref,
                    "payment_amount": amount,
                },
                notification_type=Notification.NotificationTypes.INFO
            )

            # Add a success message and redirect
            messages.success(request, _("Payment request submitted successfully."))
            return redirect(reverse_lazy('tutor:payment_dashboard'))  # Redirect to a success page

        except Exception as e:
            # Log the error and show an error message
            logger.error(f"Error creating payment request: {str(e)}", exc_info=True)
            messages.error(request, _("An error occurred while processing your payment request. Please try again."))
            return redirect(reverse_lazy('tutor:payment_dashboard'))  # Redirect back to the dashboard