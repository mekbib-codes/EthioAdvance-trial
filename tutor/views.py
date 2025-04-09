from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied

from accounts.decorators import tutor_required


import logging
logger = logging.getLogger('app')

@method_decorator(tutor_required, name='dispatch')
class TutorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'tutor/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            tutor = self.request.user
            slug = tutor.slug

            context.update({
                'tutor': tutor,
                'slug': slug,
                'active_section': 'dashboard',
                'canonical_url': self.get_canonical_url(),
            })
            
            logger.info(
                f"Tutor dashboard accessed by {tutor.email} "
                f"(ID: {tutor.pk})"
            )
            return context
            
        except Exception as e:
            logger.error(
                f"Tutor dashboard error for {self.request.user.email}: {str(e)}",
                exc_info=True
            )
            raise PermissionDenied("Error loading dashboard")

    def get_canonical_url(self):
        return self.request.build_absolute_uri(
            f"/Tutor/{self.request.user.slug}/dashboard/"
        )
