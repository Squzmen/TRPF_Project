"""Маршруты приложения planner (планы посетителей)."""

from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("", views.plan_list, name="list"),
    path("statistics/", views.statistics, name="statistics"),
    path("create/", views.plan_create, name="create"),
    path("<int:plan_id>/", views.plan_detail, name="detail"),
    path("<int:plan_id>/edit/", views.plan_update, name="update"),
    path("<int:plan_id>/cancel/", views.plan_cancel, name="cancel"),
]
