"""Проверки моделей Django, связей, миграций и переноса данных (ПР9)."""

import sqlite3
from datetime import date
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.db.models import ProtectedError

from catalog.models import Event
from db.database import DB_PATH
from db.import_sqlite_to_orm import import_data
from db.inspect_source_db import inspect
from planner.models import Plan
from visitors.models import User

pytestmark = pytest.mark.django_db


def source_count(table):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_models_have_no_missing_migrations():
    """Все изменения моделей отражены в миграциях."""
    out = StringIO()
    call_command("makemigrations", "--check", "--dry-run", stdout=out)
    assert "No changes detected" in out.getvalue()


def test_inspect_source_finds_no_broken_links():
    """Исходная база ПР7 пригодна для переноса."""
    report = inspect()
    assert report["broken_links"] == 0
    assert report["events"]["count"] == 5


def test_import_keeps_counts_ids_and_links(project_data):
    """Перенос сохраняет количество, идентификаторы и внешние ключи."""
    assert project_data == {
        "events": source_count("events"),
        "users": source_count("users"),
        "plans": source_count("plans"),
    }
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, event_id, user_id, is_cancelled FROM plans").fetchall()
    for plan_id, event_id, user_id, cancelled in rows:
        plan = Plan.objects.get(pk=plan_id)
        assert (plan.event_id, plan.user_id) == (event_id, user_id)
        expected = Plan.Status.CANCELLED if cancelled else Plan.Status.ACTIVE
        assert plan.status == expected


def test_import_can_be_repeated(project_data):
    """Повторный перенос не создаёт дублей."""
    assert import_data() == project_data


def test_import_converts_types(project_data):
    """Строка даты → date, REAL → Decimal."""
    event = Event.objects.get(pk=1)
    assert event.event_date == date(2026, 10, 17)
    assert event.ticket_price == Decimal("1500.00")


def test_forward_and_reverse_relations(project_data):
    """plan.event / plan.user и обратные event.plans / user.plans."""
    plan = Plan.objects.select_related("event", "user").get(pk=1)
    assert plan.event.name == "Спектакль «Гамлет»"
    assert plan.user.name == "Анна"
    assert set(plan.event.plans.values_list("pk", flat=True)) == {1, 2}
    assert plan.user.plans.count() == 1


def test_crud_operations():
    """Создание, чтение, изменение и удаление через ORM."""
    event = Event.objects.create(
        name="Тест", category="Театр", event_date=date(2099, 1, 1),
        ticket_price=Decimal("100"), capacity=10,
    )
    assert event.category == "театр"
    event.capacity = 20
    event.save()
    assert Event.objects.get(pk=event.pk).capacity == 20
    event.delete()
    assert not Event.objects.filter(name="Тест").exists()


def test_protect_forbids_deleting_event_with_plans(project_data):
    """on_delete=PROTECT сохраняет историю записей."""
    with pytest.raises(ProtectedError):
        Event.objects.get(pk=1).delete()
    with pytest.raises(ProtectedError):
        User.objects.get(pk=1).delete()


def test_cancel_keeps_plan(project_data):
    """cancel() меняет состояние и не удаляет запись."""
    plan = Plan.objects.get(pk=1)
    plan.cancel()
    plan.refresh_from_db()
    assert plan.status == Plan.Status.CANCELLED
    assert Plan.objects.filter(pk=1).exists()


def test_manager_methods(project_data):
    """PlanQuerySet: active(), cancelled(), completed(), for_date()."""
    assert Plan.objects.count() == 6
    assert Plan.objects.active().count() == 5
    assert list(Plan.objects.cancelled().values_list("pk", flat=True)) == [5]
    assert not Plan.objects.completed().exists()
    on_date = Plan.objects.for_date(date(2026, 10, 17))
    assert set(on_date.values_list("pk", flat=True)) == {1, 2}
    # Методы возвращают QuerySet, поэтому цепочку можно продолжать.
    assert Plan.objects.active().filter(event_id=2).count() == 2
    assert Event.objects.get(pk=1).plans.active().count() == 2


def test_with_seats_annotation(project_data):
    """EventQuerySet.with_seats(): свободные места по активным записям."""
    seats = dict(Event.objects.with_seats().values_list("pk", "seats_left"))
    assert seats == {1: 0, 2: 1, 3: 1, 4: 3, 5: 5}


def test_slug_is_generated_and_unique():
    """slug транслитерируется из названия и не повторяется."""
    first = Event.objects.create(
        name="Аудитория 301", category="лекция",
        event_date=date(2099, 1, 1), ticket_price=0, capacity=5)
    second = Event.objects.create(
        name="Аудитория 301", category="лекция",
        event_date=date(2099, 1, 2), ticket_price=0, capacity=5)
    assert first.slug == "auditoriia-301"
    assert second.slug == "auditoriia-301-2"
    assert first.get_absolute_url() == "/events/auditoriia-301/"


def test_generated_field_follows_age_limit():
    """GeneratedField is_family вычисляется базой данных."""
    event = Event.objects.create(
        name="Кукольный театр", category="театр",
        event_date=date(2099, 1, 1), age_limit=0, ticket_price=300,
        capacity=10)
    event.refresh_from_db()
    assert event.is_family
    event.age_limit = 16
    event.save()
    event.refresh_from_db()
    assert not event.is_family


def test_get_raises_for_missing_and_multiple(project_data):
    """get() требует ровно одну запись."""
    with pytest.raises(Event.DoesNotExist):
        Event.objects.get(pk=999)
    with pytest.raises(Event.MultipleObjectsReturned):
        Event.objects.get(category="концерт")


def test_domain_methods(project_data):
    """Правила ПР1 перенесены в методы моделей."""
    event = Event.objects.get(pk=4)
    user = User.objects.get(pk=3)
    assert not event.is_age_allowed(user.age)
    assert not event.is_budget_enough(user.budget)
    assert User.objects.get(pk=2).is_interested_in(event)
