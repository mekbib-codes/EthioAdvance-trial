from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.views.generic import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db import models

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
            
        rate = self.get_current_rate()
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
            ).values('child__tutor_id').annotate(
                duration_sum=Coalesce(Sum('duration'), timedelta())
            ).values_list('child__tutor_id', 'duration_sum')
        )

        for tutor in tutors:
            tutor.total_paid = payment_totals.get(tutor.id, Decimal(0))
            tutor.total_requested = requested_totals.get(tutor.id, Decimal(0))

            duration = unpaid_durations.get(tutor.id, timedelta())
            tutor.total_due = self.calculate_due_amount(duration, rate)
            
        return tutors
    
    def get_current_rate(self):
        try:
            return Decimal(TutorPayRate.objects.latest("updated_at").current_hourly_rate)
        except TutorPayRate.DoesNotExist:
            logger.error("No Session Rate Found")
            return Decimal(0)
    
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
    
    def get_success_url(self):
        return reverse('company:tutors')
    
class ToggleTutorStatusView(View):
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
    
# class TutorDetailView(BaseUserDetailView):
#     model = Tutor
#     template_name = 'company/tutor/detail.html'
#     profile_relation = 'tutor_profile'
    
#     def get_specific_context_data(self, tutor):
#         sessions = tutor.sessions.all()
#         session_data = self._calculate_session_stats(sessions)
        
#         # Payment information
#         payment_data = self._calculate_payment_info(tutor, sessions)
        
#         # Children and related data
#         children = tutor.students.all()
#         payments = tutor.tutor_payments.all()
#         feedbacks = tutor.feedbacks.filter(status=Feedback.FeedbackStatus.OPEN)[:3]
        
#         return {
#             'parent': tutor,
#             'session_data': session_data,
#             'payment_data': payment_data,
#             'feedbacks': feedbacks,
#             'payments': payments,
#             'children': children,
#         }
    
#     def _calculate_session_stats(self, sessions):
#         status_counts = {
#             'total': sessions.count(),
#             'pending': sessions.filter(status=Session.Status.PENDING),
#             'approved': sessions.filter(status=Session.Status.APPROVED),
#             'rejected': sessions.filter(status=Session.Status.REJECTED),
#         }
        
#         data = {
#             f'{key}_sessions': qs.count() if isinstance(qs, models.QuerySet) else qs
#             for key, qs in status_counts.items()
#         }
        
#         # Add durations
#         for status in ['pending', 'approved', 'rejected']:
#             data[f'{status}_duration'] = status_counts[status].aggregate(
#                 total=Sum('duration')
#             )['total'] or timedelta(0)
        
#         data['total_duration'] = sessions.aggregate(total=Sum('duration'))['total'] or timedelta(0)
#         data['recent_sessions'] = sessions.order_by('-created_at')[:5]
        
#         # Calculate percentages
#         total = data['total_sessions'] or 1
#         for status in ['approved', 'pending', 'rejected']:
#             data[f'{status}_percentage'] = round((data[f'{status}_sessions'] / total) * 100)
            
#         return data
    
#     def _calculate_payment_info(self, tutor, sessions):
#         success_payments = tutor.tutor_payments.filter(status=TutorPayments.STATUS.SUCCESS)
#         total_earned = success_payments.aggregate(total=Sum('amount'))['total'] or Decimal(0)
        
#         unpaid_sessions = sessions.filter(
#             status=Session.Status.APPROVED,
#             paid_to_tutor=False
#         )
#         unpaid_duration = unpaid_sessions.aggregate(total=Sum('duration'))['total'] or timedelta(0)
        
#         try:
#             rate = Decimal(TutorPayRate.objects.latest("updated_at").current_hourly_rate)
#         except TutorPayRate.DoesNotExist:
#             rate = Decimal(0)
#             logger.warning("No TutorPayRate found")
        
#         total_unpaid = round(Decimal(unpaid_duration.total_seconds() / 3600) * rate, 2) if unpaid_duration else Decimal(0)
#         total_requested = tutor.tutor_payments.filter(status=TutorPayments.STATUS.PENDING)
        
#         return {
#             'total_earned': total_earned,
#                 'total_requested': total_requested,
#                 'total_unpiad': total_unpaid,
#                 'paid_sessions': 
#                 'unpaid_sessions': unpaid_sessions.count(),
#                 'paid_sessions_duration': paid_sessions_duration,
#                 'unpaid_sessions_duration': unpaid_sessions_duration,
#                 'hourly_rate': rate  # Include for transparency
#         }