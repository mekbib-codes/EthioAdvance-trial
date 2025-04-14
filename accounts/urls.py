from django.urls import path

from .views.home import home
from .views.role_based_login import RoleBasedLoginView
from .views.otp_verification import OTPVerificationView, OTPResendView
from .views.password_reset import (
    PasswordResetRequestedView,
    PasswordResetOTPVerificationView,
    SetNewPasswordView,
)
from django.contrib.auth.views import LogoutView

app_name = "accounts"

urlpatterns = [
    path("", home, name="home"),
    path("login/", RoleBasedLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path('verify_otp/',OTPVerificationView.as_view(),name='otp_verification'),
    path('resend_otp/<str:purpose>',OTPResendView.as_view(),name='resend_otp'),
    path('reset_password/', PasswordResetRequestedView.as_view(), name="reset_password"),
    path('reset_password/verify_otp', PasswordResetOTPVerificationView.as_view(), name="password_reset_verify"),
    path('set_new_password', SetNewPasswordView.as_view(), name="set_new_password"),
]