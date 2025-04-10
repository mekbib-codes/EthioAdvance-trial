from django.urls import path
from .views import ( ParentDashboardView,
                    ParentRegistrationView)

app_name = "parent"

urlpatterns = [
    path('<slug:parent_slug>/dashboard/', ParentDashboardView.as_view(), name='dashboard'),
    path('register/', ParentRegistrationView.as_view(), name='register'),
]