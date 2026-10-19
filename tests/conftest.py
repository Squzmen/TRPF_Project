"""Тестовые объекты предметной области и настройка Django для тестов."""

import os
from datetime import date

import pytest

from models import Event, User


@pytest.fixture
def event():
    """Спектакль с одним местом и будущей датой."""
    return Event(1, "Спектакль «Гамлет»", "театр",
                 date(2099, 10, 17), 12, 1500, 1)


@pytest.fixture
def user():
    """Посетитель, которому спектакль подходит."""
    return User(1, "Анна", 20, "театр", 2000)


def pytest_configure(config):
    """Подготовить Django до сбора тестов веб-слоя (ПР5)."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "leisure.settings")
    import django
    from django.test.utils import setup_test_environment
    django.setup()
    setup_test_environment()
