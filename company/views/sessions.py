from django.views.generic import ListView, DetailView
from django.db.models import Q, DurationField, F, ExpressionWrapper
from django.utils.timezone import timedelta
from django.utils import timezone

from accounts.mixins import CompanyRequiredMixin
from session.models import Session

class SessionsListView(CompanyRequiredMixin, ListView):
    model = Session
    template_name = 'company/sessions/list.html'
    context_object_name = 'sessions'
    paginate_by = 25

    def get_queryset(self):
        queryset = self._get_base_queryset()
        queryset = self._apply_search(queryset)
        queryset = self._apply_filters(queryset)
        return queryset.order_by('-created_at')

    def _get_base_queryset(self):
        """Base queryset with company restriction and select_related optimizations."""
        return Session.objects.filter(
            tutor__tutor_profile__company=self.request.user
        ).select_related('tutor', 'child')

    def _apply_search(self, queryset):
        """Applies search filtering by tutor/child names."""
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(tutor__first_name__icontains=search_query) |
                Q(tutor__last_name__icontains=search_query) |
                Q(child__first_name__icontains=search_query) |
                Q(child__last_name__icontains=search_query)
            )
        return queryset

    def _apply_filters(self, queryset):
        """Applies all filters (status, duration, payment flags)."""
        queryset = self._filter_by_status(queryset)
        queryset = self._filter_by_duration(queryset)
        queryset = self._filter_by_payment_flags(queryset)
        return queryset

    def _filter_by_status(self, queryset):
        """Filters by session status."""
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def _filter_by_duration(self, queryset):
        """Filters sessions longer than a specified duration."""
        duration_filter = self.request.GET.get('duration')
        if duration_filter:
            hours = int(duration_filter.replace('h', ''))
            target_duration = timedelta(hours=hours)
            queryset = queryset.annotate(
                duration_calc=ExpressionWrapper(
                    F('duration'),
                    output_field=DurationField()
                )
            ).filter(duration_calc__gte=target_duration)
        return queryset

    def _filter_by_payment_flags(self, queryset):
        """Filters by payment-related flags (is_paid, paid_to_tutor, overdue)."""
        if self.request.GET.get('is_paid') == 'on':
            queryset = queryset.filter(is_paid=True)
        if self.request.GET.get('paid_to_tutor') == 'on':
            queryset = queryset.filter(paid_to_tutor=True)
        return queryset

    def get_context_data(self, **kwargs):
        """Passes current filter values to the template."""
        context = super().get_context_data(**kwargs)

        status_choices = Session.Status.choices
        context.update({
            'current_search': self.request.GET.get('search', ''),
            'current_status': self.request.GET.get('status', ''),
            'current_duration': self.request.GET.get('duration', ''),
            'current_is_paid': self.request.GET.get('is_paid', ''),
            'current_paid_to_tutor': self.request.GET.get('paid_to_tutor', ''),
            
            'status_choices': status_choices,
            'active_section': 'sessions',
        })
        return context
    

class SessionDetailView(CompanyRequiredMixin, DetailView):
    model = Session
    template_name = 'company/sessions/detail.html'
    pk_url_kwarg = 'session_id'
    context_object_name = 'session'

    def get_queryset(self):
        # Optimize queryset to prevent N+1 queries and ensure company restriction
        return super().get_queryset().filter(
            tutor__tutor_profile__company=self.request.user
        ).select_related(
            'tutor',
            'child',
            'tutor__tutor_profile'
        )
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add additional context data
        context['now'] = timezone.now()
        context['active_section'] = 'sessions'
        return context