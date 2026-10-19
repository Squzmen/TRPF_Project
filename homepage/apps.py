"""Конфигурация приложения Главная страница."""

from django.apps import AppConfig


class HomepageConfig(AppConfig):
    """Параметры Django-приложения Главная страница."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "homepage"
    verbose_name = "Главная страница"
