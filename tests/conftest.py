"""Тестовые объекты предметной области."""

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
