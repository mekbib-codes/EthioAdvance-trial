from django.urls import path
from .views import (home,
                    RoleBasedLoginView)
from django.contrib.auth.views import LogoutView

app_name = "accounts"

urlpatterns = [
    path("", home, name="home"),
    path("login/", RoleBasedLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

]