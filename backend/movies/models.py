from django.db import models


class Movie(models.Model):
    title = models.CharField(max_length=200)
    language = models.CharField(max_length=40)
    duration_minutes = models.PositiveSmallIntegerField()
    genre = models.CharField(max_length=100, blank=True)
    certificate = models.CharField(max_length=5, blank=True, help_text="U, UA, A")
    poster_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    release_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} ({self.language})"