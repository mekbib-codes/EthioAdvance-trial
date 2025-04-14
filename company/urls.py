from django.urls import path
from .views import ( CompanyDashboardView, )

app_name = "company"

urlpatterns = [
    path('dashboard/', CompanyDashboardView.as_view(), name='dashboard'),
]