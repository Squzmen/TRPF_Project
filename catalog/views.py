"""Страницы каталога мероприятий (данные берутся из объектов ПР3)."""

from datetime import date

from django.http import HttpResponse
from django.utils.html import escape

from events import find_event, get_event_date_status
from homepage.views import page
from plans import remaining_seats
from storage import load_data


def event_list(request):
    """Страница /events/: список мероприятий из data/events.json."""
    events_list, _users, plans_list = load_data()
    items = ""
    for event in events_list:
        text = (
            f"{event.name} – {event.category}, "
            f"{event.event_date:%d.%m.%Y}, {event.ticket_price:.2f} руб."
        )
        items += (
            '<li class="list-group-item">'
            f'<a href="/events/{event.id}/">{escape(text)}</a>'
            "</li>"
        )
    content = f"""
    <h1>Мероприятия</h1>
    <ul class="list-group">{items}</ul>
    """
    return HttpResponse(page("Мероприятия", content))


def event_detail(request, event_id):
    """Страница /events/<id>/; если мероприятия нет – код статуса 404."""
    events_list, _users, plans_list = load_data()
    event = find_event(events_list, event_id)

    if event is None:
        content = """
        <h1 class="text-danger">Мероприятие не найдено</h1>
        <a href="/events/" class="btn btn-outline-secondary">
            ← к списку мероприятий
        </a>
        """
        return HttpResponse(
            page("Мероприятие не найдено", content),
            status=404,
        )

    seats = remaining_seats(plans_list, event)
    date_status = get_event_date_status(event.event_date, date.today())
    badge = "bg-success" if seats > 0 else "bg-danger"
    seats_text = f"свободно мест: {seats}" if seats > 0 else "мест нет"

    content = f"""
    <div class="card">
        <div class="card-body">
            <h5 class="card-title">{escape(event.name)}</h5>
            <p class="card-text">
                <strong>ID:</strong> {event.id}
            </p>
            <p class="card-text">
                <strong>Категория:</strong> {escape(event.category)}
            </p>
            <p class="card-text">
                <strong>Дата:</strong> {event.event_date:%d.%m.%Y}
                ({escape(date_status)})
            </p>
            <p class="card-text">
                <strong>Возраст:</strong> от {event.age_limit} лет
            </p>
            <p class="card-text">
                <strong>Билет:</strong> {event.ticket_price:.2f} руб.
            </p>
            <p class="card-text">
                Наличие мест:
                <span class="badge {badge}">{seats_text}</span>
            </p>
            <a href="/events/" class="btn btn-outline-secondary">
                ← к списку мероприятий
            </a>
        </div>
    </div>
    """
    return HttpResponse(page(event.name, content), status=200)
