from datetime import timedelta

from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

from .models import Show, ShowPrice


@admin.action(description="Open booking now (until the show)")
def open_booking(modeladmin, request, qs):
    qs.filter(is_cancelled=False).update(booking_open=True, booking_closes_at=None)


@admin.action(description="Open booking now for 7 days")
def open_7_days(modeladmin, request, qs):
    qs.filter(is_cancelled=False).update(booking_open=True, booking_closes_at=timezone.now() + timedelta(days=7))


@admin.action(description="Close booking")
def close_booking(modeladmin, request, qs):
    qs.update(booking_open=False, booking_opens_at=None, booking_closes_at=timezone.now())


@admin.action(description="Cancel show (does not delete it)")
def cancel_shows(modeladmin, request, qs):
    qs.update(is_cancelled=True, booking_open=False)


def _repeat(modeladmin, request, qs, days):
    created = skipped = 0
    with transaction.atomic():
        for show in qs.select_related("movie", "screen").prefetch_related("prices"):
            for d in range(1, days + 1):
                start = show.start_time + timedelta(days=d)
                if Show.objects.filter(screen=show.screen, start_time=start).exists():
                    skipped += 1
                    continue
                new = Show.objects.create(movie=show.movie, screen=show.screen, start_time=start)
                ShowPrice.objects.bulk_create([
                    ShowPrice(show=new, seat_type=p.seat_type, counter_price=p.counter_price)
                    for p in show.prices.all()])
                created += 1
    modeladmin.message_user(
        request, f"Created {created} shows, skipped {skipped} that already existed.", messages.SUCCESS)


@admin.action(description="Repeat selected shows for the next 7 days")
def repeat_7_days(modeladmin, request, qs):
    _repeat(modeladmin, request, qs, 7)


@admin.action(description="Repeat selected shows for the next 14 days")
def repeat_14_days(modeladmin, request, qs):
    _repeat(modeladmin, request, qs, 14)


class ShowPriceInline(admin.TabularInline):
    model = ShowPrice
    extra = 3


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ("movie", "screen", "start_time", "state", "is_cancelled")
    list_filter = ("screen__theatre", "movie", "is_cancelled", "booking_open")
    inlines = [ShowPriceInline]
    save_as = True          # adds a "Save as new" button on the edit page
    actions = [repeat_7_days, repeat_14_days, open_booking, open_7_days, close_booking, cancel_shows]

    @admin.display(description="Booking")
    def state(self, obj):
        return obj.booking_state()

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("movie", "screen__theatre")

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser      # shows are permanent; cancel instead