"""Проверки веб-интерфейса Django: маршруты, шаблоны, статика, ORM."""

import inspect
from datetime import date

import pytest
from django.contrib.staticfiles import finders
from django.template import engines
from django.template.defaultfilters import floatformat
from django.test import override_settings
from django.urls import resolve, reverse
from django.utils.html import escape

import catalog.views
import homepage.views
import planner.views
from catalog.models import Event
from planner.models import Plan
from plans import plan_statistics, remaining_seats
from storage import load_data
from visitors.models import User

pytestmark = pytest.mark.usefixtures("project_data")

PAGES = ["/", "/events/", "/events/spektakl-gamlet/", "/events/search/",
         "/events/recommend/", "/plans/", "/plans/1/",
         "/plans/statistics/"]


def template_names(response):
    """Имена всех шаблонов, использованных при формировании ответа."""
    return {template.name for template in response.templates}


@pytest.mark.parametrize("url", PAGES)
def test_pages_open(client, url):
    """Каждая страница отвечает кодом 200 и возвращает HTML."""
    response = client.get(url)
    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]


@pytest.mark.parametrize("url", PAGES)
def test_pages_extend_base_template(client, url):
    """Все страницы наследуют base.html и подключают навигацию."""
    response = client.get(url)
    names = template_names(response)
    assert "base.html" in names
    assert "includes/navigation.html" in names
    html = response.content.decode()
    assert "bootstrap@5.3.3" in html
    assert 'href="/events/"' in html
    assert 'href="/plans/"' in html


@pytest.mark.parametrize("url, view_name, kwargs", [
    ("/", "index", {}),
    ("/events/", "event_list", {}),
    ("/events/search/", "event_search", {}),
    ("/events/recommend/", "event_recommend", {}),
    ("/events/3/", "event_redirect", {"event_id": 3}),
    ("/events/dzhazovyi-vecher/", "event_detail",
     {"slug": "dzhazovyi-vecher"}),
    ("/plans/", "plan_list", {}),
    ("/plans/statistics/", "statistics", {}),
    ("/plans/2/", "plan_detail", {"plan_id": 2}),
])
def test_url_resolves_to_view(url, view_name, kwargs):
    """URL связан с нужной view-функцией, параметр передаётся из пути."""
    match = resolve(url)
    assert match.func.__name__ == view_name
    assert match.kwargs == kwargs


def test_named_urls_with_namespaces():
    """Именованные маршруты строятся через пространства имён."""
    assert reverse("homepage:index") == "/"
    assert reverse("catalog:list") == "/events/"
    assert reverse("catalog:detail", kwargs={"slug": "abc"}) == "/events/abc/"
    assert reverse("catalog:detail_by_id", args=[3]) == "/events/3/"
    assert reverse("catalog:search") == "/events/search/"
    assert reverse("catalog:recommend") == "/events/recommend/"
    assert reverse("planner:list") == "/plans/"
    assert reverse("planner:statistics") == "/plans/statistics/"
    assert reverse("planner:detail", args=[2]) == "/plans/2/"


def test_templates_are_used_with_includes(client):
    """Страницы собираются из шаблонов приложений и включаемых фрагментов."""
    events_page = client.get("/events/")
    assert {"catalog/event_list.html",
            "catalog/includes/event_card.html"} <= template_names(events_page)
    plans_page = client.get("/plans/")
    assert {"planner/plan_list.html",
            "planner/includes/plan_status.html",
            "includes/pagination.html"} <= template_names(plans_page)
    assert "homepage/index.html" in template_names(client.get("/"))


def test_events_page_lists_all_events_from_orm(client):
    """Список мероприятий из ORM: число, карточки, даты, цены, ссылки."""
    html = client.get("/events/").content.decode()
    events = Event.objects.all()
    assert f"Всего мероприятий: {events.count()}" in html
    for event in events:
        assert escape(event.name) in html
        assert f'href="{event.get_absolute_url()}"' in html
        assert event.event_date.strftime("%d.%m.%Y") in html
        assert f"{floatformat(event.ticket_price, 2)} руб." in html


def test_free_seats_match_console_rules(client):
    """Свободные места из ORM совпадают с расчётом консольной версии."""
    events, _users, plans = load_data()
    html = client.get("/events/").content.decode()
    assert html.count("свободно мест:") == sum(
        remaining_seats(plans, event) > 0 for event in events)
    assert html.count("мест нет") == sum(
        remaining_seats(plans, event) <= 0 for event in events)


def test_events_filter_by_category(client):
    """Параметр category оставляет только мероприятия категории."""
    html = client.get("/events/", {"category": "концерт"}).content.decode()
    for event in Event.objects.all():
        assert (escape(event.name) in html) == (event.category == "концерт")


def test_events_search_ignores_case_for_cyrillic(client):
    """Поиск icontains находит название и категорию в любом регистре."""
    html = client.get("/events/", {"q": "гамлет"}).content.decode()
    assert "Всего мероприятий: 1" in html
    assert escape("Спектакль «Гамлет»") in html
    html = client.get("/events/", {"q": "КОНЦЕРТ"}).content.decode()
    assert "Всего мероприятий: 2" in html


def test_events_sort_by_price_descending(client):
    """sort=-price: первым идёт самое дорогое мероприятие."""
    response = client.get("/events/", {"sort": "-price"})
    names = [event.name for event in response.context["events"]]
    expected = list(Event.objects.order_by("-ticket_price", "name")
                    .values_list("name", flat=True))
    assert names == expected


def test_unknown_sort_falls_back_to_date(client):
    """Неизвестное значение sort не передаётся в order_by()."""
    response = client.get("/events/", {"sort": "id; DROP TABLE"})
    assert response.status_code == 200
    assert response.context["sort"] == "date"


@pytest.mark.parametrize("value", ["' OR 1=1 --", "x'; DROP TABLE events;--"])
def test_injection_in_category_is_harmless(client, value):
    """ORM передаёт значение параметром, таблицы остаются целыми."""
    response = client.get("/events/", {"category": value})
    assert response.status_code == 200
    assert "Мероприятия не найдены." in response.content.decode()
    assert Event.objects.count() == 5


def test_event_search_form_without_parameters(client):
    """Без параметров показывается только форма поиска."""
    html = client.get("/events/search/").content.decode()
    assert 'name="date_from"' in html and 'name="max_price"' in html
    assert "Найдено:" not in html


def test_event_search_by_dates_and_price(client):
    """Поиск возвращает мероприятия периода не дороже заданной цены."""
    params = {"date_from": "2026-11-01", "date_to": "2026-12-31",
              "max_price": "2000"}
    expected = Event.objects.filter(
        event_date__range=(date(2026, 11, 1), date(2026, 12, 31)),
        ticket_price__lte=2000,
    )
    html = client.get("/events/search/", params).content.decode()
    assert f"Найдено: {expected.count()}" in html
    for event in Event.objects.all():
        assert (escape(event.name) in html) == (event in expected)


@pytest.mark.parametrize("params, message", [
    ({"date_from": "31.12.2026"}, "формате ГГГГ-ММ-ДД"),
    ({"max_price": "дорого"}, "неотрицательное число"),
    ({"max_price": "-5"}, "неотрицательное число"),
])
def test_event_search_reports_invalid_input(client, params, message):
    """Некорректный ввод даёт сообщение и не вызывает ошибку сервера."""
    response = client.get("/events/search/", params)
    assert response.status_code == 200
    assert message in response.content.decode()


def test_event_recommend_matches_domain_rules(client):
    """ORM-подбор совпадает с проверками объектной модели ПР3."""
    events, users, plans = load_data()
    today = date.today()
    for user in users:
        expected = {
            event.name for event in events
            if user.is_interested_in(event)
            and event.is_age_allowed(user.age)
            and event.is_budget_enough(user.budget)
            and event.event_date >= today
            and remaining_seats(plans, event) > 0
            and not any(plan.user.id == user.id and plan.event.id == event.id
                        and not plan.is_cancelled for plan in plans)
        }
        html = client.get("/events/recommend/",
                          {"user": user.id}).content.decode()
        assert f"Подходящих мероприятий: {len(expected)}" in html
        for event in events:
            assert (escape(event.name) in html) == (event.name in expected)


@pytest.mark.parametrize("value", ["999", "abc", "1 OR 1=1"])
def test_event_recommend_unknown_user(client, value):
    """Неизвестный или некорректный номер посетителя – сообщение."""
    response = client.get("/events/recommend/", {"user": value})
    assert response.status_code == 200
    assert "не найден" in response.content.decode()


def test_event_detail_shows_seats_and_reverse_relation(client):
    """Карточка: атрибуты Event, свободные места, записавшиеся посетители."""
    events, _users, plans = load_data()
    for event in events:
        html = client.get(f"/events/{event.id}/",
                          follow=True).content.decode()
        seats = remaining_seats(plans, event)
        assert escape(event.name) in html
        assert (f"свободно мест: {seats}" if seats else "мест нет") in html
        for plan in plans:
            if plan.event.id == event.id and not plan.is_cancelled:
                assert escape(plan.user.name) in html


def test_plans_page_shows_related_data_and_status(client):
    """Список записей: данные связанных моделей и статус."""
    response = client.get("/plans/", {"page": 1})
    html = response.content.decode()
    assert f"Всего записей: {Plan.objects.count()}" in html
    for plan in response.context["plans"]:
        assert escape(plan["event_name"]) in html
        assert escape(plan["user_name"]) in html
        assert f'href="/plans/{plan["id"]}/"' in html


def test_plans_page_active_filter(client):
    """status=active убирает отменённые записи."""
    html = client.get("/plans/", {"status": "active"}).content.decode()
    active = Plan.objects.active().count()
    assert f"Всего записей: {active}" in html
    assert "plan-status-cancelled" not in html


def test_plans_filter_by_event_and_user(client):
    """Несколько фильтров сужают выборку как условие AND."""
    response = client.get("/plans/", {"event": 1, "user": 4})
    assert response.context["total"] == 1
    response = client.get("/plans/", {"event": 1})
    assert response.context["total"] == Plan.objects.filter(
        event_id=1).count()


def test_plans_filter_by_date_of_related_event(client):
    """Фильтр по дате работает по полю связанной модели Event."""
    response = client.get("/plans/", {"date": "2026-11-14"})
    assert response.context["total"] == Plan.objects.filter(
        event__event_date=date(2026, 11, 14)).count()


def test_plans_invalid_date_shows_error(client):
    """Неверная дата не ломает страницу, выводится сообщение."""
    response = client.get("/plans/", {"date": "14.11.2026"})
    assert response.status_code == 200
    assert "ГГГГ-ММ-ДД" in response.content.decode()


def test_plans_sort_by_user(client):
    """Сортировка по имени посетителя."""
    response = client.get("/plans/", {"sort": "user"})
    names = [plan["user_name"] for plan in response.context["plans"]]
    assert names == sorted(names)


def test_plans_pagination_keeps_parameters(client):
    """Пагинация: 5 записей на странице, ссылки сохраняют GET-параметры."""
    response = client.get("/plans/", {"sort": "user"})
    page = response.context["page_obj"]
    assert len(page) == planner.views.PLANS_PER_PAGE
    assert page.paginator.num_pages == 2
    html = response.content.decode()
    assert "?sort=user&amp;page=2" in html
    second = client.get("/plans/", {"sort": "user", "page": 2})
    assert len(second.context["page_obj"]) == 1


@pytest.mark.parametrize("page", ["abc", "0", "999"])
def test_plans_bad_page_number(client, page):
    """Некорректный номер страницы не вызывает ошибку."""
    assert client.get("/plans/", {"page": page}).status_code == 200


def test_plan_detail_shows_related_objects(client):
    """Карточка записи показывает связанные Event и User и статус."""
    _events, _users, plans = load_data()
    for plan in plans:
        detail = client.get(f"/plans/{plan.id}/").content.decode()
        assert escape(plan.event.name) in detail
        assert escape(plan.user.name) in detail
        assert ("Отменена" if plan.is_cancelled else "Активна") in detail


def test_statistics_page_matches_console_statistics(client):
    """Агрегаты ORM совпадают со статистикой консольной версии."""
    events, _users, plans = load_data()
    stats = plan_statistics(events, plans)
    html = client.get("/plans/statistics/").content.decode()
    assert f"Активных записей: {stats['plans']}" in html
    assert f"{floatformat(stats['total_price'], 2)} руб." in html
    for title in ("Записи по мероприятиям", "Популярные мероприятия",
                  "Категории", "Посетители"):
        assert title in html


def test_statistics_keeps_objects_without_plans(client):
    """Мероприятия и посетители без записей остаются со значением 0."""
    response = client.get("/plans/statistics/")
    by_event = {row["event_name"]: row for row in response.context["by_event"]}
    assert len(by_event) == Event.objects.count()
    assert by_event["Мастер-класс по гончарному делу"]["active_plans"] == 0
    by_user = list(response.context["by_user"])
    assert len(by_user) == User.objects.count()
    assert any(row["active_plans"] == 0 for row in by_user)


def test_old_id_url_redirects_to_slug(client):
    """/events/<id>/ постоянно перенаправляет на адрес get_absolute_url()."""
    response = client.get("/events/1/")
    assert response.status_code == 301
    assert response["Location"] == Event.objects.get(pk=1).get_absolute_url()


def test_plans_filter_by_each_status(client):
    """Параметр status принимает коды Plan.Status."""
    for value in Plan.Status.values:
        response = client.get("/plans/", {"status": value})
        assert response.context["total"] == Plan.objects.filter(
            status=value).count()


def test_statistics_counts_statuses(client):
    """aggregate() с Count(filter=Q(...)) по каждому статусу."""
    Plan.objects.filter(pk=6).update(status=Plan.Status.COMPLETED)
    by_status = client.get("/plans/statistics/").context["by_status"]
    assert by_status == {"total": 6, "active": 4, "cancelled": 1,
                         "completed": 1}


def test_cancelled_plan_frees_seat(client):
    """Отменённая запись не занимает место."""
    assert Event.objects.with_seats().get(pk=1).seats_left == 0
    Plan.objects.get(pk=2).cancel()
    assert Event.objects.with_seats().get(pk=1).seats_left == 1


def test_context_processor_data_on_every_page(client):
    """Контекстный процессор передаёт название сайта и число мероприятий."""
    for url in ("/", "/events/", "/plans/statistics/"):
        response = client.get(url)
        assert response.context["site_name"] == "Культурный досуг"
        assert "мероприятий в каталоге: 5" in response.content.decode()


def test_navigation_links_to_statistics(client):
    """Навигация ведёт во все основные разделы, включая статистику."""
    html = client.get("/").content.decode()
    assert 'href="/plans/statistics/"' in html


@pytest.mark.parametrize("url", ["/events/999/", "/events/no-such-event/",
                                 "/plans/999/"])
def test_missing_object_returns_404(client, url):
    """get_object_or_404(): отсутствующий объект – собственная страница 404."""
    with override_settings(DEBUG=False):
        response = client.get(url)
    assert response.status_code == 404
    assert "homepage/404.html" in template_names(response)


def test_non_integer_id_is_not_routed(client):
    """Конвертер <int:...> не пропускает текст вместо идентификатора."""
    assert client.get("/events/abc/").status_code == 404
    assert client.get("/plans/abc/").status_code == 404


def test_custom_404_handler_when_debug_is_off(client):
    """При DEBUG=False неизвестный адрес обрабатывает handler404."""
    with override_settings(DEBUG=False):
        response = client.get("/nonexistent/")
    assert response.status_code == 404
    assert "homepage/404.html" in template_names(response)
    assert "404 – страница не найдена" in response.content.decode()


def test_static_files_are_found_and_linked(client):
    """CSS, JavaScript и логотип найдены и подключены в base.html."""
    for path in ("homepage/css/style.css", "homepage/js/main.js",
                 "homepage/img/logo.png"):
        assert finders.find(path), path
    html = client.get("/").content.decode()
    assert "/static/homepage/css/style.css" in html
    assert "/static/homepage/js/main.js" in html
    assert "/static/homepage/img/logo.png" in html
    assert 'id="current-year"' in html


def test_views_use_orm_not_sqlite3():
    """Представления не выполняют SQL через sqlite3 и не формируют HTML."""
    assert not hasattr(homepage.views, "page")
    for module in (homepage.views, catalog.views, planner.views):
        source = inspect.getsource(module)
        assert "import sqlite3" not in source
        assert "execute(" not in source
        assert "HttpResponse" not in source
        assert "render(" in source


def test_template_autoescape_protects_from_html():
    """Значения в {{ ... }} экранируются автоматически."""
    template = engines["django"].from_string("{{ value }}")
    assert template.render({"value": "<b>x</b>"}) == "&lt;b&gt;x&lt;/b&gt;"
