from django.db.models import Count, Sum
from django.views.generic import View, DetailView
from django.db.models.functions import Coalesce
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.db import models

from decimal import Decimal
from datetime import timedelta

from accounts.mixins import CompanyRequiredMixin
from accounts.views.user_list_view import BaseUserListView
from accounts.models import User
from parent.models import Parent
from payment.models import SessionRate, Payment
from session.models import Session
from feedbacks.models import Feedback
from company.services.email_services.send_emails import EmailService
from company.views.send_notifications import BaseNotificationView
from company.forms.notification_forms import ParentNotificationForm

import logging
logger = logging.getLogger('app')

class ParentListBaseView(BaseUserListView):
    model = Parent
    template_name = 'company/parent/list.html'
    role_filter = User.Role.PARENT
    context_object_name = 'parents'
    financial_calculations = True
    annotate_fields = {
        'total_children': Count('children', distinct=True),
        'total_sessions': Count('children__sessions', distinct=True),
        'total_reports': Count('children__report', distinct=True),
        'total_testimonials': Count('testimonials', distinct=True),
        'total_feedbacks': Count('feedbacks', distinct=True),
    }
    
    def get_base_queryset(self):
        """Company-specific parent filtering"""
        return super().get_base_queryset().filter(
            parent_profile__company=self.request.user
        ).select_related('parent_profile')

    def calculate_financials(self, parents):
        if not parents:
            return parents
            
        rate = self.get_current_rate()
        parent_ids = [parent.id for parent in parents]

        # Payment totals
        payment_totals = dict(
            Payment.objects.filter(
                parent_id__in=parent_ids,
                status=Payment.STATUS.SUCCESS
            ).values('parent_id').annotate(
                total=Coalesce(Sum('amount'), Decimal(0))
            ).values_list('parent_id', 'total')
        )

        # Unpaid durations
        unpaid_durations = dict(
            Session.objects.filter(
                child__parent_id__in=parent_ids,
                status=Session.Status.APPROVED,
                is_paid=False
            ).values('child__parent_id').annotate(
                duration_sum=Coalesce(Sum('duration'), timedelta())
            ).values_list('child__parent_id', 'duration_sum')
        )

        for parent in parents:
            parent.total_paid = payment_totals.get(parent.id, Decimal(0))
            duration = unpaid_durations.get(parent.id, timedelta())
            parent.total_due = self.calculate_due_amount(duration, rate)
            
        return parents

    def get_current_rate(self):
        try:
            return Decimal(SessionRate.objects.latest("updated_at").current_hourly_rate)
        except SessionRate.DoesNotExist:
            logger.error("No Session Rate Found")
            return Decimal(0)

    def calculate_due_amount(self, duration, rate):
        if not duration:
            return Decimal(0)
        total_hours = duration.total_seconds() / 3600
        return round(Decimal(total_hours) * rate, 2)
    
class ParentListView(ParentListBaseView):
    """Default parent listing without search"""
    def get_queryset(self):
        queryset = self.get_base_queryset()
        queryset = self.apply_annotations(queryset)
        return self.calculate_financials(list(queryset))

class ParentSearchView(ParentListBaseView):
    """Parent listing with search capabilities"""
    pass

class ParentNotificationView(BaseNotificationView):
    template_name = 'company/parent/bulk_notification.html'
    form_class = ParentNotificationForm
    user_type = 'PARENT'
    user_profile_relation = 'parent_profile'
    
    def get_notification_data(self, message_type, custom_message=None):
        data = {
            'feedback_request': {
                'verb': " - Friendly request to provide your feedback about the website.",
                'link': 'feedbacks:submit',
            },
            'testimonial_request': {
                'verb': "- Friendly request to provide a testimonial.",
                'link': 'testimonials:submit',
            },
            'payment_reminder': {
                'verb': "- Friendly Payment overdue reminder.",
                'link': 'parent:payment_dashboard',
            },
            'custom': {
                'verb': f"- {custom_message}",
                'link': 'parent:dashboard',
            }
        }
        return data[message_type]
    
    def get_success_url(self):
        return reverse('company:parents')
    
class ToggleParentStatusView(CompanyRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        parent = get_object_or_404(
            get_user_model(),
            pk=kwargs['parent_id'],
            role='PARENT',
            parent_profile__company=request.user
        )
        
        was_active = parent.is_active
        parent.is_active = not was_active
        parent.save()
        
        # Send appropriate email
        context = {
            'user': parent,
            'role': 'parent',
            'company': request.user.get_full_name(),
            'support_url': 'https://ethioadvance.com/contact', # request.build_absolute_uri(reverse('contact_support')),
            'login_url': request.build_absolute_uri(reverse('accounts:login')),
            'home_url': request.build_absolute_uri(reverse('accounts:home')),
        }
        
        if was_active:
            EmailService.send_email(
                subject="Your Account Has Been Deactivated",
                to_emails=[parent.email],
                template_name="company/emails/deactivated",
                context=context
            )
            action = "deactivated"
            logger.info(f"Account Deactivated for parent - {parent.get_full_name()} - Email sent successfully")
        else:
            EmailService.send_email(
                subject="Your Account Has Been Reactivated",
                to_emails=[parent.email],
                template_name="company/emails/activated",
                context=context
            )
            action = "activated"
            logger.info(f"Account Activated for parent - {parent.get_full_name()} - Email sent successfully")
        
        messages.success(request, f"Parent {action} successfully")
        return redirect('company:parents')
    
class ParentDetailView(CompanyRequiredMixin, DetailView):
    model = Parent
    template_name = 'company/parent/detail.html'
    pk_url_kwarg = 'parent_id'
    
    def get_context_data(self, **kwargs):
        parent = self.object
        
        # Children and related data
        children = parent.children.only('id', 'first_name', 'last_name').prefetch_related('sessions')
        payments = parent.payments.all()
        feedbacks = parent.feedbacks.filter(status=Feedback.FeedbackStatus.OPEN)[:3]
        testimonials = parent.testimonials.all()[:3]
        
        return {
            'parent': parent,
            'testimonials': testimonials,
            'feedbacks': feedbacks,
            'payments': payments,
            'children': children,
        }