"""Записи в план досуга, проверка доступности и статистика."""

from datetime import date

from events import (
    get_recommendation, is_age_allowed, is_budget_enough,
    is_category_suitable,
)


def find_plan(plans: list[dict], plan_id: int) -> dict | None:
    """Найти запись по идентификатору."""
    return next((plan for plan in plans if plan["id"] == plan_id), None)


def remaining_seats(plans: list[dict], event: dict) -> int:
    """Посчитать оставшиеся места с учетом существующих записей."""
    occupied = sum(1 for plan in plans if plan["event_id"] == event["id"])
    return event["capacity"] - occupied


def plan_recommendation(plans: list[dict], event: dict, age: int,
                        category: str, budget: float,
                        today: date | None = None) -> str:
    """Применить проверки ПР1 к записи из каталога."""
    event_day = date.fromisoformat(event["event_date"])
    return get_recommendation(
        is_age_allowed(age, event["age_limit"]),
        is_category_suitable(category, event["category"]),
        is_budget_enough(budget, event["ticket_price"]),
        event_day >= (today or date.today()),
        remaining_seats(plans, event) > 0,
    )


def create_plan(plans: list[dict], event: dict, name: str, age: int,
                category: str, budget: float,
                today: date | None = None) -> dict:
    """Добавить запись после проверки ограничений и дублей."""
    name = name.strip()
    if not name or age < 0 or budget < 0:
        raise ValueError("Имя, возраст или бюджет указаны неверно.")
    if any(plan["event_id"] == event["id"] and
           plan["user_name"].casefold() == name.casefold() for plan in plans):
        raise ValueError("Пользователь уже записан на это мероприятие.")
    reason = plan_recommendation(plans, event, age, category, budget, today)
    if not reason.startswith("Мероприятие подходит"):
        raise ValueError(reason)
    plan = {
        "id": max((item["id"] for item in plans), default=0) + 1,
        "event_id": event["id"],
        "user_name": name,
        "user_age": age,
        "preferred_category": category.strip(),
        "budget": budget,
    }
    plans.append(plan)
    return plan


def cancel_plan(plans: list[dict], plan_id: int) -> dict:
    """Удалить запись по ID и вернуть ее для возможного отката."""
    plan = find_plan(plans, plan_id)
    if plan is None:
        raise ValueError("Запись не найдена.")
    plans.remove(plan)
    return plan


def plan_statistics(events: list[dict], plans: list[dict]) -> dict:
    """Подсчитать мероприятия, записи и стоимость выбранных билетов."""
    prices = {event["id"]: event["ticket_price"] for event in events}
    return {
        "events": len(events),
        "plans": len(plans),
        "total_price": sum(prices[plan["event_id"]] for plan in plans),
    }
