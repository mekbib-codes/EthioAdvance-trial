from django.urls import path
from .views import FeedbackCreateView
from django.views.generic import TemplateView

app_name = 'feedbacks'

urlpatterns = [
    path('submit/', FeedbackCreateView.as_view(), name='submit'),
    path('thank-you/', TemplateView.as_view(template_name='feedback/feedback_thankyou.html'), name='thank_you'),
]