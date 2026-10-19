"""Маршруты приложения catalog (каталог мероприятий)."""

from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.event_list, name="list"),
    path("<int:event_id>/", views.event_detail, name="detail"),
]
