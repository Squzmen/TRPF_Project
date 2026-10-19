"""Страницы планов посетителей.

Список записей и статистика получают данные из базы SQLite
SQL-запросами (sql/queries.sql), карточка записи использует объекты ПР3.
"""

import sqlite3

from django.shortcuts import render

from db.database import get_connection, rows_with_dates
from plans import find_plan
from storage import load_data

# Запрос 7: все записи с мероприятием и посетителем.
QUERY_PLANS = """
    SELECT
        p.id,
        p.is_cancelled,
        e.id AS event_id,
        e.name AS event_name,
        e.category,
        e.event_date,
        e.ticket_price,
        u.id AS user_id,
        u.name AS user_name
    FROM plans AS p
    JOIN events AS e
        ON p.event_id = e.id
    JOIN users AS u
        ON p.user_id = u.id
    ORDER BY e.event_date, p.id
"""

# Запрос 8: только активные записи.
QUERY_ACTIVE_PLANS = """
    SELECT
        p.id,
        p.is_cancelled,
        e.id AS event_id,
        e.name AS event_name,
        e.category,
        e.event_date,
        e.ticket_price,
        u.id AS user_id,
        u.name AS user_name
    FROM plans AS p
    JOIN events AS e
        ON p.event_id = e.id
    JOIN users AS u
        ON p.user_id = u.id
    WHERE p.is_cancelled = 0
    ORDER BY e.event_date, p.id
"""

# Запрос 9: общие показатели активных записей.
QUERY_TOTALS = """
    SELECT
        COUNT(p.id) AS active_plans,
        COALESCE(SUM(e.ticket_price), 0) AS total_price,
        COALESCE(AVG(e.ticket_price), 0) AS avg_price,
        COALESCE(MIN(e.ticket_price), 0) AS min_price,
        COALESCE(MAX(e.ticket_price), 0) AS max_price
    FROM plans AS p
    JOIN events AS e
        ON p.event_id = e.id
    WHERE p.is_cancelled = 0
"""

# Запрос 10: записи по каждому мероприятию.
QUERY_BY_EVENT = """
    SELECT
        e.id,
        e.name AS event_name,
        e.category,
        e.capacity,
        COUNT(p.id) AS active_plans,
        e.capacity - COUNT(p.id) AS seats_left,
        COUNT(p.id) * e.ticket_price AS revenue
    FROM events AS e
    LEFT JOIN plans AS p
        ON p.event_id = e.id
       AND p.is_cancelled = 0
    GROUP BY e.id, e.name, e.category, e.capacity, e.ticket_price
    ORDER BY active_plans DESC, e.name
"""

# Запрос 11: сводка по категориям.
QUERY_BY_CATEGORY = """
    SELECT
        category,
        COUNT(*) AS events_count,
        MIN(ticket_price) AS min_price,
        ROUND(AVG(ticket_price), 2) AS avg_price,
        MAX(ticket_price) AS max_price,
        SUM(capacity) AS total_seats
    FROM events
    GROUP BY category
    ORDER BY events_count DESC, category
"""

# Запрос 12: мероприятия с минимум двумя активными записями.
QUERY_POPULAR = """
    SELECT
        e.name AS event_name,
        COUNT(p.id) AS active_plans
    FROM events AS e
    JOIN plans AS p
        ON p.event_id = e.id
    WHERE p.is_cancelled = 0
    GROUP BY e.id, e.name
    HAVING COUNT(p.id) >= ?
    ORDER BY active_plans DESC, e.name
"""

# Запрос 13: активность посетителей.
QUERY_BY_USER = """
    SELECT
        u.id,
        u.name AS user_name,
        u.budget,
        COUNT(p.id) AS active_plans,
        COALESCE(SUM(e.ticket_price), 0) AS spent
    FROM users AS u
    LEFT JOIN plans AS p
        ON p.user_id = u.id
       AND p.is_cancelled = 0
    LEFT JOIN events AS e
        ON p.event_id = e.id
    GROUP BY u.id, u.name, u.budget
    ORDER BY spent DESC, u.name
"""

POPULAR_MIN_PLANS = 2


def plan_list(request):
    """Страница /plans/: записи из SQLite; ?status=active – только активные."""
    only_active = request.GET.get("status") == "active"

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        query = QUERY_ACTIVE_PLANS if only_active else QUERY_PLANS
        rows = conn.execute(query).fetchall()
    finally:
        conn.close()

    return render(
        request,
        "planner/plan_list.html",
        {
            "plans": rows_with_dates(rows, "event_date"),
            "only_active": only_active,
        },
    )


def statistics(request):
    """Страница /plans/statistics/: агрегатные запросы и группировки."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        totals = conn.execute(QUERY_TOTALS).fetchone()
        by_event = conn.execute(QUERY_BY_EVENT).fetchall()
        by_category = conn.execute(QUERY_BY_CATEGORY).fetchall()
        popular = conn.execute(
            QUERY_POPULAR,
            [POPULAR_MIN_PLANS],
        ).fetchall()
        by_user = conn.execute(QUERY_BY_USER).fetchall()
    finally:
        conn.close()

    return render(
        request,
        "planner/statistics.html",
        {
            "totals": totals,
            "by_event": by_event,
            "by_category": by_category,
            "popular": popular,
            "popular_min": POPULAR_MIN_PLANS,
            "by_user": by_user,
        },
    )


def plan_detail(request, plan_id):
    """Страница /plans/<id>/; если записи нет – статус 404."""
    _events, _users, plans_list = load_data()
    plan = find_plan(plans_list, plan_id)

    return render(
        request,
        "planner/plan_detail.html",
        {"plan": plan},
        status=404 if plan is None else 200,
    )
