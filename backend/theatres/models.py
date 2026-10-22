from django.db import models


class City(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        verbose_name_plural = "cities"

    def __str__(self):
        return self.name


class Theatre(models.Model):
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="theatres")
    name = models.CharField(max_length=150)
    address = models.TextField()
    phone = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)

    # per-theatre rules (tunable in admin)
    hold_cutoff_minutes = models.PositiveSmallIntegerField(
        default=30, help_text="Unpaid holds auto-release this many minutes before showtime")
    booking_close_minutes = models.PositiveSmallIntegerField(
        default=60, help_text="No new holds within this many minutes of showtime")
    max_holds_per_user = models.PositiveSmallIntegerField(default=2)

    def __str__(self):
        return f"{self.name}, {self.city}"


class Screen(models.Model):
    theatre = models.ForeignKey(Theatre, on_delete=models.CASCADE, related_name="screens")
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ("theatre", "name")

    def __str__(self):
        return f"{self.theatre.name} - {self.name}"


class Seat(models.Model):
    TYPES = [("STANDARD", "Standard"), ("PREMIUM", "Premium"), ("RECLINER", "Recliner")]

    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name="seats")
    row_label = models.CharField(max_length=3)
    number = models.PositiveSmallIntegerField()
    seat_type = models.CharField(max_length=10, choices=TYPES, default="STANDARD")

    class Meta:
        unique_together = ("screen", "row_label", "number")
        ordering = ["row_label", "number"]

    def __str__(self):
        return f"{self.row_label}{self.number}"