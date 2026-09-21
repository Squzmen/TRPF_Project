"""Чтение и надежная запись JSON-файлов приложения."""

import json
import math
import os
import tempfile
from datetime import date
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"
EVENTS_FILE = DATA_DIR / "events.json"
PLANS_FILE = DATA_DIR / "plans.json"


class StorageError(Exception):
    """Данные отсутствуют, повреждены или не могут быть сохранены."""


def load_json(path: Path) -> list[dict]:
    """Загрузить список словарей из JSON-файла."""
    try:
        with path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StorageError(f"Ошибка чтения {path}: {error}") from error
    if not isinstance(data, list) or not all(
        isinstance(item, dict) for item in data
    ):
        raise StorageError(f"Файл {path} должен содержать список объектов.")
    return data


def validate_data(events: list[dict], plans: list[dict]) -> None:
    """Проверить поля, ссылки и вместимость данных перед работой."""
    event_ids = set()
    for event in events:
        try:
            event_id = event["id"]
            name = event["name"]
            category = event["category"]
            event_day = event["event_date"]
            age = event["age_limit"]
            price = event["ticket_price"]
            capacity = event["capacity"]
            if (type(event_id) is not int or event_id <= 0 or
                    event_id in event_ids or
                    not isinstance(name, str) or not name.strip() or
                    not isinstance(category, str) or not category.strip() or
                    not isinstance(event_day, str) or
                    type(age) is not int or age < 0 or
                    type(price) not in (int, float) or
                    not math.isfinite(price) or price < 0 or
                    type(capacity) is not int or capacity < 0):
                raise ValueError("недопустимое поле мероприятия")
            date.fromisoformat(event_day)
            event_ids.add(event_id)
        except (KeyError, ValueError, TypeError) as error:
            raise StorageError(f"Некорректное мероприятие: {error}") from error

    plan_ids = set()
    occupations = {}
    users = set()
    for plan in plans:
        try:
            plan_id = plan["id"]
            event_id = plan["event_id"]
            name = plan["user_name"]
            age = plan["user_age"]
            category = plan["preferred_category"]
            budget = plan["budget"]
            if (type(plan_id) is not int or plan_id <= 0 or
                    plan_id in plan_ids or type(event_id) is not int or
                    event_id not in event_ids or
                    not isinstance(name, str) or not name.strip() or
                    not isinstance(category, str) or not category.strip() or
                    type(age) is not int or age < 0 or
                    type(budget) not in (int, float) or
                    not math.isfinite(budget) or budget < 0 or
                    (event_id, name.strip().casefold()) in users):
                raise ValueError("недопустимое поле записи")
            plan_ids.add(plan_id)
            users.add((event_id, name.strip().casefold()))
            occupations[event_id] = occupations.get(event_id, 0) + 1
        except (KeyError, ValueError, TypeError) as error:
            raise StorageError(f"Некорректная запись: {error}") from error
    for event in events:
        if occupations.get(event["id"], 0) > event["capacity"]:
            raise StorageError("Число записей превышает вместимость.")


def load_data(events_path: Path = EVENTS_FILE,
              plans_path: Path = PLANS_FILE) -> tuple[list[dict], list[dict]]:
    """Загрузить и проверить оба файла приложения."""
    events = load_json(events_path)
    plans = load_json(plans_path)
    validate_data(events, plans)
    return events, plans


def save_plans(plans: list[dict], path: Path = PLANS_FILE) -> None:
    """Сохранить планы во временный файл и заменить им исходный."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".plans-", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(plans, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    except (OSError, TypeError, ValueError) as error:
        raise StorageError(f"Ошибка записи {path}: {error}") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
