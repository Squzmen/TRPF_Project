"""Маршруты приложения catalog (каталог мероприятий)."""

from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.event_list, name="list"),
    path("search/", views.event_search, name="search"),
    path("recommend/", views.event_recommend, name="recommend"),
    path("<int:event_id>/", views.event_detail, name="detail"),
]
