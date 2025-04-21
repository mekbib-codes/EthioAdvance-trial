from django.urls import path
from .views import MarkNotificationsAsReadView

app_name = 'actions'

urlpatterns = [
    path('notifications/mark-as-read/', MarkNotificationsAsReadView.as_view(), name='mark_notifications_as_read'),
]