"""Страницы планов посетителей.

ПР9: список записей, карточка и статистика получают данные через
Django ORM; в списке добавлены фильтрация, сортировка и пагинация.
ПР10: статусы Plan.Status и методы менеджера Plan.objects.
ПР11: фильтры через PlanFilterForm; создание, редактирование (ModelForm
PlanForm) и отмена записи POST-запросом.
"""

from django.contrib import messages
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
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Event
from planner.forms import PlanFilterForm, PlanForm
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


def plan_list(request):
    """Страница /plans/: фильтры по дате, мероприятию, посетителю, статусу."""
    # GET-параметры проверяет форма: DateField, ModelChoiceField, ChoiceField.
    form = PlanFilterForm(request.GET)
    form.is_valid()
    # В cleaned_data попадают только значения, прошедшие проверку;
    # ошибочные поля выводятся в шаблоне и не участвуют в фильтрации.
    data = form.cleaned_data

    plans = Plan.objects.all()
    if data.get("status"):
        plans = plans.filter(status=data["status"])
    if data.get("date"):
        # Фильтрация по полю связанной модели Event (метод менеджера).
        plans = plans.for_date(data["date"])
    if data.get("event"):
        plans = plans.filter(event=data["event"])
    if data.get("user"):
        plans = plans.filter(user=data["user"])

    sort = data.get("sort") or "date"
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
            "status",
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
            "form": form,
            "plans": page_obj,
            "page_obj": page_obj,
            "total": paginator.count,
            "only_active": data.get("status") == Plan.Status.ACTIVE,
            "sort": sort,
        },
    )


def statistics(request):
    """Страница /plans/statistics/: aggregate() и annotate()."""
    active = Q(plans__status=Plan.Status.ACTIVE)

    # Количество записей по статусам: Count() с условием Q().
    by_status = Plan.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=Plan.Status.ACTIVE)),
        cancelled=Count("id", filter=Q(status=Plan.Status.CANCELLED)),
        completed=Count("id", filter=Q(status=Plan.Status.COMPLETED)),
    )

    totals = Plan.objects.active().aggregate(
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
            "by_status": by_status,
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
        Plan.objects.with_details(),
        pk=plan_id,
    )
    return render(
        request,
        "planner/plan_detail.html",
        {"plan": plan},
    )


def plan_create(request):
    """Страница /plans/create/: GET – пустая форма, POST – сохранение."""
    if request.method == "POST":
        form = PlanForm(request.POST)
        if form.is_valid():
            # commit=False: объект создан, но ещё не сохранён в базе –
            # можно задать поля, которых нет в форме.
            plan = form.save(commit=False)
            plan.status = Plan.Status.ACTIVE
            plan.save()
            messages.success(request, f"Запись №{plan.pk} оформлена.")
            return redirect("planner:detail", plan_id=plan.pk)
    else:
        # Начальные значения из ссылки «Записаться» (?event=&user=).
        form = PlanForm(initial={
            "event": request.GET.get("event"),
            "user": request.GET.get("user"),
        })
    return render(
        request,
        "planner/plan_form.html",
        {"form": form, "title": "Новая запись на мероприятие"},
    )


def plan_update(request, plan_id):
    """Страница /plans/<id>/edit/: изменение активной записи."""
    plan = get_object_or_404(Plan.objects.active(), pk=plan_id)
    # instance=plan: форма заполняется данными записи и при save()
    # обновляет её, а не создаёт новую.
    form = PlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Запись №{plan.pk} изменена.")
        return redirect("planner:detail", plan_id=plan.pk)
    return render(
        request,
        "planner/plan_form.html",
        {"form": form, "title": f"Изменение записи №{plan.pk}",
         "plan": plan},
    )


@require_POST
def plan_cancel(request, plan_id):
    """POST /plans/<id>/cancel/: отмена записи (GET – ответ 405)."""
    plan = get_object_or_404(Plan.objects.active(), pk=plan_id)
    # Запись не удаляется: меняется статус на CANCELLED.
    plan.cancel()
    messages.success(request, f"Запись №{plan.pk} отменена.")
    return redirect("planner:list")
