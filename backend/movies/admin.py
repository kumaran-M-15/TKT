from django.contrib import admin
from .models import Movie

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "language", "duration_minutes", "is_active")
    search_fields = ("title",)

def has_delete_permission(self, request, obj=None):
    return request.user.is_superuser