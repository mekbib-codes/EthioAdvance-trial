from django.urls import path
from .views import ( ParentDashboardView,
                    ParentRegistrationView,
                    UpdateSessionStatusView)

app_name = "parent"

urlpatterns = [
    path('dashboard/', ParentDashboardView.as_view(), name='dashboard'),
    path('register/', ParentRegistrationView.as_view(), name='register'),
    path('session-status/<int:session_id>/<str:status>/', UpdateSessionStatusView.as_view(), name='update_session_status'),
]