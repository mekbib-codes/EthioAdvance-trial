from django.urls import path
from .views.dashboard import CompanyDashboardView
from .views.parents import ParentListView, ToggleParentStatusView, ParentSearchView, ParentNotificationView, ParentDetailView
from .views.tutors import TutorListView, TutorSearchView, TutorNotificationView
from .views.manual_parent_payment import CreateManualPaymentView, UnpaidSessionsAPIView

app_name = "company"

urlpatterns = [
    path('dashboard/', CompanyDashboardView.as_view(), name='dashboard'),

    path('parents/', ParentListView.as_view(), name='parents'),
    path('parents/search/', ParentSearchView.as_view(), name='parent_search'),
    path('parents/notify/', ParentNotificationView.as_view(), name='notify_parents'),
    path('parents/<int:parent_id>/', ParentDetailView.as_view(), name='parent_detail'),

    path('tutors/', TutorListView.as_view(), name='tutors'),
    path('tutors/search/', TutorSearchView.as_view(), name='tutor_search'),
    path('tutors/notify/', TutorNotificationView.as_view(), name='notify_tutors'),

    path('parents/<int:parent_id>/toggle-status/', ToggleParentStatusView.as_view(), name='toggle_parent_status'),

    # Manual payment URL
    path('parents/<int:parent_id>/manual-payment/', CreateManualPaymentView.as_view(), name='record_manual_payment'),
    # API endpoint for dynamic session loading
    path('api/children/<int:child_id>/unpaid-sessions/', UnpaidSessionsAPIView.as_view(),name='unpaid_sessions_api'),
]
