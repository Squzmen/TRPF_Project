"""Перенос данных из базы ПР7 (data/culture.sqlite) в модели Django ORM.

Стратегия ПР9 – вариант 2: исходная база остаётся источником и не
изменяется, Django работает с db.sqlite3, таблицы которой созданы
миграциями. Запуск из корня проекта после python manage.py migrate:

    python -m db.import_sqlite_to_orm

Идентификаторы записей сохраняются, поэтому связи plans → events и
plans → users переносятся без изменений. Повторный запуск обновляет
совпадающие по id записи (update_or_create) и ничего не дублирует.
"""

import os
import sqlite3
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_DB = BASE_DIR / "data" / "culture.sqlite"


def read_source(source):
    """Прочитать три таблицы исходной базы в списки sqlite3.Row."""
    if not Path(source).exists():
        raise FileNotFoundError(f"Исходная база не найдена: {source}")
    with sqlite3.connect(source) as connection:
        connection.row_factory = sqlite3.Row
        return (
            connection.execute(
                "SELECT id, name, category, event_date, age_limit, "
                "ticket_price, capacity FROM events ORDER BY id"
            ).fetchall(),
            connection.execute(
                "SELECT id, name, age, preferred_category, budget "
                "FROM users ORDER BY id"
            ).fetchall(),
            connection.execute(
                "SELECT id, event_id, user_id, is_cancelled "
                "FROM plans ORDER BY id"
            ).fetchall(),
        )


def import_data(source=SOURCE_DB):
    """Перенести мероприятия, посетителей и записи одной транзакцией."""
    # Модели импортируются после django.setup().
    from django.db import transaction

    from catalog.models import Event
    from planner.models import Plan
    from visitors.models import User

    events, users, plans = read_source(source)
    with transaction.atomic():
        # Сначала независимые сущности, затем записи с внешними ключами.
        for row in events:
            Event.objects.update_or_create(
                pk=row["id"],
                defaults={
                    "name": row["name"],
                    "category": row["category"],
                    "event_date": date.fromisoformat(row["event_date"]),
                    "age_limit": row["age_limit"],
                    "ticket_price": Decimal(str(row["ticket_price"])),
                    "capacity": row["capacity"],
                },
            )
        for row in users:
            User.objects.update_or_create(
                pk=row["id"],
                defaults={
                    "name": row["name"],
                    "age": row["age"],
                    "preferred_category": row["preferred_category"],
                    "budget": Decimal(str(row["budget"])),
                },
            )
        for row in plans:
            Plan.objects.update_or_create(
                pk=row["id"],
                defaults={
                    "event_id": row["event_id"],
                    "user_id": row["user_id"],
                    "is_cancelled": bool(row["is_cancelled"]),
                },
            )
    return {
        "events": Event.objects.count(),
        "users": User.objects.count(),
        "plans": Plan.objects.count(),
    }


def main():
    counts = import_data()
    print("Перенос данных завершён.")
    print(f"Мероприятий: {counts['events']}")
    print(f"Посетителей: {counts['users']}")
    print(f"Записей: {counts['plans']}")


if __name__ == "__main__":
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "leisure.settings")
    import django

    django.setup()
    main()
