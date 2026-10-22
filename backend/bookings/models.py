import secrets
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no 0/O/1/I confusion


def make_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


def make_nonce():
    return secrets.token_hex(8)


class Booking(models.Model):
    HELD, CONFIRMED, CANCELLED, EXPIRED, COMPLETED = "HELD", "CONFIRMED", "CANCELLED", "EXPIRED", "COMPLETED"
    STATUSES = [(s, s.title()) for s in (HELD, CONFIRMED, CANCELLED, EXPIRED, COMPLETED)]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings")
    show = models.ForeignKey("shows.Show", on_delete=models.PROTECT, related_name="bookings")
    status = models.CharField(max_length=10, choices=STATUSES, default=HELD, db_index=True)
    booking_code = models.CharField(max_length=8, unique=True, default=make_code)
    qr_nonce = models.CharField(max_length=16, default=make_nonce)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)   # sum of counter prices, nothing added
    hold_expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="confirmed_bookings")
    payment_mode = models.CharField(max_length=10, blank=True)            # CASH / UPI

    class Meta:
        indexes = [models.Index(fields=["status", "hold_expires_at"])]

    def __str__(self):
        return f"{self.booking_code} ({self.status})"


class BookingSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="items")
    show = models.ForeignKey("shows.Show", on_delete=models.PROTECT, related_name="booked_seats")
    seat = models.ForeignKey("theatres.Seat", on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)   # False once cancelled/expired -> seat is free again

    class Meta:
        constraints = [
            # DB-level guarantee: a seat can be active in only one booking per show
            models.UniqueConstraint(fields=["show", "seat"], condition=Q(is_active=True),
                                    name="uniq_active_seat_per_show"),
        ]