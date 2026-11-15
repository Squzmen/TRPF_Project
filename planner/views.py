"""Страницы планов посетителей.

ПР9: список записей, карточка и статистика получают данные через
Django ORM; в списке добавлены фильтрация, сортировка и пагинация.
"""

from datetime import date

from django.core.paginator import Paginator
from django.db.models import (
    Avg,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Max,
    Min,
    Q,
    Sum,
)
from django.shortcuts import get_object_or_404, render

from catalog.models import Event
from planner.models import Plan
from visitors.models import User

PLANS_PER_PAGE = 5
POPULAR_MIN_PLANS = 2

# Разрешённые значения параметра sort и поля сортировки.
PLAN_SORT_FIELDS = {
    "date": "event__event_date",
    "event": "event__name",
    "user": "user__name",
}

# Значение параметра status → значение поля is_cancelled.
STATUS_FILTERS = {
    "active": False,
    "cancelled": True,
}


def plan_list(request):
    """Страница /plans/: фильтры по дате, мероприятию, посетителю, статусу."""
    raw_date = request.GET.get("date", "").strip()
    raw_event = request.GET.get("event", "").strip()
    raw_user = request.GET.get("user", "").strip()
    status = request.GET.get("status", "").strip()
    sort = request.GET.get("sort", "date")
    error = None

    plans = Plan.objects.all()
    if status in STATUS_FILTERS:
        plans = plans.filter(is_cancelled=STATUS_FILTERS[status])
    else:
        status = ""
    if raw_date:
        try:
            selected_date = date.fromisoformat(raw_date)
        except ValueError:
            error = "Укажите дату в формате ГГГГ-ММ-ДД."
        else:
            # Фильтрация по полю связанной модели Event.
            plans = plans.filter(event__event_date=selected_date)
    if raw_event.isdigit():
        plans = plans.filter(event_id=int(raw_event))
    if raw_user.isdigit():
        plans = plans.filter(user_id=int(raw_user))

    if sort not in PLAN_SORT_FIELDS:
        sort = "date"
    plans = (
        plans
        .annotate(
            event_name=F("event__name"),
            event_date=F("event__event_date"),
            category=F("event__category"),
            user_name=F("user__name"),
        )
        .order_by(PLAN_SORT_FIELDS[sort], "id")
        .values(
            "id",
            "is_cancelled",
            "event_id",
            "event_name",
            "event_date",
            "category",
            "user_id",
            "user_name",
        )
    )

    paginator = Paginator(plans, PLANS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "planner/plan_list.html",
        {
            "plans": page_obj,
            "page_obj": page_obj,
            "total": paginator.count,
            "only_active": status == "active",
            "status": status,
            "sort": sort,
            "date": raw_date,
            "selected_event": raw_event,
            "selected_user": raw_user,
            "events": Event.objects.order_by("event_date", "name"),
            "users": User.objects.order_by("name"),
            "error": error,
        },
    )


def statistics(request):
    """Страница /plans/statistics/: aggregate() и annotate()."""
    active = Q(plans__is_cancelled=False)

    totals = Plan.objects.filter(is_cancelled=False).aggregate(
        active_plans=Count("id"),
        total_price=Sum("event__ticket_price", default=0),
        avg_price=Avg("event__ticket_price", default=0),
        min_price=Min("event__ticket_price", default=0),
        max_price=Max("event__ticket_price", default=0),
    )

    # Запрос строится от Event, поэтому мероприятия без записей
    # остаются в результате со значением 0 (аналог LEFT JOIN).
    by_event = (
        Event.objects
        .annotate(active_plans=Count("plans", filter=active))
        .annotate(
            event_name=F("name"),
            seats_left=F("capacity") - F("active_plans"),
            revenue=ExpressionWrapper(
                F("active_plans") * F("ticket_price"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )
        .values(
            "id",
            "event_name",
            "category",
            "capacity",
            "active_plans",
            "seats_left",
            "revenue",
        )
        .order_by("-active_plans", "name")
    )

    # Группировка по категории: values() + annotate().
    by_category = (
        Event.objects
        .values("category")
        .annotate(
            events_count=Count("id"),
            min_price=Min("ticket_price"),
            avg_price=Avg("ticket_price"),
            max_price=Max("ticket_price"),
            total_seats=Sum("capacity"),
        )
        .order_by("-events_count", "category")
    )

    # Условие на агрегат (аналог HAVING).
    popular = (
        Event.objects
        .annotate(active_plans=Count("plans", filter=active))
        .filter(active_plans__gte=POPULAR_MIN_PLANS)
        .annotate(event_name=F("name"))
        .values("event_name", "active_plans")
        .order_by("-active_plans", "name")
    )

    by_user = (
        User.objects
        .annotate(
            user_name=F("name"),
            active_plans=Count("plans", filter=active),
            spent=Sum(
                "plans__event__ticket_price",
                filter=active,
                default=0,
            ),
        )
        .values("id", "user_name", "budget", "active_plans", "spent")
        .order_by("-spent", "name")
    )

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
    """Страница /plans/<id>/; если записи нет – ответ 404."""
    plan = get_object_or_404(
        Plan.objects.select_related("event", "user"),
        pk=plan_id,
    )
    return render(
        request,
        "planner/plan_detail.html",
        {"plan": plan},
    )
