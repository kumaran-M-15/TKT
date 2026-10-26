import io

import qrcode
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Booking
from .ticket_image import render_ticket


def _mine(request, booking_id):
    return (Booking.objects.filter(pk=booking_id, user=request.user)
            .select_related("show__movie", "show__screen__theatre")
            .prefetch_related("items__seat").first())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def booking_qr(request, booking_id):
    """Small QR (just the booking code) so it scans easily."""
    b = _mine(request, booking_id)
    if not b:
        return Response({"error": "Booking not found"}, status=404)
    buf = io.BytesIO()
    qrcode.make(b.booking_code, box_size=12, border=2).save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def booking_ticket(request, booking_id):
    b = _mine(request, booking_id)
    if not b:
        return Response({"error": "Booking not found"}, status=404)
    return HttpResponse(render_ticket(b), content_type="image/png")