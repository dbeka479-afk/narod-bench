from django.contrib import admin

from .models import Result


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("created", "name", "cpu", "single", "multi", "device")
    search_fields = ("name", "cpu")
