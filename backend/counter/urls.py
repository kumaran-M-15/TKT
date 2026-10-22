from django.urls import path
from . import views

urlpatterns = [
    path("scan/", views.scan_lookup),
    path("bookings/<uuid:booking_id>/confirm/", views.confirm),
]