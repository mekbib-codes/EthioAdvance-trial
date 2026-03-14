from datetime import timedelta

from django.views.generic import ListView, DetailView
from django.db.models import Q, Count, Sum, Value, DurationField
from django.db.models.functions import Coalesce

from accounts.mixins import CompanyRequiredMixin
from payment.models import Payment

class PaymentListView(CompanyRequiredMixin, ListView):
    model = Payment
    template_name = 'company/payments/list.html'
    context_object_name = 'payments'
    paginate_by = 25
    annotate_fields = {
        'total_sessions': Count('sessions', distinct=True),
        "total_duration": Coalesce(Sum("sessions__duration"), Value(timedelta(0)), output_field=DurationField()
    ),
    }

    def get_queryset(self):
        queryset = self._get_base_queryset()
        queryset = queryset.annotate(**self.annotate_fields)
        queryset = self._apply_search(queryset)
        return queryset.order_by('-timestamp')

    def _get_base_queryset(self):
        """Base queryset with company restriction and select_related optimizations."""
        return Payment.objects.filter(
            parent__parent_profile__company=self.request.user
        ).select_related('parent', 'child')
    
    def _apply_search(self, queryset):
        """Applies search filtering by parent/child names."""
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(parent__first_name__icontains=search_query) |
                Q(parent__last_name__icontains=search_query) |
                Q(child__first_name__icontains=search_query) |
                Q(child__last_name__icontains=search_query)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        """Passes current filter values to the template."""
        context = super().get_context_data(**kwargs)

        context.update({
            'current_search': self.request.GET.get('q', ''),
            'active_section': 'payments',
        })
        return context