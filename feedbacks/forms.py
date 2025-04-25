from django import forms
from .models import Feedback

class FeedbackForm(forms.ModelForm):

    RATING_CHOICES = [
        (1, '★'),
        (2, '★★'),
        (3, '★★★'),
        (4, '★★★★'),
        (5, '★★★★★'),
    ]
    
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'star-rating'}),
        required=False,
        label='Rating'
    )
    
    class Meta:
        model = Feedback
        fields = ['text', 'rating']