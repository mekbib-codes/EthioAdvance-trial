from django.views.generic import FormView
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib.auth import get_user_model

from company.forms.notify_parets import BulkParentNotificationForm
from actions.models import Notification
from actions.utils import create_notification

class BulkParentNotificationView(FormView):
    template_name = 'company/parent/bulk_notification.html'
    form_class = BulkParentNotificationForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user
        
        # Get parent IDs from query parameters if coming from list view
        if 'parent_ids' in self.request.GET:
            parent_ids = [id for id in self.request.GET.get('parent_ids', '').split(',') if id]
            kwargs['initial_parents'] = parent_ids
            
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get selected parents for display
        if 'parent_ids' in self.request.GET:
            parent_ids = [id for id in self.request.GET.get('parent_ids', '').split(',') if id]
            context['parents'] = get_user_model().objects.filter(
                id__in=parent_ids,
                role='PARENT',
                parent_profile__company=self.request.user
            )
            
        return context
    
    def form_valid(self, form):
        parent_ids = form.cleaned_data['parent_ids']
        message_type = form.cleaned_data['message_type']
        custom_message = form.cleaned_data['custom_message']
        
        parents = get_user_model().objects.filter(
            id__in=parent_ids,
            role='PARENT',
            parent_profile__company=self.request.user
        )
        
        # Notification content setup
        notification_data = {
            'feedback_request': {
                'verb': " - Friendly request to provide your feedback about the website.",
                'parent_link': 'feedbacks:submit',
                'parent_link_kwargs': {},
            },
            'testimonial_request': {
                'verb': "- Friendly request to provide a testimonial and help us enhance our public image.",
                'parent_link': 'testimonials:submit',
                'parent_link_kwargs': {},
            },
            'payment_reminder': {
                'verb': "- Friendly Payment overdue reminder",
                'parent_link': 'parent:payment_dashboard',
                'parent_link_kwargs': {},
            },
            'custom': {
                'verb': f"- {custom_message}",
                'parent_link': 'parent:dashboard',
                'parent_link_kwargs': {},
            }
        }
        
        # Create notifications
        for parent in parents:
            data = notification_data[message_type]
            create_notification(
                actor=self.request.user,
                verb=data['verb'],
                notification_type=Notification.NotificationTypes.INFO,
                extra_data={
                    'parent_link': data['parent_link'],
                    'parent_link_kwargs': data.get('parent_link_kwargs', {}),
                },
                recipients=[parent]
            )
        
        messages.success(self.request, f"Notifications sent to {len(parents)} parents")
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse('company:parents')

    def form_invalid(self, form):
        messages.error(self.request, "Sending notification failed")
        return super().form_invalid(form)
