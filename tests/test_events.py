"""Проверки каталога мероприятий и логики, перенесенной из ПР1."""

from datetime import date

from events import (
    filter_events, get_event_date_status, get_recommendation,
    search_events, sort_events,
)


def test_search_events_by_name():
    events = [{"name": "Спектакль Гамлет"}, {"name": "Выставка"}]
    assert search_events(events, "ГАШ") == []
    assert search_events(events, "гАмЛеТ") == [events[0]]


def test_filter_events_by_category():
    events = [{"category": "театр"}, {"category": "музей"}]
    assert filter_events(events, " Театр ") == [events[0]]


def test_sort_events_does_not_change_catalog():
    events = [{"id": 1, "ticket_price": 1500},
              {"id": 2, "ticket_price": 500}]
    assert sort_events(events) == [events[1], events[0]]
    assert events[0]["id"] == 1


def test_pr1_recommendation_and_date_status():
    assert "подходит" in get_recommendation(True, True, True, True, True)
    assert "возрастное" in get_recommendation(False, True, True, True, True)
    assert get_event_date_status(date(2026, 10, 17),
                                 date(2026, 10, 17)) == (
        "Мероприятие проходит сегодня"
    )
