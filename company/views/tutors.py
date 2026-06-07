from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.views.generic import View, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib import messages

from accounts.mixins import CompanyRequiredMixin
from accounts.views.user_list_view import BaseUserListView
from tutor.models import Tutor
from accounts.models import User
from payment.models import TutorPayRate, TutorPayments
from session.models import Session
from company.forms.notification_forms import TutorNotificationForm
from company.views.send_notifications import BaseNotificationView
from company.services.email_services.send_emails import EmailService
from feedbacks.models import Feedback
from payment.models import TutorPayments

from decimal import Decimal
from datetime import timedelta

import logging
logger = logging.getLogger('app')

class TutorBaseListView(BaseUserListView):
    model = Tutor
    template_name = 'company/tutor/list.html'
    role_filter = User.Role.TUTOR
    context_object_name = 'tutors'
    financial_calculations = True
    annotate_fields = {
        'total_students': Count('students', distinct=True),
        'total_sessions': Count('students__sessions', distinct=True),
        'total_reports': Count('students__report', distinct=True),
        'total_feedbacks': Count('feedbacks', distinct=True),
    }

    def get_base_queryset(self):
        """Company-specific tutor filtering"""
        return super().get_base_queryset().filter(
            tutor_profile__company=self.request.user
        ).select_related('tutor_profile')
    
    def calculate_financials(self, tutors):
        if not tutors:
            return tutors
        
        tutor_ids = [tutor.id for tutor in tutors]

        # Payment totals
        payment_totals = dict(
            TutorPayments.objects.filter(
                tutor_id__in=tutor_ids,
                status=TutorPayments.STATUS.SUCCESS
            ).values('tutor_id').annotate(
                total=Coalesce(Sum('amount'), Decimal(0))
            ).values_list('tutor_id', 'total')
        )

        # Requested Total
        requested_totals = dict(
            TutorPayments.objects.filter(
                tutor_id__in=tutor_ids,
                status=TutorPayments.STATUS.PENDING
            ).values('tutor_id').annotate(
                total=Coalesce(Sum('amount'), Decimal(0))
            ).values_list('tutor_id', 'total')
        )

        # Unpaid durations
        unpaid_durations = dict(
            Session.objects.filter(
                child__tutor_id__in=tutor_ids,
                status=Session.Status.APPROVED,
                paid_to_tutor=False
            )
            .values('child_id')
            .annotate(
                duration_sum=Coalesce(Sum('duration'), timedelta())
            )
            .values_list('child_id', 'duration_sum')
        )

        tutor_rate_table = TutorPayRate.objects.latest("updated_at")
        for tutor in tutors:
            tutor.total_paid = payment_totals.get(tutor.id, Decimal(0))
            tutor.total_requested = requested_totals.get(tutor.id, Decimal(0))

            total_due = Decimal(0)

            for child in tutor.students.all():
                duration = unpaid_durations.get(
                    child.id,
                    timedelta()
                )

                rate = tutor_rate_table.get_current_hourly_rate(child)

                total_due += self.calculate_due_amount(
                    duration,
                    rate
                )

            tutor.total_due = total_due
            
        return tutors
    
    def calculate_due_amount(self, duration, rate):
        if not duration:
            return Decimal(0)
        total_hours = duration.total_seconds() / 3600
        return round(Decimal(total_hours) * rate, 2)
    
class TutorListView(TutorBaseListView):
    """Default tutor listing without search"""
    def get_queryset(self):
        queryset = self.get_base_queryset()
        queryset = self.apply_annotations(queryset)
        return self.calculate_financials(list(queryset))

class TutorSearchView(TutorBaseListView):
    """Tutor lisitng with search capabilities"""
    pass

class TutorNotificationView(BaseNotificationView):
    template_name = 'company/parent/bulk_notification.html'
    form_class = TutorNotificationForm
    user_type = 'TUTOR'
    user_profile_relation = 'tutor_profile'
    
    def get_notification_data(self, message_type, custom_message=None):
        data = {
            'feedback_request': {
                'verb': " - Friendly request to provide your feedback about the website.",
                'link': 'feedbacks:submit',
            },
            'custom': {
                'verb': f"- {custom_message}",
                'link': 'tutor:dashboard',
            }
        }
        return data[message_type]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_section'] = 'tutors'
        return context
    
    def get_success_url(self):
        return reverse('company:tutors')
    
class ToggleTutorStatusView(CompanyRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        tutor = get_object_or_404(
            get_user_model(),
            pk=kwargs['tutor_id'],
            role='TUTOR',
            tutor_profile__company=request.user
        )
        
        was_active = tutor.is_active
        tutor.is_active = not was_active
        tutor.save()
        
        # Send appropriate email
        context = {
            'user': tutor,
            'role': 'tutor',
            'company': request.user.get_full_name(),
            'support_url': 'https://ethioadvance.com/contact', # request.build_absolute_uri(reverse('contact_support')),
            'login_url': request.build_absolute_uri(reverse('accounts:login')),
            'home_url': request.build_absolute_uri(reverse('accounts:home')),
        }
        
        if was_active:
            EmailService.send_email(
                subject="Your Account Has Been Deactivated",
                to_emails=[tutor.email],
                template_name="company/emails/deactivated",
                context=context
            )
            action = "deactivated"
            logger.info(f"Account Deactivated for tutor - {tutor.get_full_name()} - Email sent successfully")
        else:
            EmailService.send_email(
                subject="Your Account Has Been Reactivated",
                to_emails=[tutor.email],
                template_name="company/emails/activated",
                context=context
            )
            action = "activated"
            logger.info(f"Account Activated for tutor - {tutor.get_full_name()} - Email sent successfully")
        
        messages.success(request, f"Tutor {action} successfully")
        return redirect('company:tutors')
    
class TutorDetailView(CompanyRequiredMixin, DetailView):
    model = Tutor
    template_name = 'company/tutor/detail.html'
    pk_url_kwarg = 'tutor_id'

    def get_context_data(self, **kwargs):
        tutor = self.object
        
        # Children and related data
        students = tutor.students.only('id', 'first_name', 'last_name').prefetch_related('sessions')
        payments = tutor.tutor_payments.filter(status=TutorPayments.STATUS.SUCCESS)
        feedbacks = tutor.feedbacks.filter(status=Feedback.FeedbackStatus.OPEN)[:3]
        
        return {
            'tutor': tutor,
            'feedbacks': feedbacks,
            'payments': payments,
            'students': students,
        }