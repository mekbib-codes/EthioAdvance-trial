from django.views.generic import ListView, UpdateView
from django.db.models import Count, Sum, Q
from django.db.models.functions import Coalesce
from django.db.models import OuterRef, Subquery, Sum, Count, DecimalField, Value, IntegerField
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages

from accounts.mixins import CompanyRequiredMixin
from child.models import Child, Status
from payment.models import Payment, SessionRate
from session.models import Session
from report.models import Report
from company.forms.child_update_status import StatusForm

from datetime import date
from dateutil.relativedelta import relativedelta

from decimal import Decimal
import logging
logger = logging.getLogger('app')


class ChildrenListView(CompanyRequiredMixin, ListView):
    model = Child
    template_name = 'company/children/list.html'
    context_object_name = 'children'
    paginate_by = 25
    
    def apply_search(self, queryset, search_term):
        return queryset.filter(
            Q(first_name__icontains=search_term) |
            Q(last_name__icontains=search_term) |
            Q(parent__first_name__icontains=search_term) |
            Q(parent__last_name__icontains=search_term) |
            Q(tutor__first_name__icontains=search_term) |
            Q(tutor__last_name__icontains=search_term)
        )

    def get_queryset(self):
        payments_sum = Payment.objects.filter(
            child=OuterRef('pk'),
            status=Payment.STATUS.SUCCESS
        ).values('child').annotate(
            total=Sum('amount')
        ).values('total')

        sessions_count = Session.objects.filter(
            child=OuterRef('pk')
        ).values('child').annotate(
            count=Count('id', distinct=True)
        ).values('count')

        reports_count = Report.objects.filter(
            child=OuterRef('pk')
        ).values('child').annotate(
            count=Count('id', distinct=True)
        ).values('count')

        queryset = super().get_queryset().filter(
            parent__parent_profile__company=self.request.user
        ).annotate(
            total_payments=Coalesce(
                Subquery(payments_sum, output_field=DecimalField()), Decimal(0)
            ),
            total_sessions=Coalesce(
                Subquery(sessions_count, output_field=IntegerField()), Value(0)
            ),
            total_reports=Coalesce(
                Subquery(reports_count, output_field=IntegerField()), Value(0)
            )
        ).select_related(
            'parent', 'tutor'
        )
        
        # Get search term from GET parameters
        search_term = self.request.GET.get('q')
        if search_term:
            queryset = self.apply_search(queryset, search_term)
        
        grade = self.request.GET.get('grade')
        if grade:
            queryset = queryset.filter(grade_level = grade)

        age = self.request.GET.get('age')
        if age:
            try:
                age = int(age)
                # Calculate birth date range for the specified age
                today = date.today()
                min_birth_date = today - relativedelta(years=age+1)
                max_birth_date = today - relativedelta(years=age)
                queryset = queryset.filter(
                    date_of_birth__gte=min_birth_date,
                    date_of_birth__lt=max_birth_date
                )
            except ValueError:
                # Handle invalid age input
                pass
        
        gender = self.request.GET.get('gender')
        if gender:
            queryset = queryset.filter(gender = gender)

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
        
        search_query = self.request.GET.get('q')
        context['search_query'] = search_query
        context['grade_levels'] = range(1, 13)
        context['age_range'] = range(5, 19)
        context['active_section'] = 'children'
        return context
    
class StatusUpdateView(UpdateView):
    model = Status
    form_class = StatusForm
    template_name = 'company/children/status/update.html'

    def get_object(self, queryset=None):
        child_id = self.kwargs.get('child_id')
        child = get_object_or_404(Child, id=child_id)

        # Only allow access if the child belongs to the logged-in parent
        if child.parent.parent_profile.company != self.request.user:
            raise PermissionDenied("You are not authorized to update this child's status.")

        # Return the existing Status or create one if it doesn't exist yet
        status_obj, created = Status.objects.get_or_create(child=child)
        return status_obj

    def get_context_data(self, **kwargs):
        context =  super().get_context_data(**kwargs)
        context['active_section'] = 'children'
        return context
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Status for {self.object.child.get_full_name()} was successfully updated ✅.")
        return response

    def form_invalid(self, form):
        # Optional: log errors or add a custom error message
        messages.error(self.request, "Oops! There was an error updating the status. Please check the form and try again. 🚨")
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('company:children_list')

