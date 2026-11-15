"""Страницы каталога мероприятий.

ПР9: данные получаются средствами Django ORM (модели Event, User, Plan)
вместо SQL-запросов через sqlite3 из ПР7.
"""

import math
from datetime import date
from decimal import Decimal

from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, render

from catalog.models import Event
from events import get_event_date_status
from planner.models import Plan
from visitors.models import User

MAX_PRICE = 1_000_000.0

# Разрешённые значения параметра sort и соответствующие поля order_by().
EVENT_SORT_FIELDS = {
    "date": ("event_date", "name"),
    "price": ("ticket_price", "name"),
    "-price": ("-ticket_price", "name"),
    "name": ("name",),
}


def events_with_seats():
    """Мероприятия с числом активных записей и свободных мест."""
    return Event.objects.annotate(
        active_plans=Count("plans", filter=Q(plans__is_cancelled=False)),
    ).annotate(
        seats_left=F("capacity") - F("active_plans"),
    )


def event_list(request):
    """Страница /events/: фильтр по категории, поиск и сортировка."""
    category = request.GET.get("category", "").strip()
    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "date")
    if sort not in EVENT_SORT_FIELDS:
        sort = "date"

    events = events_with_seats()
    if category:
        events = events.filter(category__iexact=category)
    if query:
        # Поиск по нескольким полям: название или категория.
        events = events.filter(
            Q(name__icontains=query) | Q(category__icontains=query)
        )
    events = events.order_by(*EVENT_SORT_FIELDS[sort])

    categories = (
        Event.objects
        .order_by("category")
        .values_list("category", flat=True)
        .distinct()
    )

    return render(
        request,
        "catalog/event_list.html",
        {
            "events": events,
            "categories": categories,
            "category": category,
            "query": query,
            "sort": sort,
        },
    )


def parse_date(value, default, label, errors):
    """Разобрать дату ГГГГ-ММ-ДД; при ошибке добавить сообщение."""
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label}: введите дату в формате ГГГГ-ММ-ДД.")
        return default


def parse_price(value, errors):
    """Разобрать предельную цену билета; при ошибке добавить сообщение."""
    if not value:
        return MAX_PRICE
    try:
        price = float(value.replace(",", "."))
    except ValueError:
        price = -1.0
    if not math.isfinite(price) or price < 0:
        errors.append("Цена: введите неотрицательное число.")
        return MAX_PRICE
    return price


def event_search(request):
    """Страница /events/search/: поиск по периоду дат и цене билета."""
    raw_from = request.GET.get("date_from", "").strip()
    raw_to = request.GET.get("date_to", "").strip()
    raw_price = request.GET.get("max_price", "").strip()
    submitted = bool(request.GET)

    errors = []
    events = []
    if submitted:
        date_from = parse_date(raw_from, date.today(), "Дата «с»", errors)
        date_to = parse_date(raw_to, date.max, "Дата «по»", errors)
        max_price = parse_price(raw_price, errors)
        if not errors:
            # Несколько условий в одном filter() объединяются через AND.
            events = events_with_seats().filter(
                event_date__range=(date_from, date_to),
                ticket_price__lte=Decimal(str(max_price)),
            ).order_by("event_date", "name")

    return render(
        request,
        "catalog/event_search.html",
        {
            "events": events,
            "errors": errors,
            "submitted": submitted,
            "date_from": raw_from,
            "date_to": raw_to,
            "max_price": raw_price,
        },
    )


def event_recommend(request):
    """Страница /events/recommend/: подбор мероприятий для посетителя."""
    raw_user = request.GET.get("user", "").strip()

    users = User.objects.order_by("name")
    selected = None
    events = []
    error = None
    if raw_user:
        if raw_user.isdigit():
            selected = User.objects.filter(pk=int(raw_user)).first()
        if selected is None:
            error = "Посетитель с таким номером не найден."
        else:
            # Мероприятия, на которые посетитель уже записан (активно).
            booked = Plan.objects.filter(
                user=selected,
                is_cancelled=False,
            ).values_list("event_id", flat=True)
            events = (
                events_with_seats()
                .filter(
                    category__iexact=selected.preferred_category,
                    age_limit__lte=selected.age,
                    ticket_price__lte=selected.budget,
                    event_date__gte=date.today(),
                    seats_left__gt=0,
                )
                .exclude(pk__in=booked)
                .order_by("event_date", "name")
            )

    return render(
        request,
        "catalog/event_recommend.html",
        {
            "users": users,
            "selected": selected,
            "events": events,
            "error": error,
            "raw_user": raw_user,
        },
    )


def event_detail(request, event_id):
    """Страница /events/<id>/; если мероприятия нет – ответ 404."""
    event = get_object_or_404(events_with_seats(), pk=event_id)
    # Обратная связь related_name="plans": записи этого мероприятия.
    plans = event.plans.filter(is_cancelled=False).select_related("user")

    return render(
        request,
        "catalog/event_detail.html",
        {
            "event": event,
            "seats_left": event.seats_left,
            "date_status": get_event_date_status(
                event.event_date,
                date.today(),
            ),
            "plans": plans,
        },
    )
