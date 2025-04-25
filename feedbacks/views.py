from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model

from .models import Feedback
from .forms import FeedbackForm

from actions.models import Notification
from actions.utils import create_activity_log, create_notification

class FeedbackCreateView(LoginRequiredMixin, CreateView):
    model = Feedback
    form_class = FeedbackForm
    template_name = 'feedback/feedback_form.html'
    success_url = reverse_lazy('feedbacks:thank_you')
    
    def form_valid(self, form):
        form.instance.user = self.request.user

        response = super().form_valid(form)

        User = get_user_model()
        superadmins = User.objects.filter(is_superuser=True)

        create_notification(
                    actor=self.request.user,
                    verb=f"added a feedback with rating { form.instance.rating }.",
                    content_object=form.instance,
                    recipients=list(superadmins),
                    extra_data={
                },
                    notification_type=Notification.NotificationTypes.SUCCESS
                )

        create_activity_log(
            user=self.request.user,
            action=f"Added a feedback with rating { form.instance.rating }",
            related_object=form.instance,
            link=f'{ self.request.user.role.lower() }:dashboard',
        )
        
        messages.success(
            self.request,
            "Thank you for your feedback! We appreciate your input."
        )
        return response