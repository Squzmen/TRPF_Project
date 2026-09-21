"""Преобразование JSON в коллекции объектов и обратное сохранение."""

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path

from models import Event, Plan, User


DATA_DIR = Path(__file__).resolve().parent / "data"
EVENTS_FILE = DATA_DIR / "events.json"
USERS_FILE = DATA_DIR / "users.json"
PLANS_FILE = DATA_DIR / "plans.json"


class StorageError(Exception):
    """Данные отсутствуют, некорректны или не могут быть записаны."""


def load_json(path: Path) -> list[dict]:
    """Загрузить список записей из существующего UTF-8 файла."""
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


def _unique_ids(objects: list, kind: str) -> None:
    """Запретить дублирующиеся идентификаторы в одном каталоге."""
    ids = [item.id for item in objects]
    if len(ids) != len(set(ids)):
        raise StorageError(f"Повторяющийся ID: {kind}.")


def load_data(events_path: Path = EVENTS_FILE,
              plans_path: Path = PLANS_FILE,
              users_path: Path = USERS_FILE
              ) -> tuple[list[Event], list[User], list[Plan]]:
    """Восстановить объекты, связи и записи старого формата ПР2."""
    raw_events = load_json(events_path)
    raw_users = load_json(users_path)
    raw_plans = load_json(plans_path)
    try:
        events = [Event.from_data(item) for item in raw_events]
        users = [User.from_data(item) for item in raw_users]
        _unique_ids(events, "мероприятия")
        _unique_ids(users, "пользователя")
        event_by_id = {event.id: event for event in events}
        user_by_id = {user.id: user for user in users}
        next_user_id = max(user_by_id, default=0) + 1
        plans = []
        for item in raw_plans:
            event = event_by_id[item["event_id"]]
            if "user_id" in item:
                user = user_by_id[item["user_id"]]
                cancelled = item["is_cancelled"]
            else:
                # ПР2 хранила свойства посетителя прямо в записи.
                candidate = User(next_user_id, item["user_name"],
                                 item["user_age"],
                                 item["preferred_category"], item["budget"])
                user = next((existing for existing in users if
                             existing.name.casefold() ==
                             candidate.name.casefold() and
                             existing.age == candidate.age and
                             existing.preferred_category.casefold() ==
                             candidate.preferred_category.casefold() and
                             existing.budget == candidate.budget), None)
                if user is None:
                    user = candidate
                    next_user_id += 1
                    users.append(user)
                    user_by_id[user.id] = user
                cancelled = False
            plans.append(Plan(item["id"], event, user, cancelled))
        _unique_ids(plans, "записи")
        active = set()
        for plan in plans:
            if plan.is_cancelled:
                continue
            key = (plan.event.id, plan.user.name.casefold())
            if key in active:
                raise StorageError("Найдена повторная активная запись.")
            active.add(key)
        from plans import remaining_seats
        if any(remaining_seats(plans, event) < 0 for event in events):
            raise StorageError("Число записей превышает вместимость.")
    except (KeyError, TypeError, ValueError) as error:
        raise StorageError(f"Некорректные данные JSON: {error}") from error
    return events, users, plans


def save_json(data: list[dict], path: Path) -> None:
    """Записать данные во временный файл и атомарно заменить JSON."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".data-", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    except (OSError, TypeError, ValueError) as error:
        raise StorageError(f"Ошибка записи {path}: {error}") from error
    finally:
        if temporary is not None:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)


def save_events(events: list[Event], path: Path = EVENTS_FILE) -> None:
    """Сохранить каталог объектов Event."""
    save_json([event.to_data() for event in events], path)


def save_users(users: list[User], path: Path = USERS_FILE) -> None:
    """Сохранить пользователей перед сохранением связанных записей."""
    save_json([user.to_data() for user in users], path)


def save_plans(plans: list[Plan], path: Path = PLANS_FILE) -> None:
    """Сохранить записи как идентификаторы связанных объектов."""
    save_json([plan.to_data() for plan in plans], path)
