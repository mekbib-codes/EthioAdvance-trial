from django.views.generic import DetailView, ListView, TemplateView
from django.db.models import OuterRef, Subquery, Prefetch
from django.shortcuts import get_object_or_404, render
from django.views.generic import CreateView, UpdateView
from django.views.generic.edit import View
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils.translation import gettext as _
from django.db.models import Count, Q

from .models import Child
from parent.models import Parent
from .forms import ChildRegistrationForm, ChildUpdateForm
from accounts.mixins import ParentorTutorRequiredMixin, ParentRequiredMixin
from session.models import Session
from report.models import Report

from actions.models import Notification
from actions.utils import create_notification, create_activity_log

import logging
logger = logging.getLogger('app')

class ChildRegistrationView(ParentRequiredMixin, CreateView):
    model = Child
    form_class = ChildRegistrationForm
    template_name = 'registration/child_register_form.html'
    success_url = reverse_lazy('parent:dashboard')
    
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['parent'] = Parent.objects.get(id=self.request.user.id)
        return kwargs

    def form_valid(self, form):
        logger.info(f"Parent {self.request.user} is registering a child.")
        response = super().form_valid(form)

        # Notify the company
        parent = Parent.objects.get(id=self.request.user.id)
        company = parent.profile.company  # Get the company from the parent's profile
        create_notification(
            actor=parent,
            verb=f"registered a new child: {form.instance.get_full_name()}.",
            content_object=form.instance,
            child=form.instance,
            recipients=[company],  # Notify only the company
            extra_data={
                "child_name": form.instance.get_full_name(),
                "registration_date": form.instance.created_at.isoformat(),
            },
            notification_type=Notification.NotificationTypes.SUCCESS,
        )

        messages.success(
        self.request,
        _("Successfully registered %(child_name)s!") % {'child_name': form.instance.get_full_name()}
    )
        return response
    
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
        context['existing_children'] = Child.objects.filter(parent=self.request.user)
        return context

class BaseChildrenDashboardView(ListView):
    model = Child
    template_name = None  # Override in subclass
    context_object_name = 'children'

    def get_queryset(self):
        # Subquery to get the latest session ID for each child
        latest_session_id = Session.objects.filter(
            child=OuterRef('pk')
        ).order_by('-created_at').values('id')[:1]

        # Base queryset for children
        queryset = Child.objects.annotate(
            latest_session_id=Subquery(latest_session_id)
        )

        # Prefetch the latest session for each child
        session_ids = [child.latest_session_id for child in queryset if child.latest_session_id]
        sessions = Session.objects.filter(
            id__in=session_ids
        ).select_related('child')

        queryset = queryset.prefetch_related(
            Prefetch('sessions', queryset=sessions, to_attr='latest_sessions')
        )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_section'] = 'dashboard'
        return context
  
class ChildDashboardView(ParentorTutorRequiredMixin, DetailView):
    model = Child
    template_name = 'child/child_dashboard.html'
    context_object_name = 'child'
    pk_url_kwarg = 'child_id'
    def get_object(self, queryset=None):
        child = super().get_object(queryset)
        return child

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['active_section'] = 'child_dashboard' 
        return context

class ChildProfileDashboardView(ParentRequiredMixin, DetailView):
    model = Child
    template_name = 'child/profile/dashboard.html'
    context_object_name = 'child'
    pk_url_kwarg = 'child_id'

    def get_object(self, queryset=None):
        child = super().get_object(queryset)
        return child

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        child = self.get_object()
        # Fetch related payments and sessions
        payments = child.payments.all()
        session_data = child.sessions.aggregate(
        
        total_sessions=Count('id'),
        pending_sessions=Count('id', filter=Q(status=Session.Status.PENDING)),
        approved_sessions=Count('id', filter=Q(status=Session.Status.APPROVED)),
        rejected_sessions=Count('id', filter=Q(status=Session.Status.REJECTED)),
    )

        total_payment = sum([payment.amount for payment in payments])

        context['user'] = self.request.user

        context['payments'] = payments
        context['total_payment'] = total_payment

        context['session_data'] = session_data

        context['active_section'] = 'profile' 
        return context

class ChildProfileUpdateView(ParentRequiredMixin, UpdateView):
    model = Child
    form_class = ChildUpdateForm
    template_name = 'child/profile/update.html'
    pk_url_kwarg = 'child_id'

    def get_object(self, queryset=None):
        # Fetch the child object using the child_id and ensure it belongs to the logged-in parent
        child = get_object_or_404(Child, id=self.kwargs.get(self.pk_url_kwarg), parent=self.request.user)
        logger.info(f"Child object fetched for update: {child} (ID: {child.id})")
        return child

    def get_success_url(self):
        # Dynamically generate the success URL with the child_id
        return reverse('child:profile_dashboard', kwargs={'child_id': self.object.id})

    def form_valid(self, form):
        # Get the original values before saving
        child = self.get_object()
        original_date_of_birth = child.date_of_birth
        original_grade_level = child.grade_level
        original_school = child.school

        # Save the form
        response = super().form_valid(form)

        # Check if any of the dob, grade or school were updated were updated
        updated_fields = []
        if form.cleaned_data['date_of_birth'] != original_date_of_birth:
            updated_fields.append('date_of_birth')
        if form.cleaned_data['grade_level'] != original_grade_level:
            updated_fields.append('grade_level')
        if form.cleaned_data['school'] != original_school:
            updated_fields.append('school')
        
        # If any of the above fields were updated, create a notification
        if updated_fields:
            parent = Parent.objects.get(id=self.request.user.id)
            company = parent.profile.company  # Get the company from the parent's profile
            create_notification(
                actor=self.request.user,
                verb=f"updated the profile of {child.get_full_name()}.",
                content_object=child,
                child=child,
                recipients=[company],  # Notify only the company
                extra_data={
                    "updated_fields": updated_fields,
                },
                notification_type=Notification.NotificationTypes.INFO,
            )
            logger.info(f"Notification created for child profile update: {updated_fields}")

        # Log the activity
        parent = self.request.user
        pronoun = 'his' if child.gender == 'MALE' else 'her'
        create_activity_log(
            user=parent,
            action=f"{ child.first_name } updated {pronoun} profile.",
            related_object=child,
            link='child:profile_dashboard',
            kwargs={'child_id': child.id}
        )

        logger.info(f"Child profile updated successfully: {self.object} (ID: {self.object.id})")
        messages.success(self.request, "Child profile updated successfully.")
        return response

    def form_invalid(self, form):
        # Log errors and add an error message
        logger.warning(f"Failed to update child profile: {form.errors}")
        messages.error(self.request, "There was an error updating the child profile. Please check the form and try again.")
        return super().form_invalid(form)
       
class AddReportFeedbackView(ParentRequiredMixin, View):
    def post(self, request, report_id, *args, **kwargs):
        report = get_object_or_404(Report, id=report_id)

        # Get the feedback from the POST request
        child_feedback = request.POST.get("child_feedback", "").strip()
        if child_feedback:
            report.feedback_from_child = child_feedback
            report.save()

            # Notify the tutor and company
            tutor = report.tutor
            company = tutor.profile.company
            recipients = [tutor, company]

            child = report.child
            create_notification(
                actor=request.user,
                verb=f"provided feedback on the report for {child.get_full_name()}.\n( Child Feedback. )",
                content_object=report,
                child=child,
                recipients=recipients,
                extra_data={
                    "feedback": child_feedback,
                    "report_date": report.created_at.isoformat(),
                },
                notification_type=Notification.NotificationTypes.INFO,
            )


            # Log the activity
            parent = self.request.user

            pronoun = 'his' if child.gender == 'MALE' else 'her'
            create_activity_log(
                user=parent,
                action=f"{ child.first_name } Gave feedback {pronoun} report.",
                related_object=report,
                link='parent:child_reports_dashboard',
                kwargs={'child_id': child.id}
            )

        # Render only the updated feedback block to be replaced dynamically
        return render(request, "child/reports/child_feedback_block.html", {"report": report})


class PaymentDashboardView(ListView):
    model = Child  # Paginate by Child
    template_name = None
    context_object_name = 'children'
    
    def get_context_data(self, **kwargs):
        """
        Add additional context data for the payment dashboard.
        """
        context = super().get_context_data(**kwargs)

        context.update({
            'active_section': 'payment',
        })

        logger.info(f"Payment dashboard accessed by {self.request.user.get_full_name()}")
        return context