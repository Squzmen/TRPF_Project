"""Объекты каталога и проверки, унаследованные от ПР1/ПР2."""

from datetime import date

import pytest

from events import (
    filter_events, get_event_date_status, get_recommendation,
    search_events, sort_events,
)
from models import Event


def test_event_attributes_and_str(event):
    assert event.name == "Спектакль «Гамлет»"
    assert event.capacity == 1
    assert event.is_age_allowed(12)
    assert not event.is_age_allowed(11)
    assert event.is_budget_enough(1500)
    assert "1500.00" in str(event)
    assert event.to_data()["event_date"] == "2099-10-17"


def test_event_from_data_and_capacity(event):
    restored = Event.from_data(event.to_data())
    assert restored.to_data() == event.to_data()
    assert Event.valid_capacity(0)
    assert not Event.valid_capacity(-1)
    with pytest.raises(ValueError):
        Event(2, "Ошибка", "театр", date(2099, 10, 17), 12, 100, -1)


def test_search_and_filter_events(event):
    other = Event(2, "Выставка", "музей", date(2099, 10, 17), 6, 500, 5)
    assert search_events([event, other], "гАмЛеТ") == [event]
    assert filter_events([event, other], " Театр ") == [event]


def test_sort_events_keeps_original_order(event):
    other = Event(2, "Выставка", "музей", date(2099, 10, 17), 6, 500, 5)
    events = [event, other]
    assert sort_events(events) == [other, event]
    assert events == [event, other]


def test_pr1_recommendation_and_date():
    assert "подходит" in get_recommendation(True, True, True, True, True)
    assert "возрастное" in get_recommendation(False, True, True, True, True)
    assert get_event_date_status(date(2026, 10, 17),
                                 date(2026, 10, 17)) == (
        "Мероприятие проходит сегодня"
    )
