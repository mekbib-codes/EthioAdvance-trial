from django.views.generic import TemplateView
from django.core.exceptions import PermissionDenied

from accounts.mixins import CompanyRequiredMixin

import logging
logger = logging.getLogger('app')

class CompanyDashboardView(CompanyRequiredMixin, TemplateView):
    template_name = 'company/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            company = self.request.user

            context.update({
                'company': company,
                'active_section': 'dashboard',
            })
            
            logger.info(
                f"Company dashboard accessed by {company.email} "
                f"(ID: {company.pk})"
            )
            return context
            
        except Exception as e:
            logger.error(
                f"Company dashboard error for {self.request.user.email}: {str(e)}",
                exc_info=True
            )
            raise PermissionDenied("Error loading dashboard")
