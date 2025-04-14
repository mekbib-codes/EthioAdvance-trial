from django.urls import path
from .views import (ChildRegistrationView,
                    ChildrenDashboardView,
                    ChildDashboardView)

app_name = "child"

urlpatterns = [
    path('register/', ChildRegistrationView.as_view(), name='register'),
    path('dashboard/', ChildrenDashboardView.as_view(), name='children_dashboard'),
    path('dashboard/<int:child_id>', ChildDashboardView.as_view(), name='child_dashboard'),

]