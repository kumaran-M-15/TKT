from datetime import date, timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from bookings.models import BookingSeat
from movies.models import Movie
from .models import Show


@api_view(["GET"])
@permission_classes([AllowAny])
def movie_list(request):
    """GET /api/movies/?city=<id>  movies with upcoming shows"""
    f = {"is_active": True, "shows__start_time__gt": timezone.now(), "shows__is_cancelled": False}
    if request.query_params.get("city"):
        f["shows__screen__theatre__city_id"] = request.query_params["city"]
    movies = Movie.objects.filter(**f).distinct().order_by("title")
    return Response([{
        "id": m.id, "title": m.title, "language": m.language, "duration_minutes": m.duration_minutes,
        "genre": m.genre, "certificate": m.certificate, "poster_url": m.poster_url,
    } for m in movies])


@api_view(["GET"])
@permission_classes([AllowAny])
def movie_shows(request, movie_id):
    """GET /api/movies/<id>/shows/?city=<id>&date=YYYY-MM-DD"""
    qs = (Show.objects.filter(movie_id=movie_id, is_cancelled=False, start_time__gt=timezone.now())
          .select_related("screen__theatre").prefetch_related("prices"))
    if request.query_params.get("city"):
        qs = qs.filter(screen__theatre__city_id=request.query_params["city"])
    if request.query_params.get("date"):
        try:
            qs = qs.filter(start_time__date=date.fromisoformat(request.query_params["date"]))
        except ValueError:
            return Response({"error": "date must be YYYY-MM-DD"}, status=400)
    return Response([{
        "id": s.id,
        "theatre": {"id": s.screen.theatre_id, "name": s.screen.theatre.name},
        "screen": s.screen.name,
        "start_time": s.start_time,
        "prices": {p.seat_type: str(p.counter_price) for p in s.prices.all()},
    } for s in qs])


@api_view(["GET"])
@permission_classes([AllowAny])
def seat_map(request, show_id):
    show = get_object_or_404(Show.objects.select_related("movie", "screen__theatre"), pk=show_id)
    now = timezone.now()
    taken = set(
        BookingSeat.objects.filter(show=show, is_active=True)
        .exclude(booking__status="HELD", booking__hold_expires_at__lte=now)   # lapsed holds count as free
        .values_list("seat_id", flat=True))

    rows = {}
    for s in show.screen.seats.all():
        rows.setdefault(s.row_label, []).append({
            "id": s.id, "number": s.number, "type": s.seat_type,
            "status": "TAKEN" if s.id in taken else "AVAILABLE"})

    theatre = show.screen.theatre
    closes_at = show.start_time - timedelta(minutes=theatre.booking_close_minutes)
    return Response({
        "show_id": show.id,
        "movie": show.movie.title,
        "theatre": theatre.name,
        "screen": show.screen.name,
        "start_time": show.start_time,
        "bookable": (not show.is_cancelled) and now < closes_at,
        "pay_at_counter_before": show.start_time - timedelta(minutes=theatre.hold_cutoff_minutes),
        "prices": {p.seat_type: str(p.counter_price) for p in show.prices.all()},
        "rows": rows,
    })