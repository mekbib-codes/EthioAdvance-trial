from django.urls import path
from .views import ( ParentDashboardView,
                    ParentRegistrationView,
                    ChildrenDashboardView,
                    ParentSessionsDashboardView,
                    UpdateSessionStatusView,)

app_name = "parent"

urlpatterns = [
    path('dashboard/', ParentDashboardView.as_view(), name='dashboard'),
    path('register/', ParentRegistrationView.as_view(), name='register'),
    path('children/', ChildrenDashboardView.as_view(), name='children_dashboard'),
    path('child/<int:child_id>/sessions/', ParentSessionsDashboardView.as_view(), name='child_sessions_dashboard'),
    path('session-status/<int:session_id>/<str:status>/', UpdateSessionStatusView.as_view(), name='update_session_status'),
]