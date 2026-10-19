"""Страницы планов посетителей: view готовит контекст, HTML — шаблон."""

from django.shortcuts import render

from plans import find_plan
from storage import load_data


def plan_list(request):
    """Страница /plans/: записи посетителей с их статусами."""
    _events, _users, plans_list = load_data()

    return render(
        request,
        "planner/plan_list.html",
        {"plans": plans_list},
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
