from django.contrib import admin
from .models import Booking, BookingSeat


class BookingSeatInline(admin.TabularInline):
    model = BookingSeat
    extra = 0
    can_delete = False
    readonly_fields = ("seat", "show", "price", "is_active")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("booking_code", "user", "show", "status", "total_amount", "hold_expires_at")
    list_filter = ("status",)
    search_fields = ("booking_code", "user__phone")
    inlines = [BookingSeatInline]