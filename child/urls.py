from django.urls import path
from .views import (ChildRegistrationView,
                    ChildDashboardView,
                    ChildProfileDashboardView,
                    ChildProfileUpdateView,)

app_name = "child"

urlpatterns = [
    path('register/', ChildRegistrationView.as_view(), name='register'), 
    path('dashboard/<int:child_id>', ChildDashboardView.as_view(), name='child_dashboard'),
    path('profile/update/<int:child_id>/', ChildProfileUpdateView.as_view(), name='update_profile'),
    path("profile/<int:child_id>", ChildProfileDashboardView.as_view(), name="profile_dashboard"),
]