from django import forms
from django.contrib.auth import get_user_model

class BulkParentNotificationForm(forms.Form):
    MESSAGE_TYPES = (
        ('feedback_request', 'Feedback Request'),
        ('testimonial_request', 'Testimonial Request'),
        ('payment_reminder', 'Payment Reminder'),
        ('custom', 'Custom Message'),
    )
    
    message_type = forms.ChoiceField(choices=MESSAGE_TYPES)
    custom_message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Only needed if 'Custom Message' is selected"
    )
    parent_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    
    def __init__(self, *args, company=None, initial_parents=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial value for parent_ids if provided
        if initial_parents:
            self.fields['parent_ids'].initial = ','.join(str(id) for id in initial_parents if id)
    
    def clean_parent_ids(self):
        parent_ids = self.cleaned_data['parent_ids']
        if not parent_ids:
            raise forms.ValidationError("No parents selected")
        
        try:
            # Convert comma-separated string to list of integers
            return [int(id) for id in parent_ids.split(',') if id]
        except ValueError:
            raise forms.ValidationError("Invalid parent IDs format")