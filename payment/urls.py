from django.urls import path
from .views import InitializePaymentView, ChapaWebhookView
app_name = 'payment'

urlpatterns = [
    path("initialize/<int:child_id>/", InitializePaymentView.as_view(), name="initialize"),
    path('webhook/', ChapaWebhookView.as_view(), name='chapa_webhook'),
]