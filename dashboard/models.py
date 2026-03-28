from django.conf import settings
from django.db import models


class UserDashboardState(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dashboard_state",
    )
    pins = models.JSONField(default=list, blank=True)
    notes = models.JSONField(default=dict, blank=True)
    hide_tags = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Dashboard state for {self.user.username}"
