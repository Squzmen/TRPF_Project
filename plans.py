"""Операции над коллекцией связанных объектов Plan."""

from datetime import date

from events import get_recommendation
from models import Event, Plan, User


def find_plan(plans: list[Plan], plan_id: int) -> Plan | None:
    """Найти запись по её идентификатору."""
    return next((plan for plan in plans if plan.id == plan_id), None)


def remaining_seats(plans: list[Plan], event: Event) -> int:
    """Учесть только активные записи на данное событие."""
    occupied = sum(1 for plan in plans if not plan.is_cancelled and
                   plan.event.id == event.id)
    return event.capacity - occupied


def plan_recommendation(plans: list[Plan], event: Event, user: User,
                        today: date | None = None) -> str:
    """Применить проверки ПР1 к взаимодействию User и Event."""
    return get_recommendation(
        event.is_age_allowed(user.age),
        user.is_interested_in(event),
        event.is_budget_enough(user.budget),
        event.event_date >= (today or date.today()),
        remaining_seats(plans, event) > 0,
    )


def create_plan(plans: list[Plan], event: Event, user: User,
                today: date | None = None) -> Plan:
    """Связать существующие объекты, не создавая активных дублей."""
    if any(not plan.is_cancelled and plan.event.id == event.id and
           plan.user.name.casefold() == user.name.casefold()
           for plan in plans):
        raise ValueError("Пользователь уже записан на это мероприятие.")
    reason = plan_recommendation(plans, event, user, today)
    if not reason.startswith("Мероприятие подходит"):
        raise ValueError(reason)
    plan = Plan(max((item.id for item in plans), default=0) + 1,
                event, user)
    plans.append(plan)
    return plan


def cancel_plan(plans: list[Plan], plan_id: int) -> Plan:
    """Изменить состояние записи без удаления из истории."""
    plan = find_plan(plans, plan_id)
    if plan is None:
        raise ValueError("Запись не найдена.")
    plan.cancel()
    return plan


def plan_statistics(events: list[Event], plans: list[Plan]) -> dict:
    """Подсчитать активные записи и сумму цен их билетов."""
    active = [plan for plan in plans if not plan.is_cancelled]
    return {
        "events": len(events),
        "plans": len(active),
        "total_price": sum(plan.event.ticket_price for plan in active),
    }
