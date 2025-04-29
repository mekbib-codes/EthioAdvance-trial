from django.views.generic import FormView
from django.contrib import messages
from django.shortcuts import redirect

from actions.models import Notification
from actions.utils import create_notification

from accounts.mixins import CompanyRequiredMixin

class BaseNotificationView(CompanyRequiredMixin, FormView):
    """
    Base view for sending notifications to any user type
    Child classes should define:
    - template_name
    - form_class
    - user_type (string)
    - user_profile_relation (string - path to profile)
    - get_notification_data()
    - get_success_url()
    """
    user_type = None
    user_profile_relation = None
    notification_types = ()
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user
        
        if 'user_ids' in self.request.GET:
            user_ids = [id for id in self.request.GET.get('user_ids', '').split(',') if id]
            kwargs['initial_users'] = user_ids
            
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if 'user_ids' in self.request.GET:
            user_ids = [id for id in self.request.GET.get('user_ids', '').split(',') if id]
            context['users'] = self.get_queryset().filter(
                id__in=user_ids,
                role=self.user_type,
                **{self.user_profile_relation + '__company': self.request.user}
            )

            context['user_type'] = self.user_type
            
        return context
    
    def get_queryset(self):
        """Get base queryset filtered by user type and company"""
        return self.form_class.Meta.model.objects.filter(
            role=self.user_type,
            **{self.user_profile_relation + '__company': self.request.user}
        )
    
    def get_notification_data(self, message_type, custom_message=None):
        """
        Must be implemented by child classes
        Returns dict with:
        - verb: Notification text
        - link: Where user goes when clicking notification
        - link_kwargs: Any kwargs for reverse()
        """
        raise NotImplementedError("Child classes must implement get_notification_data")
    
    def form_valid(self, form):
        user_ids = form.cleaned_data['user_ids']
        message_type = form.cleaned_data['message_type']
        custom_message = form.cleaned_data.get('custom_message', '')
        
        users = self.get_queryset().filter(id__in=user_ids)
        notification_data = self.get_notification_data(message_type, custom_message)
        
        for user in users:
            create_notification(
                actor=self.request.user,
                verb=notification_data['verb'],
                notification_type=Notification.NotificationTypes.INFO,
                extra_data={
                    f'{self.user_type.lower()}_link': notification_data['link'],
                    f'{self.user_type.lower()}_link_kwargs': notification_data.get('link_kwargs', {}),
                },
                recipients=[user]
            )
        
        messages.success(
            self.request, 
            f"Notifications sent to {len(users)} {self.user_type.lower()}s"
        )
        return redirect(self.get_success_url())
    
    def form_invalid(self, form):
        print(form.errors)
        messages.error(self.request, "Sending notifications failed")
        return super().form_invalid(form)