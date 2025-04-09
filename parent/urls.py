from django.urls import path
from .views import ( ParentDashboardView, )

app_name = "parent"

urlpatterns = [
    path('<slug:parent_slug>/dashboard/', ParentDashboardView.as_view(), name='dashboard'),
]