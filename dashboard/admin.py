from django.contrib import admin

from .models import UserDashboardState


@admin.register(UserDashboardState)
class UserDashboardStateAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("updated_at",)
