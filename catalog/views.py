"""Страницы каталога мероприятий: view готовит контекст, HTML — шаблон."""

from datetime import date

from django.shortcuts import render

from events import find_event, get_event_date_status
from plans import remaining_seats
from storage import load_data


def event_list(request):
    """Страница /events/: мероприятия и число свободных мест."""
    events_list, _users, plans_list = load_data()

    items = [
        {"event": event, "seats_left": remaining_seats(plans_list, event)}
        for event in events_list
    ]

    return render(
        request,
        "catalog/event_list.html",
        {"items": items},
    )


def event_detail(request, event_id):
    """Страница /events/<id>/; если мероприятия нет – статус 404."""
    events_list, _users, plans_list = load_data()
    event = find_event(events_list, event_id)

    context = {
        "event": event,
        "seats_left": None,
        "date_status": None,
    }
    if event is not None:
        context["seats_left"] = remaining_seats(plans_list, event)
        context["date_status"] = get_event_date_status(
            event.event_date,
            date.today(),
        )

    return render(
        request,
        "catalog/event_detail.html",
        context,
        status=404 if event is None else 200,
    )
