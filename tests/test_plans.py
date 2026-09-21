"""Взаимодействие пользователей, мероприятий и записей."""

from datetime import date

import pytest

from models import Plan, User
from plans import (
    cancel_plan, create_plan, plan_recommendation, plan_statistics,
    remaining_seats,
)


TODAY = date(2026, 9, 21)


def test_user_creation_and_classmethod(event, user):
    assert "Анна" in str(user)
    assert user.is_interested_in(event)
    assert User.from_data(user.to_data()).to_data() == user.to_data()
    with pytest.raises(ValueError):
        User(2, "", 20, "театр", 2000)


def test_plan_links_real_objects(event, user):
    plan = create_plan([], event, user, TODAY)
    assert plan.event is event
    assert plan.user is user
    assert "активна" in str(plan)
    assert plan.to_data() == {
        "id": 1, "event_id": 1, "user_id": 1, "is_cancelled": False,
    }


def test_cancel_preserves_history_and_restores_seat(event, user):
    plans = []
    plan = create_plan(plans, event, user, TODAY)
    assert remaining_seats(plans, event) == 0
    assert cancel_plan(plans, plan.id) is plan
    assert plans == [plan] and plan.is_cancelled
    assert "отменена" in str(plan)
    assert remaining_seats(plans, event) == 1
    with pytest.raises(ValueError, match="уже отменена"):
        cancel_plan(plans, plan.id)


def test_renew_after_cancellation_keeps_unique_ids(event, user):
    plans = []
    first = create_plan(plans, event, user, TODAY)
    first.cancel()
    second = create_plan(plans, event, user, TODAY)
    assert second.id != first.id
    assert len(plans) == 2


def test_no_duplicate_active_user(event, user):
    plans = [Plan(1, event, user)]
    with pytest.raises(ValueError, match="уже записан"):
        create_plan(plans, event, user, TODAY)


def test_full_event_is_unavailable(event, user):
    other = User(2, "Борис", 30, "театр", 2000)
    plans = [Plan(1, event, user)]
    with pytest.raises(ValueError, match="мест нет"):
        create_plan(plans, event, other, TODAY)


@pytest.mark.parametrize("age,category,budget,message", [
    (11, "театр", 2000, "возрастное"),
    (20, "музей", 2000, "категории"),
    (20, "театр", 1000, "бюджет"),
])
def test_ineligible_visitor(event, age, category, budget, message):
    visitor = User(2, "Борис", age, category, budget)
    with pytest.raises(ValueError, match=message):
        create_plan([], event, visitor, TODAY)


def test_past_event(event, user):
    assert "уже прошло" in plan_recommendation(
        [], event, user, date(2099, 10, 18)
    )


def test_statistics_include_only_active(event, user):
    plans = [Plan(1, event, user), Plan(2, event, user, True)]
    assert plan_statistics([event], plans) == {
        "events": 1, "plans": 1, "total_price": 1500.0,
    }
