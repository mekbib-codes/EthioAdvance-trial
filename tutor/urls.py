from django.urls import path
from .views import ( TutorDashboardView, 
                    TutorRegistrationView)

app_name = "tutor"

urlpatterns = [
    path('dashboard/', TutorDashboardView.as_view(), name='dashboard'),
    path('hidden/register/', TutorRegistrationView.as_view(), name='register'),
]