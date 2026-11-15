"""Страницы каталога мероприятий.

ПР9: данные получаются средствами Django ORM (модели Event, User, Plan)
вместо SQL-запросов через sqlite3 из ПР7.
ПР10: менеджеры Event.objects.with_seats() и Plan.objects.active(),
карточка мероприятия открывается по slug.
"""

import math
from datetime import date
from decimal import Decimal

from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

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


def event_list(request):
    """Страница /events/: фильтр по категории, поиск и сортировка."""
    category = request.GET.get("category", "").strip()
    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "date")
    if sort not in EVENT_SORT_FIELDS:
        sort = "date"

    events = Event.objects.with_seats()
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
            events = Event.objects.with_seats().filter(
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
            booked = Plan.objects.active().filter(
                user=selected,
            ).values_list("event_id", flat=True)
            events = (
                Event.objects.with_seats()
                .filter(
                    category__iexact=selected.preferred_category,
                    age_limit__lte=selected.age,
                    ticket_price__lte=selected.budget,
                    seats_left__gt=0,
                )
                .upcoming(date.today())
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


def event_redirect(request, event_id):
    """Старый адрес /events/<id>/ перенаправляет на адрес по slug."""
    event = get_object_or_404(Event, pk=event_id)
    return redirect(event, permanent=True)


def event_detail(request, slug):
    """Страница /events/<slug>/; если мероприятия нет – ответ 404."""
    event = get_object_or_404(Event.objects.with_seats(), slug=slug)
    # Обратная связь related_name="plans": активные записи мероприятия.
    plans = event.plans.active().select_related("user")

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
