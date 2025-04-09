from django.urls import path
from .views import ( TutorDashboardView, )

app_name = "tutor"

urlpatterns = [
    path('<slug:tutor_slug>/dashboard/', TutorDashboardView.as_view(), name='dashboard'),
]