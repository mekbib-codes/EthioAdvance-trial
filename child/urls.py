from django.urls import path
from .views import ( ChildDashboardView, )

app_name = "child"

urlpatterns = [
    path('<slug:child_slug>/dashboard/', ChildDashboardView.as_view(), name='dashboard'),
]