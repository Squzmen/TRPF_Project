"""Проверки административной панели Django (ПР10)."""

import pytest
from django.contrib import admin
from django.urls import reverse

from catalog.models import Event
from planner.models import Plan
from visitors.models import User

pytestmark = pytest.mark.usefixtures("project_data")


@pytest.mark.parametrize("model", [Event, User, Plan])
def test_models_registered(model):
    """Модели проекта зарегистрированы в admin.site."""
    assert admin.site.is_registered(model)


@pytest.mark.parametrize("name", [
    "admin:catalog_event_changelist",
    "admin:visitors_user_changelist",
    "admin:planner_plan_changelist",
])
def test_changelists_open(admin_client, name):
    """Списки моделей открываются у суперпользователя."""
    assert admin_client.get(reverse(name)).status_code == 200


def test_admin_requires_login(client):
    """Без входа админ-панель перенаправляет на страницу авторизации."""
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


def test_plan_search_by_related_field(admin_client):
    """search_fields = event__name, user__name (поиск без учёта регистра)."""
    url = reverse("admin:planner_plan_changelist")
    response = admin_client.get(url, {"q": "анна"})
    assert response.context["cl"].result_count == 1


def test_plan_filter_by_status(admin_client):
    """list_filter по статусу."""
    url = reverse("admin:planner_plan_changelist")
    response = admin_client.get(url, {"status__exact": "cancelled"})
    assert response.context["cl"].result_count == 1


def test_event_list_shows_annotated_column(admin_client):
    """Столбец «Активных записей» считается annotate() в get_queryset()."""
    response = admin_client.get(reverse("admin:catalog_event_changelist"))
    assert "Активных записей" in response.content.decode()
    counts = {obj.pk: obj.active_plans_count
              for obj in response.context["cl"].result_list}
    assert counts[1] == 2 and counts[5] == 0


def test_event_change_page_has_plan_inline(admin_client):
    """Карточка мероприятия показывает связанные записи (inline)."""
    url = reverse("admin:catalog_event_change", args=[1])
    html = admin_client.get(url).content.decode()
    assert "plans-TOTAL_FORMS" in html
    assert "Анна" in html


def test_cancel_action_changes_status(admin_client):
    """Массовое действие меняет статус, записи сохраняются."""
    url = reverse("admin:planner_plan_changelist")
    admin_client.post(url, {"action": "cancel_plans",
                            "_selected_action": [1, 2]})
    assert Plan.objects.cancelled().count() == 3
    assert Plan.objects.count() == 6
