from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import services
from .emails import send_ticket_email
from .models import Booking
from .services import BookingError


class HoldSerializer(serializers.Serializer):
    show_id = serializers.IntegerField()
    seat_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1, max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True)


def _load(**filters):
    return (Booking.objects.filter(**filters)
            .select_related("show__movie", "show__screen__theatre")
            .prefetch_related("items__seat"))


def booking_dict(b):
    return {
        "id": str(b.id),
        "booking_code": b.booking_code,
        "status": b.status,
        "movie": b.show.movie.title,
        "theatre": b.show.screen.theatre.name,
        "screen": b.show.screen.name,
        "show_time": b.show.start_time,
        "seats": [f"{i.seat.row_label}{i.seat.number}" for i in b.items.all()],
        "total_amount": str(b.total_amount),
        "pay_at_counter_before": b.hold_expires_at if b.status == Booking.HELD else None,
        "note": "No booking fee. Pay exactly this amount at the counter.",
    }


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def hold(request):
    if "amount" in request.data or "total_amount" in request.data:
        return Response({"error": "Price is set by the server"}, status=400)
    s = HoldSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    try:
        b = services.hold_seats(request.user, s.validated_data["show_id"], s.validated_data["seat_ids"])
    except BookingError as e:
        return Response({"error": e.message}, status=e.status)
    except IntegrityError:
        return Response({"error": "Seat just taken. Please choose different seats."}, status=409)

    email = s.validated_data.get("email")
    if email and request.user.email != email:
        request.user.email = email
        request.user.save(update_fields=["email"])

    send_ticket_email(b.pk, "HELD")      # background thread, never blocks or breaks the booking
    return Response(booking_dict(_load(pk=b.pk).get()), status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_bookings(request):
    qs = _load(user=request.user).order_by("-created_at")[:50]
    return Response([booking_dict(b) for b in qs])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detail(request, booking_id):
    b = _load(pk=booking_id, user=request.user).first()
    if not b:
        return Response({"error": "Booking not found"}, status=404)
    return Response(booking_dict(b))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel(request, booking_id):
    try:
        services.cancel_booking(request.user, booking_id)
    except BookingError as e:
        return Response({"error": e.message}, status=e.status)
    return Response(booking_dict(_load(pk=booking_id).get()))