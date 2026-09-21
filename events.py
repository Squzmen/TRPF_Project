"""Поиск по коллекции мероприятий и проверки, восходящие к ПР1."""

from datetime import date

from models import Event


def find_event(events: list[Event], event_id: int) -> Event | None:
    """Найти объект Event по идентификатору."""
    return next((event for event in events if event.id == event_id), None)


def search_events(events: list[Event], query: str) -> list[Event]:
    """Найти события по подстроке названия без учета регистра."""
    return [event for event in events
            if query.strip().casefold() in event.name.casefold()]


def filter_events(events: list[Event], category: str) -> list[Event]:
    """Отобрать события категории."""
    return [event for event in events
            if event.category.casefold() == category.strip().casefold()]


def sort_events(events: list[Event]) -> list[Event]:
    """Вернуть новый список объектов по возрастанию цены."""
    return sorted(events, key=lambda event: (event.ticket_price, event.id))


def get_event_date_status(event_day: date, today: date) -> str:
    """Вернуть статус даты события (сценарий ПР1)."""
    if event_day < today:
        return "Мероприятие уже прошло"
    if event_day == today:
        return "Мероприятие проходит сегодня"
    return "Мероприятие еще впереди"


def get_recommendation(age_allowed: bool, category_suitable: bool,
                       budget_enough: bool, date_available: bool,
                       has_available_seats: bool) -> str:
    """Сохранить порядок и текст причин отказа из ПР1."""
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
