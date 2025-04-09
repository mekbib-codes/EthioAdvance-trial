from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied

from accounts.decorators import parent_required

import logging
logger = logging.getLogger('app')

@method_decorator(parent_required, name='dispatch')
class ParentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'parent/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            parent = self.request.user
            slug = parent.slug

            context.update({
                'parent': parent,
                'slug': slug,
                'active_section': 'dashboard',
                'canonical_url': self.get_canonical_url(),
            })
            
            logger.info(
                f"Parent dashboard accessed by {parent.email} "
                f"(ID: {parent.pk})"
            )
            return context
            
        except Exception as e:
            logger.error(
                f"Parent dashboard error for {self.request.user.email}: {str(e)}",
                exc_info=True
            )
            raise PermissionDenied("Error loading dashboard")

    def get_canonical_url(self):
        return self.request.build_absolute_uri(
            f"/parent/{self.request.user.slug}/dashboard/"
        )
