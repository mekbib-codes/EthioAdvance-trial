from django.urls import path
from .views import (ChildRegistrationView,
                    ChildDashboardView,
                    ChildProfileDashboardView, 
                    AddReportFeedbackView)

app_name = "child"

urlpatterns = [
    path('register/', ChildRegistrationView.as_view(), name='register'), 
    path('dashboard/<int:child_id>', ChildDashboardView.as_view(), name='child_dashboard'),
    path("profile/<int:child_id>", ChildProfileDashboardView.as_view(), name="profile_dashboard"),
    path('add-feedback/<int:report_id>/', AddReportFeedbackView.as_view(), name='add_report_feedback'),
]