from django.urls import path
from . import views

urlpatterns = [
    path("scan/", views.scan_lookup),
    path("bookings/<uuid:booking_id>/confirm/", views.confirm),
    path("shows/", views.staff_shows),
    path("shows/bulk-booking/", views.bulk_booking),
    path("shows/<int:show_id>/booking/", views.show_booking),
    path("shows/<int:show_id>/cancel/", views.cancel_show),
    path("auto-open/", views.auto_open),
]