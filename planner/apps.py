"""Конфигурация приложения Планы посетителей."""

from django.apps import AppConfig


class PlannerConfig(AppConfig):
    """Параметры Django-приложения Планы посетителей."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "planner"
    verbose_name = "Планы посетителей"
