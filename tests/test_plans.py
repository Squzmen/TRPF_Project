"""Проверки добавления, запретов, отмены и статистики."""

from datetime import date

import pytest

from plans import (
    cancel_plan, create_plan, plan_recommendation, plan_statistics,
    remaining_seats,
)


EVENT = {
    "id": 1, "name": "Спектакль «Гамлет»", "category": "театр",
    "event_date": "2026-10-17", "ticket_price": 1500.0,
    "age_limit": 12, "capacity": 1,
}
TODAY = date(2026, 9, 21)


def test_add_and_cancel_restores_seat():
    plans = []
    plan = create_plan(plans, EVENT, "Анна", 20, "театр", 2000, TODAY)
    assert remaining_seats(plans, EVENT) == 0
    assert cancel_plan(plans, plan["id"]) == plan
    assert remaining_seats(plans, EVENT) == 1


def test_prevent_duplicate_user():
    plans = []
    create_plan(plans, EVENT, "Анна", 20, "театр", 2000, TODAY)
    with pytest.raises(ValueError, match="уже записан"):
        create_plan(plans, EVENT, " анна ", 20, "театр", 2000, TODAY)
    assert len(plans) == 1


def test_prevent_full_event():
    plans = []
    create_plan(plans, EVENT, "Анна", 20, "театр", 2000, TODAY)
    with pytest.raises(ValueError, match="мест нет"):
        create_plan(plans, EVENT, "Борис", 20, "театр", 2000, TODAY)


@pytest.mark.parametrize("age,category,budget,message", [
    (11, "театр", 2000, "возрастное"),
    (20, "музей", 2000, "категории"),
    (20, "театр", 1000, "бюджет"),
])
def test_prevent_ineligible_visitor(age, category, budget, message):
    with pytest.raises(ValueError, match=message):
        create_plan([], EVENT, "Анна", age, category, budget, TODAY)


def test_reject_past_event():
    assert "уже прошло" in plan_recommendation(
        [], EVENT, 20, "театр", 2000, date(2026, 10, 18)
    )


def test_plan_statistics():
    plans = []
    create_plan(plans, EVENT, "Анна", 20, "театр", 2000, TODAY)
    assert plan_statistics([EVENT], plans) == {
        "events": 1, "plans": 1, "total_price": 1500.0,
    }
