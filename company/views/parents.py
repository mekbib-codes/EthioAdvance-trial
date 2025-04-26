from django.db.models import Count, Sum,DecimalField
from django.views.generic import ListView, DetailView
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from accounts.mixins import CompanyRequiredMixin
from parent.models import Parent
from payment.models import SessionRate, Payment
from session.models import Session
from feedbacks.models import Feedback

import logging
logger = logging.getLogger('app')

class ParentListView(CompanyRequiredMixin, ListView):
    model = Parent
    template_name = 'company/parent/list.html'
    context_object_name = 'parents'
    paginate_by = 25

    def get_queryset(self):
        # Get parents that belong to the current company
        queryset = Parent.objects.filter(
            parent_profile__company=self.request.user
        ).select_related('parent_profile').annotate(
            total_children=Count('children', distinct=True),
            total_sessions=Count('children__sessions', distinct=True),
            total_reports=Count('children__report', distinct=True),
            total_testimonials=Count('testimonials', distinct=True),
            total_feedbacks=Count('feedbacks', distinct=True),
        )

        # Get the current session rate
        try:
            rate = Decimal(SessionRate.objects.latest("updated_at").current_hourly_rate)
        except SessionRate.DoesNotExist:
            logger.error("No Session Rate Found")
            rate = Decimal(0)

        # We'll calculate total_paid and total_due in Python for accuracy
        parents = list(queryset)
        parent_ids = queryset.values_list('id', flat=True)

        # Prefetch all necessary data in bulk
        from django.db.models import Prefetch
        from collections import defaultdict

        # Get all successful payments for these parents
        success_payments = Payment.objects.filter(
            parent_id__in=parent_ids,
            status=Payment.STATUS.SUCCESS
        ).values('parent_id').annotate(
            total=Sum('amount', output_field=DecimalField(max_digits=12, decimal_places=2))
        )
        payment_totals = {p['parent_id']: p['total'] for p in success_payments}

        # Get all unpaid sessions for these parents
        unpaid_sessions = Session.objects.filter(
            child__parent_id__in=parent_ids,
            status=Session.Status.APPROVED,
            is_paid=False
        ).select_related('child').only('child__parent_id', 'duration')

        # Calculate total due per parent
        parent_unpaid_durations = defaultdict(timedelta)
        for session in unpaid_sessions:
            if session.duration:
                parent_unpaid_durations[session.child.parent_id] += session.duration

        # Attach the calculated values to each parent
        for parent in parents:
            # Total paid
            parent.total_paid = payment_totals.get(parent.id, Decimal(0))

            # Total due calculation
            unpaid_duration = parent_unpaid_durations.get(parent.id, timedelta())
            if unpaid_duration:
                total_hours = unpaid_duration.total_seconds() / 3600
                parent.total_due = round(Decimal(total_hours) * rate, 2)
            else:
                parent.total_due = Decimal(0)

        return parents

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_section'] = 'parents'
        return context

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