"""Тестовые объекты предметной области и данные для тестов Django.

Настройки Django подключает pytest-django (параметр
DJANGO_SETTINGS_MODULE в pytest.ini); тесты с базой данных работают с
отдельной тестовой базой, а не с db.sqlite3.
"""

from datetime import date

import pytest
from django.test import Client

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


@pytest.fixture
def project_data(db):
    """Тестовая база, заполненная из data/culture.sqlite скриптом ПР9."""
    from db.import_sqlite_to_orm import import_data

    return import_data()


@pytest.fixture
def client():
    """Тестовый клиент, обращающийся к разрешённому хосту localhost."""
    return Client(SERVER_NAME="localhost")
