from django.views.generic import TemplateView

from testimonials.models import Testimonial

import logging
logger = logging.getLogger('app')

class Home(TemplateView):
    template_name = 'accounts/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            testimonials = Testimonial.objects.filter(show_testimonial=True).select_related('parent', 'parent__parent_profile')
            context.update({
                'testimonials': testimonials,
            })
            return context
            
        except Exception as e:
            logger.error(
                f"Home page error: {str(e)}",
                exc_info=True
            )
            raise Exception