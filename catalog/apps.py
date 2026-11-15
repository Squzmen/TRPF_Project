"""Конфигурация приложения Каталог мероприятий."""

from django.apps import AppConfig


class CatalogConfig(AppConfig):
    """Параметры Django-приложения Каталог мероприятий."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"
    verbose_name = "Каталог мероприятий"

    def ready(self):
        # Регистронезависимый поиск по кириллице в SQLite.
        from catalog import sqlite_functions

        sqlite_functions.connect()
