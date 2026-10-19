"""Маршруты приложения planner (планы посетителей)."""

from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("", views.plan_list, name="list"),
    path("statistics/", views.statistics, name="statistics"),
    path("<int:plan_id>/", views.plan_detail, name="detail"),
]
