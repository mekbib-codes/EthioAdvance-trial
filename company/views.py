from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied

from accounts.decorators import company_required


import logging
logger = logging.getLogger('app')

@method_decorator(company_required, name='dispatch')
class CompanyDashboardView(LoginRequiredMixin, TemplateView):
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
