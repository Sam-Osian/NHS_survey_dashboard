from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

urlpatterns = [
    path("", login_required(views.home), name="home"),
    path("api/overview/", login_required(views.api_overview), name="api_overview"),
    path("api/themes/", login_required(views.api_themes), name="api_themes"),
    path(
        "api/theme-quotes/",
        login_required(views.api_theme_quotes),
        name="api_theme_quotes",
    ),
    path("api/user-state/", login_required(views.api_user_state), name="api_user_state"),
]
