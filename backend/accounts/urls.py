from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path("otp/send/", views.send_otp),
    path("otp/verify/", views.verify_otp),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("me/", views.me),
]