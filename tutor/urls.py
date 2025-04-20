from django.urls import path
from .views import ( TutorDashboardView, 
                    TutorRegistrationView,
                    TutorProfileDashboardView,
                    StudentsDashboardView,
                    TutorSessionsDashboardView,
                    CreateSessionView,
                    TutorReportsDashboardView,
                    ReportSummaryStepView,
                    SessionInsightStepView,
                    QuizAssignmentInsightStepView,
                    MockExamInsightStepView,
                    ChallengesAndSolutionsStepView,
                    TutorPaymentDashboardView,
                    TutorRequestPaymentView,)

app_name = "tutor"

urlpatterns = [
    path('dashboard/', TutorDashboardView.as_view(), name='dashboard'),
    path('hidden/register/', TutorRegistrationView.as_view(), name='register'),
    path("profile/", TutorProfileDashboardView.as_view(), name="profile_dashboard"),
    path('students/',StudentsDashboardView.as_view(), name='students_dashboard'),
    path('child/<int:child_id>/sessions/', TutorSessionsDashboardView.as_view(), name='child_sessions_dashboard'),
    path('sessions/create/<int:child_id>/', CreateSessionView.as_view(), name='create_session'),
    path('child/<int:child_id>/reports/', TutorReportsDashboardView.as_view(), name='child_reports_dashboard'),
    path('reports/create/<int:child_id>/step-1/', ReportSummaryStepView.as_view(), name='create_report_summary_step'),
    path('reports/create/<int:child_id>/step-2/', SessionInsightStepView.as_view(), name='create_sessions_insight_step'),
    path('report/create/<int:child_id>/step-3/', QuizAssignmentInsightStepView.as_view(), name='create_quiz_assignment_step'),
    path('report/create/<int:child_id>/step-4/', MockExamInsightStepView.as_view(), name='create_mock_exam_step'),
    path('report/create/<int:child_id>/step-5/', ChallengesAndSolutionsStepView.as_view(), name='create_challenges_and_solutions_step'),
    path('payment/dashboard/', TutorPaymentDashboardView.as_view(), name='payment_dashboard'),
    path('payment/request/<int:child_id>/', TutorRequestPaymentView.as_view(), name='tutor_request_payment'),
]