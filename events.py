"""Каталог культурных мероприятий и проверки ПР1."""

from datetime import date


def find_event(events: list[dict], event_id: int) -> dict | None:
    """Найти мероприятие по идентификатору."""
    return next((event for event in events if event["id"] == event_id), None)


def search_events(events: list[dict], query: str) -> list[dict]:
    """Найти мероприятия по части названия без учета регистра."""
    return [event for event in events
            if query.strip().casefold() in event["name"].casefold()]


def filter_events(events: list[dict], category: str) -> list[dict]:
    """Отобрать мероприятия нужной категории."""
    return [event for event in events
            if event["category"].casefold() == category.strip().casefold()]


def sort_events(events: list[dict]) -> list[dict]:
    """Отсортировать каталог по цене, сохранив исходный порядок каталога."""
    return sorted(events, key=lambda event: (
        event["ticket_price"], event["id"]
    ))


def is_age_allowed(user_age: int, age_limit: int) -> bool:
    """Проверить возраст посетителя (сценарий ПР1)."""
    return user_age >= age_limit


def is_category_suitable(preferred: str, category: str) -> bool:
    """Проверить соответствие категории (сценарий ПР1)."""
    return preferred.strip().casefold() == category.strip().casefold()


def is_budget_enough(budget: float, price: float) -> bool:
    """Проверить возможность покупки билета (сценарий ПР1)."""
    return budget >= price


def get_event_date_status(event_day: date, today: date) -> str:
    """Определить временной статус мероприятия (сценарий ПР1)."""
    if event_day < today:
        return "Мероприятие уже прошло"
    if event_day == today:
        return "Мероприятие проходит сегодня"
    return "Мероприятие еще впереди"


def get_recommendation(age_allowed: bool, category_suitable: bool,
                       budget_enough: bool, date_available: bool,
                       has_available_seats: bool) -> str:
    """Сформировать рекомендацию по условиям ПР1."""
    if not has_available_seats:
        return "Мероприятие не подходит: свободных мест нет."
    if not date_available:
        return "Мероприятие не подходит: оно уже прошло."
    if not age_allowed:
        return "Мероприятие не подходит: не пройдено возрастное ограничение."
    if not category_suitable:
        return "Мероприятие не подходит по выбранной категории."
    if not budget_enough:
        return "Мероприятие не подходит: стоимость билета превышает бюджет."
    return "Мероприятие подходит. Его можно добавить в план досуга."
