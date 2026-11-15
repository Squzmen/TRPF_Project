"""Проверки форм Django (ПР11): фильтрация, создание, изменение, отмена."""

import shutil
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from catalog.forms import EventForm, EventSearchForm
from catalog.models import Event
from planner.forms import PlanFilterForm, PlanForm
from planner.models import Plan
from visitors.models import User

pytestmark = pytest.mark.usefixtures("project_data")

FUTURE = date(2099, 6, 1)


@pytest.fixture
def concert():
    """Предстоящий концерт на два места."""
    return Event.objects.create(
        name="Вечер романсов", category="концерт", event_date=FUTURE,
        age_limit=12, ticket_price=Decimal("1000"), capacity=2,
    )


@pytest.fixture
def boris():
    """Борис: 34 года, любит концерты, бюджет 3000."""
    return User.objects.get(pk=2)


@pytest.fixture
def egor():
    """Егор: 25 лет, любит концерты, бюджет 2500."""
    return User.objects.get(pk=6)


def plan_data(event, user, comment=""):
    return {"event": event.pk, "user": user.pk, "comment": comment}


# --- PlanFilterForm (forms.Form, GET) ---------------------------------

def test_filter_form_accepts_russian_date_format():
    """Локаль ru-RU: кроме ГГГГ-ММ-ДД принимается ДД.ММ.ГГГГ."""
    form = PlanFilterForm({"date": "17.10.2026"})
    assert form.is_valid()
    assert form.cleaned_data["date"] == date(2026, 10, 17)


def test_filter_form_converts_values():
    """is_valid() и cleaned_data: строка → date, id → объект модели."""
    form = PlanFilterForm({"date": "2026-10-17", "event": "1",
                           "user": "1", "status": "active", "sort": "user"})
    assert form.is_valid()
    assert form.cleaned_data["date"] == date(2026, 10, 17)
    assert form.cleaned_data["event"] == Event.objects.get(pk=1)
    assert form.cleaned_data["user"].name == "Анна"


@pytest.mark.parametrize("params, field", [
    ({"date": "2026-13-45"}, "date"),
    ({"event": "999"}, "event"),
    ({"user": "abc"}, "user"),
    ({"status": "deleted"}, "status"),
    ({"sort": "id; DROP TABLE"}, "sort"),
])
def test_filter_form_rejects_bad_values(params, field):
    """Встроенная валидация полей формы фильтрации."""
    form = PlanFilterForm(params)
    assert not form.is_valid()
    assert field in form.errors


def test_plan_list_uses_filter_form(client):
    """Список записей получает форму, фильтры применяются из GET."""
    response = client.get("/plans/", {"event": 1, "status": "active"})
    assert isinstance(response.context["form"], PlanFilterForm)
    assert response.context["total"] == 2
    html = response.content.decode()
    assert 'name="event"' in html and "form-select" in html


def test_plan_list_invalid_filter_shows_error(client):
    """Ошибочный фильтр выводит сообщение и не роняет страницу."""
    response = client.get("/plans/", {"event": "999"})
    assert response.status_code == 200
    assert "Выберите корректный вариант" in response.content.decode()
    assert response.context["total"] == Plan.objects.count()


# --- EventSearchForm ---------------------------------------------------

def test_search_form_clean_method_checks_period():
    """clean(): дата «с» не может быть позже даты «по»."""
    form = EventSearchForm({"date_from": "2026-12-31",
                            "date_to": "2026-01-01"})
    assert not form.is_valid()
    assert "позже" in form.non_field_errors()[0]


def test_search_form_accepts_comma_price():
    """clean_max_price(): цена с запятой превращается в Decimal."""
    form = EventSearchForm({"max_price": "1500,5"})
    assert form.is_valid()
    assert form.cleaned_data["max_price"] == Decimal("1500.5")


# --- PlanForm (ModelForm): создание ------------------------------------

def test_plan_form_fields_and_widgets():
    """ModelForm связана с моделью Plan; status в форму не входит."""
    form = PlanForm()
    assert list(form.fields) == ["event", "user", "comment"]
    assert form.fields["comment"].widget.attrs["rows"] == 3
    assert "form-select" in form.fields["event"].widget.attrs["class"]
    assert form.fields["event"].help_text


def test_create_page_get_shows_empty_form_with_csrf(client):
    """GET: пустая форма, CSRF-токен, начальные значения из ссылки."""
    response = client.get("/plans/create/", {"event": 5})
    html = response.content.decode()
    assert response.status_code == 200
    assert "csrfmiddlewaretoken" in html
    assert response.context["form"].initial["event"] == "5"


def test_create_valid_plan_redirects(client, concert, boris):
    """POST с корректными данными: запись создана, переход к карточке."""
    response = client.post("/plans/create/",
                           plan_data(concert, boris, "Первый ряд"))
    plan = Plan.objects.get(event=concert, user=boris)
    assert response.status_code == 302
    assert response["Location"] == reverse("planner:detail",
                                           args=[plan.pk])
    assert plan.status == Plan.Status.ACTIVE
    assert plan.comment == "Первый ряд"


def test_create_invalid_form_is_shown_again(client, concert):
    """Ошибка: форма показывается снова, запись не создаётся."""
    before = Plan.objects.count()
    response = client.post("/plans/create/", {"event": concert.pk})
    assert response.status_code == 200
    assert "Выберите посетителя." in response.content.decode()
    assert Plan.objects.count() == before


def test_past_event_is_rejected(client, boris):
    """clean_event(): на прошедшее мероприятие записаться нельзя."""
    past = Event.objects.create(
        name="Прошедший концерт", category="концерт",
        event_date=date.today() - timedelta(days=1), ticket_price=100,
        capacity=10)
    form = PlanForm(plan_data(past, boris))
    assert not form.is_valid()
    assert "прошедшее" in form.errors["event"][0]


def test_duplicate_active_plan_is_rejected(concert, boris):
    """Повторная активная запись того же посетителя отклоняется."""
    Plan.objects.create(event=concert, user=boris)
    form = PlanForm(plan_data(concert, boris))
    assert not form.is_valid()
    assert "уже записан" in form.non_field_errors()[0]


def test_full_event_blocks_and_cancelled_frees_seat(concert, boris, egor):
    """Активные записи занимают места, отменённая – не блокирует."""
    Plan.objects.create(event=concert, user=boris)
    taken = Plan.objects.create(event=concert, user=User.objects.create(
        name="Ирина", age=40, preferred_category="концерт", budget=5000))
    form = PlanForm(plan_data(concert, egor))
    assert not form.is_valid()
    assert "свободных мест нет" in form.non_field_errors()[0]
    taken.cancel()
    assert PlanForm(plan_data(concert, egor)).is_valid()


@pytest.mark.parametrize("user_id, message", [
    (3, "возрастное ограничение"),   # Вера, 15 лет, на 16+
    (1, "по выбранной категории"),   # Анна любит театр
])
def test_domain_rules_of_pr1(user_id, message):
    """Правила ПР1: возраст и категория (джазовый вечер 16+)."""
    event = Event.objects.get(pk=4)
    event.event_date = FUTURE
    event.save()
    form = PlanForm(plan_data(event, User.objects.get(pk=user_id)))
    assert not form.is_valid()
    assert message in form.non_field_errors()[0]


def test_budget_rule(concert):
    """Цена билета больше бюджета посетителя."""
    poor = User.objects.create(name="Олег", age=30,
                               preferred_category="концерт", budget=500)
    form = PlanForm(plan_data(concert, poor))
    assert not form.is_valid()
    assert "превышает бюджет" in form.non_field_errors()[0]


def test_custom_validator_rejects_links(concert, boris):
    """Валидатор-функция validate_no_links для комментария."""
    form = PlanForm(plan_data(concert, boris, "см. https://spam.example"))
    assert not form.is_valid()
    assert "ссылок" in form.errors["comment"][0]


# --- редактирование ----------------------------------------------------

def test_edit_form_is_filled_from_instance(client, concert, boris):
    """GET: форма заполнена данными существующей записи (instance)."""
    plan = Plan.objects.create(event=concert, user=boris, comment="x")
    response = client.get(f"/plans/{plan.pk}/edit/")
    assert response.context["form"].instance == plan
    assert response.context["form"]["comment"].value() == "x"


def test_edit_without_changes_does_not_conflict_with_itself(
        client, concert, boris, egor):
    """Редактируемая запись исключается из проверки мест и дублей."""
    Plan.objects.create(event=concert, user=egor)
    plan = Plan.objects.create(event=concert, user=boris)  # мест больше нет
    response = client.post(f"/plans/{plan.pk}/edit/",
                           plan_data(concert, boris, "Без изменений"))
    assert response.status_code == 302
    plan.refresh_from_db()
    assert plan.comment == "Без изменений"
    assert Plan.objects.filter(event=concert).count() == 2


def test_edit_to_conflicting_values_is_rejected(client, concert, boris):
    """Изменение на мероприятие, где посетитель уже записан, отклоняется."""
    Plan.objects.create(event=concert, user=boris)
    other = Event.objects.create(
        name="Органный вечер", category="концерт", event_date=FUTURE,
        ticket_price=500, capacity=5)
    plan = Plan.objects.create(event=other, user=boris)
    response = client.post(f"/plans/{plan.pk}/edit/",
                           plan_data(concert, boris))
    assert response.status_code == 200
    assert "уже записан" in response.content.decode()
    plan.refresh_from_db()
    assert plan.event == other


@pytest.mark.parametrize("plan_id", [999, 5])
def test_edit_missing_or_cancelled_plan_returns_404(client, plan_id):
    """get_object_or_404(Plan.objects.active(), ...) – 404."""
    assert client.get(f"/plans/{plan_id}/edit/").status_code == 404


# --- отмена ------------------------------------------------------------

def test_cancel_by_post_changes_status(client):
    """POST: статус CANCELLED, запись остаётся в базе."""
    response = client.post("/plans/1/cancel/")
    assert response.status_code == 302
    plan = Plan.objects.get(pk=1)
    assert plan.status == Plan.Status.CANCELLED
    assert "отменена" in client.get("/plans/").content.decode()


def test_cancel_by_get_is_not_allowed(client):
    """GET-запрос на адрес отмены не меняет данные (405)."""
    assert client.get("/plans/1/cancel/").status_code == 405
    assert Plan.objects.get(pk=1).status == Plan.Status.ACTIVE


def test_cancel_twice_returns_404(client):
    """Повторная отмена: активной записи уже нет."""
    client.post("/plans/1/cancel/")
    assert client.post("/plans/1/cancel/").status_code == 404


def test_forms_have_csrf_token(client):
    """Формы, изменяющие данные, содержат CSRF-токен."""
    for url in ("/plans/", "/plans/1/", "/plans/create/", "/plans/1/edit/",
                "/events/create/"):
        assert "csrfmiddlewaretoken" in client.get(url).content.decode()


def test_csrf_is_enforced():
    """Без токена POST отклоняется (403)."""
    from django.test import Client

    strict = Client(SERVER_NAME="localhost", enforce_csrf_checks=True)
    assert strict.post("/plans/1/cancel/").status_code == 403


# --- мероприятия и постер ----------------------------------------------

def png_file(name="poster.png"):
    buffer = BytesIO()
    Image.new("RGB", (20, 10), "purple").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(),
                              content_type="image/png")


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_event_form_validates_category_and_date():
    """Валидатор категории и clean_event_date()."""
    form = EventForm({"name": "X", "category": "театр 2", "age_limit": 0,
                      "event_date": "2000-01-01", "ticket_price": "10",
                      "capacity": 5})
    assert not form.is_valid()
    assert "category" in form.errors and "event_date" in form.errors


def test_event_create_with_poster(client, media_root):
    """Загрузка файла: request.FILES, ImageField, MEDIA_ROOT/events/."""
    response = client.post("/events/create/", {
        "name": "Выставка плакатов", "category": "Выставка",
        "event_date": "2099-03-01", "age_limit": 0, "ticket_price": "300",
        "capacity": 20, "poster": png_file(),
    })
    event = Event.objects.get(name="Выставка плакатов")
    assert response.status_code == 302
    assert response["Location"] == event.get_absolute_url()
    assert event.poster.name.startswith("events/")
    assert (media_root / event.poster.name).exists()
    html = client.get(event.get_absolute_url()).content.decode()
    assert event.poster.url in html


def test_event_update_replaces_poster(client, media_root):
    """Изменение мероприятия: новый файл заменяет ссылку на постер."""
    event = Event.objects.get(pk=5)
    response = client.post(f"/events/{event.slug}/edit/", {
        "name": event.name, "category": event.category,
        "event_date": event.event_date.isoformat(),
        "age_limit": event.age_limit, "ticket_price": event.ticket_price,
        "capacity": event.capacity, "poster": png_file("new.png"),
    })
    assert response.status_code == 302
    event.refresh_from_db()
    assert event.poster.name.startswith("events/new")


def test_not_image_is_rejected(client, media_root):
    """ImageField проверяет, что загружено изображение."""
    fake = SimpleUploadedFile("poster.png", b"not an image",
                              content_type="image/png")
    response = client.post("/events/create/", {
        "name": "Фальшивка", "category": "театр", "event_date": "2099-03-01",
        "age_limit": 0, "ticket_price": "1", "capacity": 1, "poster": fake,
    })
    assert response.status_code == 200
    assert not Event.objects.filter(name="Фальшивка").exists()
