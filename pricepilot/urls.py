"""Top-level URL configuration for PricePilot AI."""
from django.contrib import admin
from django.urls import include, path

from pricing import views as pricing_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("pricing.urls")),
    path("", pricing_views.dashboard, name="dashboard"),
]
