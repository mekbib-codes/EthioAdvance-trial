from django.urls import path
from .views import CreateReportView
app_name = 'report'

urlpatterns = [
    path('create/<int:child_id>/', CreateReportView.as_view(), name='create')
]