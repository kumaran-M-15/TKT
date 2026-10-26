from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from bookings import services
from bookings.emails import send_ticket_email
from bookings.models import Booking
from bookings.services import BookingError
from bookings.tokens import make_qr_token, read_qr_token
from core.permissions import IsCounterStaff
from shows.models import Show


def _load(**f):
    return (Booking.objects.filter(**f)
            .select_related("user", "show__movie", "show__screen__theatre")
            .prefetch_related("items__seat"))


def _summary(b):
    held = b.status == Booking.HELD
    return {
        "booking_id": str(b.id),
        "booking_code": b.booking_code,
        "status": b.status,
        "customer": {"name": b.user.name, "phone_last4": b.user.phone[-4:]},
        "movie": b.show.movie.title,
        "screen": b.show.screen.name,
        "show_time": b.show.start_time,
        "seats": [f"{i.seat.row_label}{i.seat.number}" for i in b.items.all()],
        "amount_to_collect": str(b.total_amount) if held else "0.00",
        "can_confirm": held and b.hold_expires_at > timezone.now(),
        "payment_mode": b.payment_mode,
    }


# NOTE: the customer QR image (/qr/) and ticket download (/ticket.png) live in
# bookings/ticket_views.py and are routed from core/urls.py.

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def booking_qr_token(request, booking_id):
    """Signed token as text, handy for testing."""
    b = Booking.objects.filter(pk=booking_id, user=request.user).first()
    if not b:
        return Response({"error": "Booking not found"}, status=404)
    return Response({"token": make_qr_token(b), "booking_code": b.booking_code})


@api_view(["POST"])
@permission_classes([IsCounterStaff])
def scan_lookup(request):
    """Staff scans the QR (8-character code) or types the code."""
    token = (request.data.get("token") or "").strip()
    code = (request.data.get("code") or "").strip().upper()
    if token and len(token) <= 12 and not code:     # scanner sent the short code as "token"
        code, token = token.upper(), ""

    b = None
    if code:
        b = _load(booking_code=code).first()
    elif token:
        try:
            data = read_qr_token(token)
        except Exception:
            return Response(
                {"error": "This is an old or unreadable QR. Ask the customer to open My tickets, or type the booking code."},
                status=400)
        b = _load(pk=data["b"], qr_nonce=data["n"]).first()
    else:
        return Response({"error": "Type the booking code or scan a QR first."}, status=400)

    if not b:
        return Response({"error": "Booking not found"}, status=404)
    if b.show.screen.theatre_id != request.user.theatre_id:
        return Response({"error": "This booking is for a different theatre"}, status=403)
    return Response(_summary(b))


@api_view(["POST"])
@permission_classes([IsCounterStaff])
def confirm(request, booking_id):
    try:
        services.confirm_payment(request.user, booking_id, request.data.get("mode", "CASH"))
    except BookingError as e:
        return Response({"error": e.message}, status=e.status)
    send_ticket_email(booking_id, "CONFIRMED")   # payment received + paid ticket attached
    return Response(_summary(_load(pk=booking_id).get()))


# ---------- show management (staff) ----------

def _show_row(s):
    return {
        "id": s.id, "movie": s.movie.title,
        "screen": s.screen.name, "start_time": s.start_time,
        "state": s.booking_state(), "booking_closes_at": s.booking_closes_at,
        "is_cancelled": s.is_cancelled,
    }


def _my_shows(user):
    return (Show.objects.filter(screen__theatre_id=user.theatre_id)
            .select_related("movie", "screen__theatre"))


@api_view(["GET"])
@permission_classes([IsCounterStaff])
def staff_shows(request):
    qs = _my_shows(request.user).filter(start_time__gt=timezone.now()).order_by("start_time")[:100]
    return Response([_show_row(s) for s in qs])


@api_view(["POST"])
@permission_classes([IsCounterStaff])
def show_booking(request, show_id):
    """action: open | open_days (days) | close"""
    show = _my_shows(request.user).filter(pk=show_id).first()
    if not show:
        return Response({"error": "Show not found"}, status=404)
    if show.is_cancelled:
        return Response({"error": "Show is cancelled"}, status=409)

    action, now = request.data.get("action"), timezone.now()
    if action == "open":
        show.booking_open, show.booking_opens_at, show.booking_closes_at = True, None, None
    elif action == "open_days":
        try:
            days = int(request.data.get("days", 7))
        except (TypeError, ValueError):
            return Response({"error": "days must be a number"}, status=400)
        if not 1 <= days <= 60:
            return Response({"error": "days must be between 1 and 60"}, status=400)
        show.booking_open, show.booking_opens_at = True, None
        show.booking_closes_at = now + timedelta(days=days)
    elif action == "close":
        show.booking_open, show.booking_opens_at, show.booking_closes_at = False, None, now
    else:
        return Response({"error": "action must be open, open_days or close"}, status=400)
    show.save(update_fields=["booking_open", "booking_opens_at", "booking_closes_at"])
    return Response(_show_row(show))


@api_view(["POST"])
@permission_classes([IsCounterStaff])
def bulk_booking(request):
    """Open or close every upcoming show starting within the next N days at this theatre."""
    action = request.data.get("action")
    try:
        days = int(request.data.get("days", 7))
    except (TypeError, ValueError):
        return Response({"error": "days must be a number"}, status=400)
    if action not in ("open", "close") or not 1 <= days <= 60:
        return Response({"error": "action open/close and days 1-60 required"}, status=400)
    now = timezone.now()
    qs = _my_shows(request.user).filter(
        is_cancelled=False, start_time__gt=now, start_time__lte=now + timedelta(days=days))
    if action == "open":
        n = qs.update(booking_open=True, booking_closes_at=None)
    else:
        n = qs.update(booking_open=False, booking_opens_at=None, booking_closes_at=now)
    return Response({"updated": n})


@api_view(["POST"])
@permission_classes([IsCounterStaff])
@transaction.atomic
def cancel_show(request, show_id):
    if request.user.role != "MANAGER":
        return Response({"error": "Only a theatre manager can cancel a show"}, status=403)
    show = (Show.objects.select_for_update(of=("self",))
            .filter(pk=show_id, screen__theatre_id=request.user.theatre_id).first())
    if not show:
        return Response({"error": "Show not found"}, status=404)
    if Booking.objects.filter(show=show, status=Booking.CONFIRMED).exists():
        return Response({"error": "Paid bookings exist. Contact the platform admin to cancel this show."}, status=409)
    for b in Booking.objects.select_for_update().filter(show=show, status=Booking.HELD):
        b.status = Booking.CANCELLED          # no strike: it is not the customer's fault
        b.save(update_fields=["status"])
        b.items.update(is_active=False)
    show.is_cancelled, show.booking_open = True, False
    show.save(update_fields=["is_cancelled", "booking_open"])
    return Response({"cancelled": show.id})


@api_view(["GET", "POST"])
@permission_classes([IsCounterStaff])
def auto_open(request):
    """GET the theatre's auto-open window; POST {"days": N} to change it (0 turns it off)."""
    theatre = request.user.theatre
    if request.method == "POST":
        try:
            days = int(request.data.get("days"))
        except (TypeError, ValueError):
            return Response({"error": "days must be a number"}, status=400)
        if not 0 <= days <= 60:
            return Response({"error": "days must be between 0 and 60"}, status=400)
        theatre.auto_open_days = days
        theatre.save(update_fields=["auto_open_days"])
    return Response({"days": theatre.auto_open_days})