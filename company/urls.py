from django.urls import path
from .views.dashboard import CompanyDashboardView
from .views.parents import ParentListView, ParentSearchView, ParentNotificationView, ToggleParentStatusView,  ParentDetailView
from .views.tutors import TutorListView, TutorSearchView, TutorNotificationView, ToggleTutorStatusView, TutorDetailView
from .views.manual_payments import ManualParentPayment, ManualTutorPayment, UnpaidChildSessionsApIView, UnpaidTutorSessionsAPIView
from .views.children import ChildrenListView, StatusUpdateView, ChildDeatilView
from .views.sessions import SessionsListView, SessionDetailView

app_name = "company"

urlpatterns = [
    path('dashboard/', CompanyDashboardView.as_view(), name='dashboard'),

    path('parents/', ParentListView.as_view(), name='parents'),
    path('parents/search/', ParentSearchView.as_view(), name='parent_search'),
    path('parents/notify/', ParentNotificationView.as_view(), name='notify_parents'),
    path('parents/<int:parent_id>/toggle-status/', ToggleParentStatusView.as_view(), name='toggle_parent_status'),
    path('parents/<int:parent_id>/', ParentDetailView.as_view(), name='parent_detail'),

    path('tutors/', TutorListView.as_view(), name='tutors'),
    path('tutors/search/', TutorSearchView.as_view(), name='tutor_search'),
    path('tutors/notify/', TutorNotificationView.as_view(), name='notify_tutors'),
    path('tutors/<int:tutor_id>/toggle-status/', ToggleTutorStatusView.as_view(), name='toggle_tutor_status'),
    path('tutor/<int:tutor_id>/', TutorDetailView.as_view(), name='tutor_detail'),
    

    # Manual payment URL
    path('parents/<int:parent_id>/manual-payment/', ManualParentPayment.as_view(), name='record_parent_payment'),
    path('tutor/<int:tutor_id>/manual-payment/', ManualTutorPayment.as_view(), name='record_tutor_payment'),
    # API endpoint for dynamic session loading
    path('api/children/<int:child_id>/unpaid-sessions/', UnpaidChildSessionsApIView.as_view(),name='unpaid_sessions_api'),
    path('api/students/<int:child_id>/requested-sessions/', UnpaidTutorSessionsAPIView.as_view(),name='requested_sessions_api'),

    path('children/', ChildrenListView.as_view(), name='children_list'),
    path('child/<int:child_id>/status/update/', StatusUpdateView.as_view(), name='update_child_status'),
    path('child/<int:child_id>/', ChildDeatilView.as_view(), name='child_detail'),

    path('sessions/', SessionsListView.as_view(), name='sessions_list'),
    path('session/<int:session_id>/', SessionDetailView.as_view(), name='session_detail')
]
