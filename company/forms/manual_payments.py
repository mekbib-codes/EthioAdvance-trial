from django import forms

from payment.models import Payment

class ManualPaymentForm(forms.ModelForm):    
    class Meta:
        model = Payment
        fields = ['child']
    
    def __init__(self, *args, parent=None, tutor=None, **kwargs):
        super().__init__(*args, **kwargs)