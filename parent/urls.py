from django.urls import path
from .views import ( ParentDashboardView,
                    ParentRegistrationView,
                    ParentProfileDashboardView,
                    ParentProfileUpdateView,
                    ChildrenDashboardView,
                    ParentSessionsDashboardView,
                    UpdateSessionStatusView,
                    ParentReportsDashboardView,
                    AddReportFeedbackView,
                    ParentPaymentDashboardView)

app_name = "parent"

urlpatterns = [
    path('dashboard/', ParentDashboardView.as_view(), name='dashboard'),
    path('register/', ParentRegistrationView.as_view(), name='register'),
    path("profile/", ParentProfileDashboardView.as_view(), name="profile_dashboard"),
    path("profile/update/", ParentProfileUpdateView.as_view(), name="update_profile"),
    path('children/', ChildrenDashboardView.as_view(), name='children_dashboard'),
    path('child/<int:child_id>/sessions/', ParentSessionsDashboardView.as_view(), name='child_sessions_dashboard'),
    path('session-status/<int:session_id>/<str:status>/', UpdateSessionStatusView.as_view(), name='update_session_status'),
    path('child/<int:child_id>/reports/', ParentReportsDashboardView.as_view(), name='child_reports_dashboard'),
    path('add-feedback/<int:report_id>/', AddReportFeedbackView.as_view(), name='add_report_feedback'),
    path('payment/dashboard/', ParentPaymentDashboardView.as_view(), name='payment_dashboard'),
]