"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from counter import views as counter_views

def health(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/auth/", include("accounts.urls")),

    # QR routes must come BEFORE the bookings include
    path("api/bookings/<uuid:booking_id>/qr/", counter_views.booking_qr),
    path("api/bookings/<uuid:booking_id>/qr-token/", counter_views.booking_qr_token),

    path("api/bookings/", include("bookings.urls")),
    path("api/counter/", include("counter.urls")),
    path("api/", include("shows.urls")),
]