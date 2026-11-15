"""Конфигурация приложения Посетители."""

from django.apps import AppConfig


class VisitorsConfig(AppConfig):
    """Параметры Django-приложения Посетители."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "visitors"
    verbose_name = "Посетители"
