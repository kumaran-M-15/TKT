import io

import qrcode
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from bookings import services
from bookings.models import Booking
from bookings.services import BookingError
from bookings.tokens import make_qr_token, read_qr_token
from core.permissions import IsCounterStaff


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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def booking_qr(request, booking_id):
    """Customer's QR image (owner only)."""
    b = Booking.objects.filter(pk=booking_id, user=request.user).first()
    if not b:
        return Response({"error": "Booking not found"}, status=404)
    img = qrcode.make(make_qr_token(b))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def booking_qr_token(request, booking_id):
    """Same token as text, handy for testing without scanning."""
    b = Booking.objects.filter(pk=booking_id, user=request.user).first()
    if not b:
        return Response({"error": "Booking not found"}, status=404)
    return Response({"token": make_qr_token(b), "booking_code": b.booking_code})


@api_view(["POST"])
@permission_classes([IsCounterStaff])
def scan_lookup(request):
    """Staff scans a QR token OR types the 8-character booking code."""
    token, code = request.data.get("token"), request.data.get("code")
    b = None
    if token:
        try:
            data = read_qr_token(token)
        except Exception:
            return Response({"error": "Invalid QR"}, status=400)
        b = _load(pk=data["b"], qr_nonce=data["n"]).first()
    elif code:
        b = _load(booking_code=str(code).strip().upper()).first()
    else:
        return Response({"error": "Send token or code"}, status=400)

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
    return Response(_summary(_load(pk=booking_id).get()))