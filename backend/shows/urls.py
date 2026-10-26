from django.urls import path
from . import views

urlpatterns = [
    path("movies/", views.movie_list),
    path("movies/<int:movie_id>/", views.movie_detail),
    path("movies/<int:movie_id>/shows/", views.movie_shows),
    path("shows/<int:show_id>/seats/", views.seat_map),
]