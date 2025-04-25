from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages

from accounts.mixins import ParentRequiredMixin
from .models import Testimonial
from .forms import TestimonialForm

from actions.models import Notification
from parent.models import Parent
from actions.utils import create_notification, create_activity_log

class TestimonialCreateView(ParentRequiredMixin, CreateView):
    model = Testimonial
    form_class = TestimonialForm
    template_name = 'testimonial/testimonial_form.html'
    success_url = reverse_lazy('parent:dashboard')
    
    def form_valid(self, form):
        parent = Parent.objects.get(id=self.request.user.id)
        form.instance.parent = parent
        response = super().form_valid(form)

        company = parent.profile.company
        create_notification(
                    actor=parent,
                    verb=f"added a testiomial with rating { form.instance.rating }.",
                    content_object=form.instance,
                    recipients=[company],  # Notify only the company
                    extra_data={
                    'company_link': 'company:parent_page',
                    'company_link_kwargs': {'parent_id': parent.id}
                },
                    notification_type=Notification.NotificationTypes.SUCCESS
                )

        create_activity_log(
            user=parent,
            action=f"Added a testimonial with rating { form.instance.rating }",
            related_object=form.instance,
            link='parent:dashboard',
        )

        messages.success(
            self.request,
            "Thank you for your testimonial! We appreciate your input."
        )
        
        return response