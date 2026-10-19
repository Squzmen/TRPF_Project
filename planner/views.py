"""Страницы планов посетителей (записи на мероприятия из объектов ПР3)."""

from django.http import HttpResponse
from django.utils.html import escape

from homepage.views import page
from plans import find_plan
from storage import load_data


def plan_list(request):
    """Страница /plans/: записи посетителей из data/plans.json."""
    _events, _users, plans_list = load_data()
    items = ""
    for plan in plans_list:
        status = "отменена" if plan.is_cancelled else "активна"
        badge = "bg-secondary" if plan.is_cancelled else "bg-success"
        text = (
            f"{plan.user.name} – {plan.event.name}, "
            f"{plan.event.event_date:%d.%m.%Y}"
        )
        items += f"""
        <li class="list-group-item d-flex justify-content-between">
            <a href="/plans/{plan.id}/">{escape(text)}</a>
            <span class="badge {badge}">{status}</span>
        </li>
        """
    content = f"""
    <h1>Планы посетителей</h1>
    <ul class="list-group">{items}</ul>
    """
    return HttpResponse(page("Планы посетителей", content))


def plan_detail(request, plan_id):
    """Страница /plans/<id>/; если записи нет – код статуса 404."""
    _events, _users, plans_list = load_data()
    plan = find_plan(plans_list, plan_id)

    if plan is None:
        content = """
        <h1 class="text-danger">Запись не найдена</h1>
        <a href="/plans/" class="btn btn-outline-secondary">
            ← к списку планов
        </a>
        """
        return HttpResponse(
            page("Запись не найдена", content),
            status=404,
        )

    status = "отменена" if plan.is_cancelled else "активна"
    badge = "bg-secondary" if plan.is_cancelled else "bg-success"
    content = f"""
    <div class="card">
        <div class="card-body">
            <h5 class="card-title">Запись №{plan.id}</h5>
            <p class="card-text">
                Мероприятие: {escape(plan.event.name)}
            </p>
            <p class="card-text">
                Дата: {plan.event.event_date:%d.%m.%Y}
            </p>
            <p class="card-text">
                Посетитель: {escape(plan.user.name)}
            </p>
            <p class="card-text">
                Статус: <span class="badge {badge}">{status}</span>
            </p>
            <a href="/plans/" class="btn btn-outline-secondary">
                ← к списку планов
            </a>
        </div>
    </div>
    """
    return HttpResponse(page(f"Запись №{plan.id}", content), status=200)
