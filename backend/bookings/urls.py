from django.urls import path
from . import views

urlpatterns = [
    path("hold/", views.hold),
    path("my/", views.my_bookings),
    path("<uuid:booking_id>/", views.detail),
    path("<uuid:booking_id>/cancel/", views.cancel),
]