from django.contrib import admin
from .models import City, Theatre, Screen, Seat

admin.site.register(City)

@admin.register(Theatre)
class TheatreAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "hold_cutoff_minutes", "max_holds_per_user", "is_active")
    list_filter = ("city", "is_active")

@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ("name", "theatre")

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("screen", "row_label", "number", "seat_type")
    list_filter = ("screen", "seat_type")