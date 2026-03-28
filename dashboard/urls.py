from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("api/overview/", views.api_overview, name="api_overview"),
    path("api/themes/", views.api_themes, name="api_themes"),
    path("api/theme-quotes/", views.api_theme_quotes, name="api_theme_quotes"),
]
