from django.db.models import Count, Sum,DecimalField
from django.views.generic import ListView, DetailView, View
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect

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
        parent_ids = [p.id for p in parents]

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

class ParentDetailView(CompanyRequiredMixin, DetailView):
    model = Parent
    template_name = 'company/parent/detail.html'
    context_object_name = 'parent'
    pk_url_kwarg = 'parent_id'

    def get_queryset(self):
        # Only allow access to parents belonging to the current company
        return Parent.objects.filter(
            parent_profile__company=self.request.user
        ).select_related('parent_profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parent = self.object
        
        try:
            # Prefetch related data
            parent = Parent.objects.prefetch_related(
                'children',
                'activity_logs',
                'payments',
                'feedbacks',
                'testimonials'
            ).select_related('parent_profile').get(id=parent.id)

            # Get all sessions for the parent
            sessions = Session.objects.filter(child__parent=parent).select_related('child')
            
            # Session statistics
            total_sessions = sessions.count()
            pending_sessions = sessions.filter(status=Session.Status.PENDING)
            approved_sessions = sessions.filter(status=Session.Status.APPROVED)
            rejected_sessions = sessions.filter(status=Session.Status.REJECTED)
            
            session_data = {
                'total_sessions': total_sessions,
                'total_duration': sessions.aggregate(total=Sum('duration'))['total'] or timedelta(0),
                
                'pending_sessions': pending_sessions.count(),
                'pending_duration': pending_sessions.aggregate(total=Sum('duration'))['total'] or timedelta(0),
                
                'approved_sessions': approved_sessions.count(),
                'approved_duration': approved_sessions.aggregate(total=Sum('duration'))['total'] or timedelta(0),
                
                'rejected_sessions': rejected_sessions.count(),
                'rejected_duration': rejected_sessions.aggregate(total=Sum('duration'))['total'] or timedelta(0),
                
                'recent_sessions': sessions.order_by('-created_at')[:5]
            }

            # Calculate percentages
            total = session_data['total_sessions'] or 1  # avoid division by zero
            session_data['approved_percentage'] = round((session_data['approved_sessions'] / total) * 100)
            session_data['pending_percentage'] = round((session_data['pending_sessions'] / total) * 100)
            session_data['rejected_percentage'] = round((session_data['rejected_sessions'] / total) * 100)

            # Payment information
            success_payments = parent.payments.filter(status=Payment.STATUS.SUCCESS)
            total_paid = success_payments.aggregate(total=Sum('amount'))['total'] or Decimal(0)

            # Paid/Unpaid sessions
            paid_sessions = approved_sessions.filter(is_paid=True)
            unpaid_sessions = approved_sessions.filter(is_paid=False)

            # Duration calculations
            paid_sessions_duration = paid_sessions.aggregate(
                total=Sum('duration')
            )['total'] or timedelta(0)

            unpaid_sessions_duration = unpaid_sessions.aggregate(
                total=Sum('duration')
            )['total'] or timedelta(0)

            # Calculate amount due
            try:
                rate = Decimal(SessionRate.objects.latest("updated_at").current_hourly_rate)
            except SessionRate.DoesNotExist:
                rate = Decimal(0)
                logger.warning("No SessionRate found")

            if unpaid_sessions_duration != timedelta(0):
                total_unpaid_hours = unpaid_sessions_duration.total_seconds() / 3600
                total_due = round(Decimal(total_unpaid_hours) * rate, 2)
            else:
                total_due = Decimal(0)

            payment_data = {
                'total_paid': total_paid,
                'total_due': total_due,
                'paid_sessions': paid_sessions.count(),
                'unpaid_sessions': unpaid_sessions.count(),
                'paid_sessions_duration': paid_sessions_duration,
                'unpaid_sessions_duration': unpaid_sessions_duration,
                'hourly_rate': rate
            }
            
            # Feedback and testimonials
            parent_feedbacks = parent.feedbacks.filter(status=Feedback.FeedbackStatus.OPEN)[:3]
            testimonials = parent.testimonials.all()[:3]
            
            children = parent.children.all().prefetch_related('sessions')
            payments = parent.payments.all()

            context.update({
                'testimonials': testimonials,
                'session_data': session_data,
                'payment_data': payment_data,
                'feedbacks': parent_feedbacks,
                'active_section': 'parents',
                'payments': payments,
                'children': children,
                'current_time': timezone.now(),
            })
            
            logger.info(
                f"Parent detail viewed for {parent.get_full_name()} by company {self.request.user.email}"
            )
            return context
            
        except Exception as e:
            logger.error(
                f"Error loading parent detail for {parent.id}: {str(e)}",
                exc_info=True
            )
            raise PermissionDenied("Error loading parent details")

class ToggleParentStatusView(View):
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
            'parent': parent,
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