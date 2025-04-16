from django.urls import path
from .views import ( TutorDashboardView, 
                    TutorRegistrationView,
                    StudentsDashboardView,
                    TutorSessionsDashboardView,
                    CreateSessionView,
                    TutorReportsDashboardView,)

app_name = "tutor"

urlpatterns = [
    path('dashboard/', TutorDashboardView.as_view(), name='dashboard'),
    path('hidden/register/', TutorRegistrationView.as_view(), name='register'),
    path('students/',StudentsDashboardView.as_view(), name='students_dashboard'),
    path('child/<int:child_id>/sessions/', TutorSessionsDashboardView.as_view(), name='child_sessions_dashboard'),
    path('sessions/create/<int:child_id>/', CreateSessionView.as_view(), name='create_session'),
    path('child/<int:child_id>/reports/', TutorReportsDashboardView.as_view(), name='child_reports_dashboard'),
]