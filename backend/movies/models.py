from django.db import models


class Movie(models.Model):
    title = models.CharField(max_length=200)
    language = models.CharField(max_length=40)
    duration_minutes = models.PositiveSmallIntegerField()
    genre = models.CharField(max_length=100, blank=True)
    certificate = models.CharField(max_length=5, blank=True, help_text="U, UA, A")
    poster = models.ImageField(upload_to="posters/", blank=True)
    poster_url = models.URLField(blank=True, help_text="Direct image link, used only if no file is uploaded")
    description = models.TextField(blank=True)
    release_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    @property
    def poster_src(self):
        return self.poster.url if self.poster else self.poster_url

    def __str__(self):
        return f"{self.title} ({self.language})"