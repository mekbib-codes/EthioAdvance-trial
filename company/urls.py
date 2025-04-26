from django.urls import path
from .views.dashboard import CompanyDashboardView
from .views.parents import ParentListView, ParentDetailView

app_name = "company"

urlpatterns = [
    path('dashboard/', CompanyDashboardView.as_view(), name='dashboard'),
    path('parents/', ParentListView.as_view(), name='parents'),
    path('parents/<int:parent_id>/', ParentDetailView.as_view(), name='parent_detail'),
]