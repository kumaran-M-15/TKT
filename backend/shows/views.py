from datetime import date, timedelta

from django.db.models import Q
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
    f = {"is_active": True, "shows__start_time__gt": timezone.now(), "shows__is_cancelled": False}
    if request.query_params.get("city"):
        f["shows__screen__theatre__city_id"] = request.query_params["city"]
    movies = Movie.objects.filter(**f).distinct().order_by("title")
    return Response([{
        "id": m.id, "title": m.title, "language": m.language, "duration_minutes": m.duration_minutes,
        "genre": m.genre, "certificate": m.certificate, "poster": m.poster_src,
    } for m in movies])


@api_view(["GET"])
@permission_classes([AllowAny])
def movie_detail(request, movie_id):
    m = get_object_or_404(Movie, pk=movie_id, is_active=True)
    return Response({
        "id": m.id, "title": m.title, "language": m.language, "duration_minutes": m.duration_minutes,
        "genre": m.genre, "certificate": m.certificate, "poster": m.poster_src,
        "description": m.description, "release_date": m.release_date,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def movie_shows(request, movie_id):
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
        "theatre": {"id": s.screen.theatre_id, "name": s.screen.theatre.name, "address": s.screen.theatre.address},
        "screen": s.screen.name,
        "start_time": s.start_time,
        "state": s.booking_state(),
        "booking_opens_at": s.booking_opens_at,
        "booking_closes_at": s.booking_closes_at,
        "prices": {p.seat_type: str(p.counter_price) for p in s.prices.all()},
    } for s in qs])


@api_view(["GET"])
@permission_classes([AllowAny])
def seat_map(request, show_id):
    show = get_object_or_404(Show.objects.select_related("movie", "screen__theatre"), pk=show_id)
    now = timezone.now()
    taken = set(
        BookingSeat.objects.filter(show=show, is_active=True)
        .exclude(booking__status="HELD", booking__hold_expires_at__lte=now)
        .values_list("seat_id", flat=True))
    prices = {p.seat_type: str(p.counter_price) for p in show.prices.all()}

    sections, cols = {}, 0
    for s in show.screen.seats.all():
        sec = sections.setdefault(
            s.seat_type, {"name": s.seat_type, "price": prices.get(s.seat_type), "rows": {}})
        sec["rows"].setdefault(s.row_label, []).append({
            "id": s.id, "number": s.number, "col": s.col,
            "status": "TAKEN" if s.id in taken else "AVAILABLE"})
        cols = max(cols, s.col + 1)

    theatre = show.screen.theatre
    state = show.booking_state(now)

    local_day = timezone.localtime(show.start_time).date()
    sibs = (Show.objects.filter(movie=show.movie, screen__theatre=theatre, is_cancelled=False,
                                start_time__date=local_day)
            .filter(Q(start_time__gt=now) | Q(pk=show.pk))
            .select_related("screen__theatre").order_by("start_time"))

    return Response({
        "show_id": show.id,
        "movie_id": show.movie_id,
        "movie": show.movie.title,
        "poster": show.movie.poster_src,
        "language": show.movie.language,
        "certificate": show.movie.certificate,
        "theatre": theatre.name,
        "screen": show.screen.name,
        "start_time": show.start_time,
        "state": state,
        "bookable": state == "OPEN",
        "booking_closes_at": show.booking_closes_at,
        "pay_at_counter_before": show.start_time - timedelta(minutes=theatre.hold_cutoff_minutes),
        "prices": prices,
        "cols": cols,
        "siblings": [{"id": s.id, "start_time": s.start_time, "state": s.booking_state(now)} for s in sibs],
        "sections": [{"name": v["name"], "price": v["price"],
                      "rows": [{"label": k, "seats": seats} for k, seats in v["rows"].items()]}
                     for v in sections.values()],
    })