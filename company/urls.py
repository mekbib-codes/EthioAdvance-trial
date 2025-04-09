from django.urls import path
from .views import ( CompanyDashboardView, )

app_name = "company"

urlpatterns = [
    path('<slug:company_slug>/dashboard/', CompanyDashboardView.as_view(), name='dashboard'),
]