"""Страницы каталога мероприятий.

Списки и поиск получают данные из базы SQLite параметризованными
SQL-запросами (sql/queries.sql), карточка мероприятия по-прежнему
использует объекты ПР3 и JSON.
"""

import math
import sqlite3
from datetime import date

from django.shortcuts import render

from db.database import get_connection, rows_with_dates
from events import find_event, get_event_date_status
from plans import remaining_seats
from storage import load_data

# Запрос 1 из sql/queries.sql: список мероприятий со свободными местами.
QUERY_EVENTS = """
    SELECT
        e.id,
        e.name,
        e.category,
        e.event_date,
        e.age_limit,
        e.ticket_price,
        e.capacity,
        e.capacity - (
            SELECT COUNT(*)
            FROM plans AS p
            WHERE p.event_id = e.id
              AND p.is_cancelled = 0
        ) AS seats_left
    FROM events AS e
    ORDER BY e.event_date, e.name
"""

# Запрос 2: категории для выпадающего списка.
QUERY_CATEGORIES = """
    SELECT DISTINCT
        category
    FROM events
    ORDER BY category
"""

# Запрос 3: посетители для выпадающего списка.
QUERY_USERS = """
    SELECT
        id,
        name,
        age,
        preferred_category,
        budget
    FROM users
    ORDER BY name
"""

# Запрос 4: мероприятия выбранной категории.
QUERY_EVENTS_BY_CATEGORY = """
    SELECT
        e.id,
        e.name,
        e.category,
        e.event_date,
        e.age_limit,
        e.ticket_price,
        e.capacity,
        e.capacity - (
            SELECT COUNT(*)
            FROM plans AS p
            WHERE p.event_id = e.id
              AND p.is_cancelled = 0
        ) AS seats_left
    FROM events AS e
    WHERE e.category = ?
    ORDER BY e.event_date, e.name
"""

# Запрос 5: поиск по периоду дат и предельной цене билета.
QUERY_EVENTS_SEARCH = """
    SELECT
        e.id,
        e.name,
        e.category,
        e.event_date,
        e.age_limit,
        e.ticket_price,
        e.capacity,
        e.capacity - (
            SELECT COUNT(*)
            FROM plans AS p
            WHERE p.event_id = e.id
              AND p.is_cancelled = 0
        ) AS seats_left
    FROM events AS e
    WHERE e.event_date BETWEEN ? AND ?
      AND e.ticket_price <= ?
    ORDER BY e.event_date, e.name
"""

# Запрос 6: подбор мероприятий для посетителя.
QUERY_EVENTS_FOR_USER = """
    SELECT
        e.id,
        e.name,
        e.category,
        e.event_date,
        e.age_limit,
        e.ticket_price,
        e.capacity,
        e.capacity - (
            SELECT COUNT(*)
            FROM plans AS p
            WHERE p.event_id = e.id
              AND p.is_cancelled = 0
        ) AS seats_left
    FROM events AS e
    JOIN users AS u
        ON u.id = ?
    WHERE e.category = u.preferred_category
      AND e.age_limit <= u.age
      AND e.ticket_price <= u.budget
      AND e.event_date >= ?
      AND e.capacity > (
            SELECT COUNT(*)
            FROM plans AS p
            WHERE p.event_id = e.id
              AND p.is_cancelled = 0
      )
      AND e.id NOT IN (
            SELECT p.event_id
            FROM plans AS p
            WHERE p.user_id = u.id
              AND p.is_cancelled = 0
      )
    ORDER BY e.event_date, e.name
"""

MAX_PRICE = 1_000_000.0


def event_list(request):
    """Страница /events/: список из SQLite, фильтр по категории."""
    category = request.GET.get("category", "").strip()

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        categories = conn.execute(QUERY_CATEGORIES).fetchall()
        if category:
            rows = conn.execute(
                QUERY_EVENTS_BY_CATEGORY,
                [category],
            ).fetchall()
        else:
            rows = conn.execute(QUERY_EVENTS).fetchall()
    finally:
        conn.close()

    return render(
        request,
        "catalog/event_list.html",
        {
            "events": rows_with_dates(rows, "event_date"),
            "categories": categories,
            "category": category,
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
    """Страница /events/search/: поиск по датам и цене билета."""
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
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    QUERY_EVENTS_SEARCH,
                    [date_from.isoformat(), date_to.isoformat(), max_price],
                ).fetchall()
            finally:
                conn.close()
            events = rows_with_dates(rows, "event_date")

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

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        users = conn.execute(QUERY_USERS).fetchall()
        selected = None
        events = []
        error = None
        if raw_user:
            selected = next(
                (user for user in users if str(user["id"]) == raw_user),
                None,
            )
            if selected is None:
                error = "Посетитель с таким номером не найден."
            else:
                rows = conn.execute(
                    QUERY_EVENTS_FOR_USER,
                    [selected["id"], date.today().isoformat()],
                ).fetchall()
                events = rows_with_dates(rows, "event_date")
    finally:
        conn.close()

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
