from django.urls import path
from .views import TestimonialCreateView

app_name = 'testimonials'

urlpatterns = [
    path('submit/', TestimonialCreateView.as_view(), name='submit'),
]