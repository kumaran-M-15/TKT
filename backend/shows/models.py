from datetime import timedelta
from django.db import models


class Show(models.Model):
    movie = models.ForeignKey("movies.Movie", on_delete=models.PROTECT, related_name="shows")
    screen = models.ForeignKey("theatres.Screen", on_delete=models.PROTECT, related_name="shows")
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(blank=True)
    is_cancelled = models.BooleanField(default=False)

    class Meta:
        ordering = ["start_time"]

    def save(self, *args, **kwargs):
        if not self.end_time:
            self.end_time = self.start_time + timedelta(minutes=self.movie.duration_minutes + 15)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.movie.title} @ {self.screen} {self.start_time:%d %b %H:%M}"


class ShowPrice(models.Model):
    """The single all-inclusive counter price. Same number the customer pays at the counter."""
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="prices")
    seat_type = models.CharField(max_length=10)
    counter_price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = ("show", "seat_type")

    def __str__(self):
        return f"{self.show_id} {self.seat_type} Rs{self.counter_price}"