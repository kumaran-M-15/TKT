from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from shows.models import Show
from theatres.models import Seat
from .models import Booking, BookingSeat


class BookingError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _add_strike(user_id):
    u = User.objects.select_for_update().get(pk=user_id)
    u.strike_count += 1
    if u.strike_count >= settings.NOSHOW_STRIKE_LIMIT:          # 5
        u.blocked_until = timezone.now() + timedelta(days=settings.NOSHOW_BLOCK_DAYS)   # 15 days
        u.strike_count = 0
    u.save(update_fields=["strike_count", "blocked_until"])


@transaction.atomic
def expire_stale_holds(show_id=None):
    """Release unpaid holds past their cutoff and add a strike. Celery will call this every minute later."""
    qs = Booking.objects.select_for_update().filter(status=Booking.HELD, hold_expires_at__lte=timezone.now())
    if show_id:
        qs = qs.filter(show_id=show_id)
    count = 0
    for b in qs:
        b.status = Booking.EXPIRED
        b.save(update_fields=["status"])
        b.items.update(is_active=False)
        _add_strike(b.user_id)
        count += 1
    return count


@transaction.atomic
def hold_seats(user, show_id, seat_ids):
    now = timezone.now()

    if user.blocked_until and user.blocked_until > now:
        until = timezone.localtime(user.blocked_until).strftime("%d %b %Y")
        raise BookingError(f"Pay-at-counter holds are paused on your account until {until}.", 403)

    seat_ids = list(dict.fromkeys(seat_ids))                      # de-duplicate, keep order
    if not seat_ids:
        raise BookingError("Select at least one seat")
    if len(seat_ids) > settings.MAX_SEATS_PER_HOLD:
        raise BookingError(f"You can hold at most {settings.MAX_SEATS_PER_HOLD} seats at a time")

    # Lock the show row: concurrent holds for the same show queue up here
    try:
        show = (Show.objects.select_for_update(of=("self",))
                .select_related("screen__theatre").get(pk=show_id))
    except Show.DoesNotExist:
        raise BookingError("Show not found", 404)

    theatre = show.screen.theatre
    if not theatre.is_active:
        raise BookingError("This theatre is not available", 409)

    # Booking window is controlled by theatre staff / admin
    state = show.booking_state(now)
    if state != "OPEN":
        raise BookingError({
            "CANCELLED": "This show has been cancelled.",
            "ENDED": "Online holds are closed for this show. Please book at the counter.",
            "CLOSED": "Booking for this show is closed. Please wait for the theatre to open it again.",
            "NOT_OPEN": "Booking for this show has not opened yet. The theatre will open it soon.",
        }[state], 409)

    hold_expires_at = show.start_time - timedelta(minutes=theatre.hold_cutoff_minutes)
    if hold_expires_at <= now:
        raise BookingError("Too late to hold seats for this show", 409)

    expire_stale_holds(show.id)                                   # free seats from lapsed holds first

    active = Booking.objects.filter(user=user, status=Booking.HELD, show__start_time__gt=now).count()
    if active >= theatre.max_holds_per_user:
        raise BookingError(f"You already have {active} active holds. Pay or cancel one first.", 409)

    seats = list(Seat.objects.filter(id__in=seat_ids, screen_id=show.screen_id))
    if len(seats) != len(seat_ids):
        raise BookingError("Invalid seat selection")

    if BookingSeat.objects.filter(show=show, seat_id__in=seat_ids, is_active=True).exists():
        raise BookingError("One or more seats were just taken. Please choose different seats.", 409)

    prices = {p.seat_type: p.counter_price for p in show.prices.all()}
    if any(s.seat_type not in prices for s in seats):
        raise BookingError("Pricing is not set for this show", 409)
    total = sum((prices[s.seat_type] for s in seats), Decimal("0"))   # server-side, no fees

    booking = Booking.objects.create(user=user, show=show, total_amount=total, hold_expires_at=hold_expires_at)
    BookingSeat.objects.bulk_create(
        [BookingSeat(booking=booking, show=show, seat=s, price=prices[s.seat_type]) for s in seats])
    return booking


@transaction.atomic
def cancel_booking(user, booking_id):
    try:
        b = Booking.objects.select_for_update().get(pk=booking_id, user=user)
    except Booking.DoesNotExist:
        raise BookingError("Booking not found", 404)
    if b.status != Booking.HELD:
        raise BookingError(f"Booking is already {b.status.lower()} and cannot be cancelled here", 409)
    b.status = Booking.CANCELLED
    b.save(update_fields=["status"])
    b.items.update(is_active=False)                                # seats free immediately, no strike
    return b


@transaction.atomic
def confirm_payment(staff, booking_id, mode):
    """Counter staff marks a held booking as paid (cash/UPI). Single use."""
    if mode not in ("CASH", "UPI"):
        raise BookingError("Payment mode must be CASH or UPI")
    try:
        b = (Booking.objects.select_for_update(of=("self",))
             .select_related("show__screen")
             .get(pk=booking_id))
    except Booking.DoesNotExist:
        raise BookingError("Booking not found", 404)

    if b.show.screen.theatre_id != staff.theatre_id:
        raise BookingError("This booking is for a different theatre", 403)
    if b.status != Booking.HELD:
        raise BookingError(f"Booking is already {b.status.lower()}", 409)
    if b.hold_expires_at <= timezone.now():
        raise BookingError("Hold has expired", 410)

    b.status = Booking.CONFIRMED
    b.confirmed_at = timezone.now()
    b.confirmed_by = staff
    b.payment_mode = mode
    b.save(update_fields=["status", "confirmed_at", "confirmed_by", "payment_mode"])
    return b