from django.urls import path
from session.views import ChildSessionsDashboard
app_name = 'session'

urlpatterns = [
    path('child/<int:child_id>/sessions/', ChildSessionsDashboard.as_view(), name='child_sessions_dashboard'),
]