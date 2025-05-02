from django.views.generic import ListView
from django.db.models import Count, Sum, Prefetch
from django.db.models.functions import Coalesce
from django.db.models import DecimalField, IntegerField
from datetime import timedelta

from accounts.mixins import CompanyRequiredMixin
from child.models import Child
from payment.models import Payment, SessionRate
from session.models import Session
from report.models import Report

from decimal import Decimal
import logging
logger = logging.getLogger('app')


class ChildrenListView(CompanyRequiredMixin, ListView):
    model = Child
    template_name = 'company/children/list.html'
    context_object_name = 'children'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            parent__parent_profile__company=self.request.user
        ).select_related(
            'parent', 'tutor'
        ).prefetch_related(
            Prefetch('payments', queryset=Payment.objects.filter(
                status=Payment.STATUS.SUCCESS
            ).only('amount')),
            Prefetch('sessions', queryset=Session.objects.only(
                'duration', 'status', 'is_paid'
            )),
            Prefetch('report', queryset=Report.objects.only('id'))
        ).annotate(
            total_payments=Coalesce(Sum('payments__amount'), Decimal(0)),
            total_sessions=Count('sessions', distinct=True),
            total_reports=Count('report', distinct=True)
        )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get rate once for all calculations
        hourly_rate = Decimal(str(SessionRate.objects.latest("updated_at").current_hourly_rate))
        
        for child in context['children']:
            # Calculate age (safe, uses model method)
            child.age = child.age()
            
            # Calculate payment due using prefetched data
            unpaid_sessions = [
                s for s in child.sessions.all() 
                if s.status == Session.Status.APPROVED and not s.is_paid
            ]
            
            total_seconds = sum(
                (s.duration.total_seconds() for s in unpaid_sessions if s.duration),
                0.0
            )
            
            child.total_due = Decimal(total_seconds) / Decimal(3600) * hourly_rate
            child.total_due = child.total_due.quantize(Decimal('0.00'))
            child.unpaid_sessions = unpaid_sessions
        
        context['active_section'] = 'children'
        return context
