"""Маршруты приложения planner (планы посетителей)."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.plan_list, name="plan_list"),
    path("<int:plan_id>/", views.plan_detail, name="plan_detail"),
]
