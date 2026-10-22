from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("phone", "name", "role", "theatre", "strike_count", "blocked_until")
    search_fields = ("phone", "name")
    list_filter = ("role", "theatre")