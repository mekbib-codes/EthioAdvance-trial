from django.views.generic import TemplateView
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import View, UpdateView
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.contrib import messages

from accounts.mixins import ParentRequiredMixin
from accounts.views.base_registration import BaseRegistrationView
from accounts.models import User
from parent.models import ParentProfile, Parent
from parent.forms import ParentRegistrationForm, ParentProfileUpdateForm
from session.models import Session
from child.views import BaseChildrenDashboardView, PaymentDashboardView
from session.views import BaseSessionsDashboardView
from report.views import BaseReportsDashboardView
from report.models import Report
from payment.models import Payment
from actions.models import Notification, ActivityLog
from actions.utils import create_notification, create_activity_log


import logging
logger = logging.getLogger('app')

class ParentDashboardView(ParentRequiredMixin, TemplateView):
    template_name = 'parent/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            parent = Parent.objects.prefetch_related('testimonials', 'activity_logs').get(id=self.request.user.id)
            testimonials = parent.testimonials.filter(show_testimonial=True).exclude(parent=parent)[:3]
            activities = ActivityLog.objects.filter(user=parent)[:5]
            
            context.update({
                'parent': parent,
                'testimonials': testimonials,
                'activities': activities,
                'active_section': 'dashboard',
            })
            
            logger.info(
                f"Parent dashboard accessed by {parent.get_full_name()} "
            )
            return context
            
        except Exception as e:
            logger.error(
                f"Parent dashboard error for {self.request.user.get_full_name()}: {str(e)}",
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

class ParentProfileDashboardView(ParentRequiredMixin, TemplateView):
    template_name = "parent/profile/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parent = Parent.objects.select_related("parent_profile").prefetch_related("children", "payments").get(id=self.request.user.id)

        # Fetch the parent's profile
        profile = getattr(parent, "parent_profile", None)

        # Fetch all children associated with the parent and annotate session counts
        children = parent.children.prefetch_related(
            "sessions",  # Prefetch sessions for each child
        ).annotate(
            total_sessions=Count("sessions"),
        )

        # Fetch all sessions associated with the parent's children
        sessions = Session.objects.filter(child__in=children).select_related("child")

        # Fetch all payments made by the parent
        payments = parent.payments.select_related("child").filter(status=Payment.STATUS.SUCCESS)
        total_payment = sum([payment.amount for payment in payments])

        # Aggregate session counts
        session_counts = sessions.aggregate(
            total_sessions=Count("id"),
            pending_sessions=Count("id", filter=Q(status=Session.Status.PENDING)),
            approved_sessions=Count("id", filter=Q(status=Session.Status.APPROVED)),
            rejected_sessions=Count("id", filter=Q(status=Session.Status.REJECTED)),
        )

        context.update({
            "parent": parent,
            "profile": profile,
            "children": children,
            "sessions": sessions,
            "payments": payments,
            'total_payment': total_payment,
            "session_counts": session_counts,
            "active_section": "profile",
        })

        return context

class ParentProfileUpdateView(ParentRequiredMixin, UpdateView):
    model = ParentProfile
    form_class = ParentProfileUpdateForm
    template_name = "parent/profile/update.html"
    success_url = reverse_lazy("parent:profile_dashboard")  # Redirect to the profile dashboard after update

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['parent'] = self.request.user  # Pass the parent instance to the form
        return kwargs

    def get_object(self, queryset=None):
        # Ensure the logged-in user can only update their own profile
        return ParentProfile.objects.get(user=self.request.user)

    def form_valid(self, form):
        try:
            # Save the form and add a success message
            response = super().form_valid(form)

            # Log the activity
            parent = self.request.user
            create_activity_log(
                user=parent,
                action="Updated your profile",
                related_object=parent,
                link='parent:profile_dashboard'
            )

            messages.success(self.request, "Your profile has been updated successfully.")
            logger.info(f"Profile updated successfully for parent: {parent.get_full_name()}")
            return response
        except Exception as e:
            # Log any unexpected errors
            logger.error(f"Error updating profile for parent: {self.request.user.get_full_name()}: {str(e)}", exc_info=True)
            messages.error(self.request, "An unexpected error occurred while updating your profile. Please try again later.")
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Add an error message if the form is invalid
        messages.error(self.request, "There was an error updating your profile. Please check the form and try again.")
        logger.warning(f"Profile update failed for parent: {self.request.user.get_full_name()} (ID: {self.request.user.id}). Validation errors: {form.errors}")
        return super().form_invalid(form)
    
class ChildrenDashboardView(ParentRequiredMixin, BaseChildrenDashboardView):
    template_name = 'parent/children/dashboard.html'  # Parent-specific template
    paginate_by = 6

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(parent = Parent.objects.get(id=self.request.user.id))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent'] = self.request.user
        context['active_section'] = 'my_children'
        return context
    
class UpdateSessionStatusView(ParentRequiredMixin, View):

    def post(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(Session, id=session_id)

        # Validate the status
        status = self.kwargs.get("status")
        if status in ["approved", "rejected"]:
            session.status = status
            session.save()

            # Determine the notification type based on the status
            notification_type = (
                Notification.NotificationTypes.SUCCESS
                if status == Session.Status.APPROVED
                else Notification.NotificationTypes.ERROR
            )

            # Notify the tutor and company
            tutor = session.tutor
            child = session.child
            company = tutor.profile.company
            recipients = [tutor, company]

            create_notification(
                actor=request.user,
                verb=f"updated the session status to {status} for {session.child.get_full_name()}.",
                content_object=session,
                child=session.child,
                recipients=recipients,
                extra_data={
                    'company_link': 'company:child_sessions_dashboard',
                    'company_link_kwargs': {'child_id': child.id},
                    'tutor_link': 'tutor:child_sessions_dashboard',
                    'tutor_link_kwargs': {'child_id': child.id}
                },
                notification_type=notification_type,
            )

            # Log the activity
            parent = self.request.user
            create_activity_log(
                user=parent,
                action=f"Updated session status to {status} for { session.child.first_name }",
                related_object=session,
                link='parent:child_sessions_dashboard',
                kwargs={'child_id': session.child.id}
            )
            
            # Render only the updated session block to be replaced dynamically
            return render(request, "parent/sessions/status_update/session_block.html", {"session": session})

        return HttpResponse("Invalid status", status=400)
    
class ParentSessionsDashboardView(ParentRequiredMixin, BaseSessionsDashboardView):
    template_name = 'parent/sessions/dashboard.html'  # Parent-specific template

    def get_child(self):
        """Fetch the child object and ensure it belongs to the parent."""
        child = super().get_child()
        if child.parent != self.request.user:
            raise PermissionDenied("You don't have permission to view sessions for this child.")
        return child

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent'] = self.request.user
        return context

class ParentReportsDashboardView(ParentRequiredMixin, BaseReportsDashboardView):
    template_name = 'parent/reports/dashboard.html'  # Parent-specific template

    def get_child(self):
        """Fetch the child object and ensure it belongs to the parent."""
        child = super().get_child()
        if child.parent != self.request.user:
            raise PermissionDenied("You don't have permission to view reports for this child.")
        return child

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent'] = self.request.user
        return context
    
class AddReportFeedbackView(ParentRequiredMixin, View):
    def post(self, request, report_id, *args, **kwargs):
        report = get_object_or_404(Report, id=report_id)

        # Get the feedback from the POST request
        parent_feedback = request.POST.get("parent_feedback", "").strip()
        if parent_feedback:
            report.feedback_from_parent = parent_feedback
            report.save()

            # Notify the tutor and company
            tutor = report.tutor
            child = report.child
            company = tutor.profile.company
            recipients = [tutor, company]

            create_notification(
                actor=request.user,
                verb=f"provided feedback on the report for {report.child.get_full_name()}.",
                content_object=report,
                child=report.child,
                recipients=recipients,
                extra_data={
                    'company_link': 'company:child_reports_dashboard',
                    'company_link_kwargs': {'child_id': child.id},
                    'tutor_link': 'tutor:child_reports_dashboard',
                    'tutor_link_kwargs': {'child_id': child.id}
                },
                notification_type=Notification.NotificationTypes.INFO,
            )

            # Log the activity
            parent = self.request.user
            create_activity_log(
                user=parent,
                action=f"Gave feedback on the report of { report.child.first_name }",
                related_object=report,
                link='parent:child_reports_dashboard',
                kwargs={'child_id': report.child.id}
            )

        # Render only the updated feedback block to be replaced dynamically
        return render(request, "parent/reports/parent_feedback_block.html", {"report": report})
    
class ParentPaymentDashboardView(ParentRequiredMixin, PaymentDashboardView):
    template_name = 'parent/payment/dashboard.html'
    paginate_by = 6

    def get_queryset(self):
        parent = Parent.objects.get(id=self.request.user.id)
        # Annotate children with total_due and unpaid_sessions
        children = parent.children.all()
        
        return children
    
    def get_context_data(self, **kwargs):
        """
        Add additional context data for the payment dashboard.
        """
        context = super().get_context_data(**kwargs)
        parent = self.request.user
        children = self.get_queryset()

        context.update({
            'parent': parent,
            'children': children,
            'active_section': 'payment',
        })

        logger.info(f"Parent Payment dashboard accessed by {parent.get_full_name()}")
        return context