from django import forms

from parent.models import Parent
from tutor.models import Tutor

class BaseNotificationForm(forms.Form):
    """
    Base form for notifications
    Child classes should define:
    - Meta.model (the User model)
    - notification_types
    """
    user_ids = forms.CharField(widget=forms.HiddenInput(), required=True)
    
    class Meta:
        model = None
    
    def __init__(self, *args, company=None, initial_users=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if initial_users:
            self.fields['user_ids'].initial = ','.join(str(id) for id in initial_users if id)
        
        # Set dynamic choices for message type
        self.fields['message_type'] = forms.ChoiceField(
            choices=self.Meta.notification_types
        )
        
        # Add custom message field
        self.fields['custom_message'] = forms.CharField(
            widget=forms.Textarea(attrs={'rows': 3}),
            required=False,
            help_text="Only needed if 'Custom Message' is selected"
        )
    
    def clean_user_ids(self):
        user_ids = self.cleaned_data['user_ids']
        if not user_ids:
            raise forms.ValidationError("No users selected")
        
        try:
            return [int(id) for id in user_ids.split(',') if id]
        except ValueError:
            raise forms.ValidationError("Invalid user IDs format")
        
class ParentNotificationForm(BaseNotificationForm):
    class Meta:
        model = Parent
        notification_types = (
            ('feedback_request', 'Feedback Request'),
            ('testimonial_request', 'Testimonial Request'),
            ('payment_reminder', 'Payment Reminder'),
            ('custom', 'Custom Message'),
        )

class TutorNotificationForm(BaseNotificationForm):
    class Meta:
        model = Tutor
        notification_types = (
            ('feedback_request', 'Feedback Request'),
            ('custom', 'Custom Message'),
        )