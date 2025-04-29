from django.views.generic import ListView
from django.db.models import Q
from accounts.mixins import CompanyRequiredMixin

from decimal import Decimal
import logging

logger = logging.getLogger('app')

class BaseUserListView(CompanyRequiredMixin, ListView):
    """
    Base view for all user type listings (Company, Tutor, Parent)
    To be inherited by specific user type views
    """
    template_name = None # To be overridden by subclass
    context_object_name = 'users'
    paginate_by = 25
    role_filter = None  # Must be set in child classes (User.Role.COMPANY etc.)
    search_fields = ['first_name', 'last_name', 'email', 'phone_number']
    annotate_fields = {}  # Fields to annotate to queryset
    financial_calculations = False  # Set True to enable payment/due calculations
    
    def get_base_queryset(self):
        """Base queryset filtered by role"""
        if not self.role_filter:
            raise NotImplementedError("role_filter must be defined in child class")
        return self.model.objects.filter(role=self.role_filter)

    def apply_search(self, queryset, search_query):
        """Apply search to the queryset"""
        if not search_query:
            return queryset
            
        query = Q()
        for field in self.search_fields:
            query |= Q(**{f"{field}__icontains": search_query})
        return queryset.filter(query)

    def apply_annotations(self, queryset):
        """Apply annotations to queryset"""
        if self.annotate_fields:
            return queryset.annotate(**self.annotate_fields)
        return queryset

    def calculate_financials(self, users):
        """
        Calculate financial data if enabled
        Override in child classes for specific calculations
        """
        if not self.financial_calculations:
            return users
            
        rate = self.get_current_rate()
        for user in users:
            user.total_paid = Decimal(0)
            user.total_due = Decimal(0)
        return users

    def get_current_rate(self):
        """Can be overridden by child classes"""
        return Decimal(0)

    def get_queryset(self):
        queryset = self.get_base_queryset()
        queryset = self.apply_annotations(queryset)
        queryset = self.apply_search(queryset, self.request.GET.get('q', '').strip())
        
        users = list(queryset)
        return self.calculate_financials(users)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'active_section': self.context_object_name,
            'search_query': self.request.GET.get('q', ''),
            'is_search': 'q' in self.request.GET,
            'user_type': self.role_filter.lower() if self.role_filter else 'user'
        })
        return context