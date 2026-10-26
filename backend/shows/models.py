from datetime import timedelta

from django.db import models
from django.utils import timezone


class Show(models.Model):
    movie = models.ForeignKey("movies.Movie", on_delete=models.PROTECT, related_name="shows")
    screen = models.ForeignKey("theatres.Screen", on_delete=models.PROTECT, related_name="shows")
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(blank=True)
    is_cancelled = models.BooleanField(default=False)

    # Booking window, controlled only by staff/admin
    booking_open = models.BooleanField(default=False, help_text="Staff switch: tickets can be held now")
    booking_opens_at = models.DateTimeField(null=True, blank=True, help_text="Optional: opens automatically at this time")
    booking_closes_at = models.DateTimeField(null=True, blank=True, help_text="Optional: booking stops at this time")

    class Meta:
        ordering = ["start_time"]

    def save(self, *args, **kwargs):
        if not self.end_time:
            self.end_time = self.start_time + timedelta(minutes=self.movie.duration_minutes + 15)
        super().save(*args, **kwargs)

    def booking_state(self, now=None):
        """CANCELLED / ENDED / CLOSED / OPEN / NOT_OPEN"""
        now = now or timezone.now()
        theatre = self.screen.theatre
        if self.is_cancelled:
            return "CANCELLED"
        if now >= self.start_time - timedelta(minutes=theatre.booking_close_minutes):
            return "ENDED"
        if self.booking_closes_at and now >= self.booking_closes_at:
            return "CLOSED"                      # a manual close always wins
        if self.booking_open or (self.booking_opens_at and now >= self.booking_opens_at):
            return "OPEN"
        if theatre.auto_open_days and self.start_time <= now + timedelta(days=theatre.auto_open_days):
            return "OPEN"                        # theatre's rolling auto-open window
        return "NOT_OPEN"

    def __str__(self):
        return f"{self.movie.title} @ {self.screen} {self.start_time:%d %b %H:%M}"


class ShowPrice(models.Model):
    """The single all-inclusive counter price. Same number the customer pays at the counter."""
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="prices")
    seat_type = models.CharField(max_length=30)
    counter_price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = ("show", "seat_type")

    def __str__(self):
        return f"{self.show_id} {self.seat_type} Rs{self.counter_price}"