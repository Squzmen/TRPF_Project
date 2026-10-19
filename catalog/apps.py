"""Конфигурация приложения Каталог мероприятий."""

from django.apps import AppConfig


class CatalogConfig(AppConfig):
    """Параметры Django-приложения Каталог мероприятий."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"
    verbose_name = "Каталог мероприятий"
