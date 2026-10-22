from django.contrib import admin
from .models import Show, ShowPrice

class ShowPriceInline(admin.TabularInline):
    model = ShowPrice
    extra = 3

@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ("movie", "screen", "start_time", "is_cancelled")
    list_filter = ("screen__theatre", "movie", "is_cancelled")
    inlines = [ShowPriceInline]