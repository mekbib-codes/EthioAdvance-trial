from django.views.generic import TemplateView
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import View
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse

from accounts.mixins import ParentRequiredMixin
from accounts.views.base_registration import BaseRegistrationView
from accounts.models import User
from .forms import ParentRegistrationForm
from session.models import Session
from child.views import BaseChildrenDashboardView, PaymentDashboardView
from session.views import BaseSessionsDashboardView
from report.views import BaseReportsDashboardView
from report.models import Report
from payment.models import Payment

import logging
logger = logging.getLogger('app')

class ParentDashboardView(ParentRequiredMixin, TemplateView):
    template_name = 'parent/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            parent = self.request.user

            context.update({
                'parent': parent,
                'active_section': 'dashboard',
            })
            
            logger.info(
                f"Parent dashboard accessed by {parent.get_full_name()} "
            )
            return context
            
        except Exception as e:
            logger.error(
                f"Parent dashboard error for {parent.get_full_name()}: {str(e)}",
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

class ChildrenDashboardView(ParentRequiredMixin, BaseChildrenDashboardView):
    template_name = 'parent/children/dashboard.html'  # Parent-specific template

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(parent=self.request.user)

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

        # Render only the updated feedback block to be replaced dynamically
        return render(request, "parent/reports/parent_feedback_block.html", {"report": report})
    
class ParentPaymentDashboardView(ParentRequiredMixin, PaymentDashboardView):
    template_name = 'parent/payment/dashboard.html'
    paginate_by = 2

    def get_queryset(self):
        parent = self.request.user
        children = parent.children.all()

        return children
    
    def get_context_data(self, **kwargs):
        """
        Add additional context data for the payment dashboard.
        """
        context = super().get_context_data(**kwargs)
        parent = self.request.user
        children = parent.children.all()

        context.update({
            'parent': parent,
            'children': children,
            'active_section': 'payment',
        })

        logger.info(f"Parent Payment dashboard accessed by {parent.get_full_name()}")
        return context