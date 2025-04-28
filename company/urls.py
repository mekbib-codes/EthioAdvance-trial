from django.urls import path
from .views.dashboard import CompanyDashboardView
from .views.parents import ParentListView, ParentDetailView, ToggleParentStatusView
from .views.send_notifications import BulkParentNotificationView
from .views.manual_parent_payment import CreateManualPaymentView, UnpaidSessionsAPIView

app_name = "company"

urlpatterns = [
    path('dashboard/', CompanyDashboardView.as_view(), name='dashboard'),
    path('parents/', ParentListView.as_view(), name='parents'),
    path('parents/<int:parent_id>/', ParentDetailView.as_view(), name='parent_detail'),
    path('parents/notify/', BulkParentNotificationView.as_view(), name='parent_notify_bulk'),
    path('parents/<int:parent_id>/toggle-status/', ToggleParentStatusView.as_view(), name='toggle_parent_status'),
    # Manual payment URL
    path('parents/<int:parent_id>/manual-payment/', CreateManualPaymentView.as_view(), name='record_manual_payment'),
    # API endpoint for dynamic session loading
    path('api/children/<int:child_id>/unpaid-sessions/', UnpaidSessionsAPIView.as_view(),name='unpaid_sessions_api'),
]
