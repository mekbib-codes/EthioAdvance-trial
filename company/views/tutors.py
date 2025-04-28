from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from accounts.views.user_list_view import BaseUserListView
from tutor.models import Tutor
from accounts.models import User
from payment.models import TutorPayRate, TutorPayments
from session.models import Session

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