from django.views.generic import ListView, DetailView
from django.db.models import Q

from accounts.mixins import CompanyRequiredMixin
from report.models import Report

class ReportListView(CompanyRequiredMixin, ListView):
    model = Report
    template_name = 'company/reports/list.html'
    context_object_name = 'reports'
    paginate_by = 25

    def get_queryset(self):
        queryset = self._get_base_queryset()
        queryset = self._apply_search(queryset)
        return queryset.order_by('-created_at')

    def _get_base_queryset(self):
        """Base queryset with company restriction and select_related optimizations."""
        return Report.objects.filter(
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
    
    def get_context_data(self, **kwargs):
        """Passes current filter values to the template."""
        context = super().get_context_data(**kwargs)

        context.update({
            'current_search': self.request.GET.get('q', ''),
            'active_section': 'reports',
        })
        return context
    
class ReportDetailView(CompanyRequiredMixin, DetailView):
    model = Report
    template_name = 'company/reports/detail.html'
    context_object_name = 'report'
    pk_url_kwarg = 'report_id'

    def get_queryset(self):
        # Optimize queryset by prefetching all related data
        return super().get_queryset().select_related(
            'tutor',
            'child'
        ).prefetch_related(
            'strengths',
            'weaknesses',
            'goals_achieved',
            'learning_material_prepared',
            'challenges_encountered',
            'suggested_solutions'
        )
    
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['active_section'] = 'reports'
        return context

