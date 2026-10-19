"""Проверки веб-интерфейса Django: маршруты, шаблоны, статика (ПР5–ПР6)."""

import inspect
import sqlite3
from datetime import date

import pytest
from django.contrib.staticfiles import finders
from django.template import engines
from django.template.defaultfilters import floatformat
from django.test import Client, override_settings
from django.urls import resolve, reverse
from django.utils.html import escape

import catalog.views
import homepage.views
import planner.views
from db.database import get_connection
from plans import plan_statistics, remaining_seats
from storage import load_data

PAGES = ["/", "/events/", "/events/1/", "/events/search/",
         "/events/recommend/", "/plans/", "/plans/1/",
         "/plans/statistics/"]


@pytest.fixture
def client():
    """Тестовый клиент, обращающийся к разрешённому хосту localhost."""
    return Client(SERVER_NAME="localhost")


def db_rows(query, params=()):
    """Выполнить SQL-запрос к базе проекта и вернуть строки как словари."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(query, params)]
    finally:
        conn.close()


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
    ("/events/3/", "event_detail", {"event_id": 3}),
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
    assert reverse("catalog:detail", args=[3]) == "/events/3/"
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
            "planner/includes/plan_status.html"} <= template_names(plans_page)
    assert "homepage/index.html" in template_names(client.get("/"))


def test_events_page_count_filter_and_cards(client):
    """Список мероприятий из SQLite: length, цикл, карточки, ссылки."""
    events = db_rows("SELECT * FROM events ORDER BY id")
    html = client.get("/events/").content.decode()
    assert f"Всего мероприятий: {len(events)}" in html
    for event in events:
        assert escape(event["name"]) in html
        assert f'href="/events/{event["id"]}/"' in html
        assert date.fromisoformat(event["event_date"]).strftime(
            "%d.%m.%Y") in html
        assert f"{floatformat(event['ticket_price'], 2)} руб." in html


def test_events_page_shows_free_seats_from_sql(client):
    """Число свободных мест вычисляет SQL-запрос."""
    rows = db_rows(
        "SELECT e.id, e.capacity - (SELECT COUNT(*) FROM plans AS p "
        "WHERE p.event_id = e.id AND p.is_cancelled = 0) AS seats_left "
        "FROM events AS e"
    )
    html = client.get("/events/").content.decode()
    assert html.count("свободно мест:") == sum(
        row["seats_left"] > 0 for row in rows)
    assert html.count("мест нет") == sum(
        row["seats_left"] <= 0 for row in rows)


def test_events_filter_by_category_uses_where(client):
    """Параметр category оставляет только мероприятия категории."""
    events = db_rows("SELECT * FROM events")
    category = events[0]["category"]
    html = client.get("/events/", {"category": category}).content.decode()
    for event in events:
        assert (escape(event["name"]) in html) == (
            event["category"] == category)


@pytest.mark.parametrize("value", ["' OR 1=1 --", "x'; DROP TABLE events;--"])
def test_sql_injection_in_category_is_harmless(client, value):
    """Значение передаётся параметром ?, таблицы остаются целыми."""
    response = client.get("/events/", {"category": value})
    assert response.status_code == 200
    assert "Мероприятия не найдены." in response.content.decode()
    assert db_rows("SELECT COUNT(*) AS n FROM events")[0]["n"] > 0


def test_event_search_form_without_parameters(client):
    """Без параметров показывается только форма поиска."""
    response = client.get("/events/search/")
    html = response.content.decode()
    assert response.status_code == 200
    assert 'name="date_from"' in html and 'name="max_price"' in html
    assert "Найдено:" not in html


def test_event_search_by_dates_and_price(client):
    """Поиск возвращает мероприятия периода не дороже заданной цены."""
    params = {"date_from": "2026-11-01", "date_to": "2026-12-31",
              "max_price": "2000"}
    expected = db_rows(
        "SELECT name FROM events WHERE event_date BETWEEN ? AND ? "
        "AND ticket_price <= ?", ["2026-11-01", "2026-12-31", 2000.0])
    others = db_rows(
        "SELECT name FROM events WHERE NOT (event_date BETWEEN ? AND ? "
        "AND ticket_price <= ?)", ["2026-11-01", "2026-12-31", 2000.0])
    html = client.get("/events/search/", params).content.decode()
    assert f"Найдено: {len(expected)}" in html
    for row in expected:
        assert escape(row["name"]) in html
    for row in others:
        assert escape(row["name"]) not in html


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
    """SQL-подбор совпадает с проверками объектной модели ПР3."""
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


def test_event_detail_uses_object_attributes_and_seats(client):
    """Страница мероприятия показывает атрибуты Event и число мест."""
    events, _users, plans = load_data()
    for event in events:
        html = client.get(f"/events/{event.id}/").content.decode()
        seats = remaining_seats(plans, event)
        assert escape(event.name) in html
        assert event.category in html
        assert f"{floatformat(event.ticket_price, 2)} руб." in html
        assert (f"свободно мест: {seats}" if seats else "мест нет") in html


def test_plans_page_shows_joined_data_and_status(client):
    """Список записей из SQLite: JOIN, include статуса, фильтр status."""
    plans = db_rows(
        "SELECT p.id, p.is_cancelled, e.name AS event_name, "
        "u.name AS user_name FROM plans AS p "
        "JOIN events AS e ON p.event_id = e.id "
        "JOIN users AS u ON p.user_id = u.id")
    html = client.get("/plans/").content.decode()
    assert f"Всего записей: {len(plans)}" in html
    assert html.count("plan-status-cancelled") == sum(
        row["is_cancelled"] for row in plans)
    assert html.count("plan-status-active") == sum(
        not row["is_cancelled"] for row in plans)
    for row in plans:
        assert escape(row["event_name"]) in html
        assert escape(row["user_name"]) in html
        assert f'href="/plans/{row["id"]}/"' in html


def test_plans_page_active_filter(client):
    """Параметр status=active убирает отменённые записи."""
    active = db_rows("SELECT COUNT(*) AS n FROM plans WHERE is_cancelled=0")
    html = client.get("/plans/", {"status": "active"}).content.decode()
    assert f"Всего записей: {active[0]['n']}" in html
    assert "plan-status-cancelled" not in html


def test_plan_detail_shows_related_objects(client):
    """Карточка записи показывает связанные Event и User и статус."""
    _events, _users, plans = load_data()
    for plan in plans:
        detail = client.get(f"/plans/{plan.id}/").content.decode()
        assert escape(plan.event.name) in detail
        assert escape(plan.user.name) in detail
        assert ("Отменена" if plan.is_cancelled else "Активна") in detail


def test_statistics_page_matches_console_statistics(client):
    """Агрегаты SQLite совпадают со статистикой консольной версии."""
    events, _users, plans = load_data()
    stats = plan_statistics(events, plans)
    html = client.get("/plans/statistics/").content.decode()
    assert f"Активных записей: {stats['plans']}" in html
    assert f"{floatformat(stats['total_price'], 2)} руб." in html
    for title in ("Записи по мероприятиям", "Популярные мероприятия",
                  "Категории", "Посетители"):
        assert title in html


def test_statistics_lists_events_without_plans(client):
    """LEFT JOIN сохраняет мероприятия без записей со значением 0."""
    empty = db_rows(
        "SELECT e.name FROM events AS e LEFT JOIN plans AS p "
        "ON p.event_id = e.id AND p.is_cancelled = 0 "
        "GROUP BY e.id HAVING COUNT(p.id) = 0")
    html = client.get("/plans/statistics/").content.decode()
    for row in empty:
        assert escape(row["name"]) in html


def test_navigation_links_to_statistics(client):
    """Навигация ведёт во все основные разделы, включая статистику."""
    html = client.get("/").content.decode()
    assert 'href="/plans/statistics/"' in html


@pytest.mark.parametrize("url, text", [
    ("/events/999/", "Мероприятие не найдено"),
    ("/plans/999/", "Запись не найдена"),
])
def test_missing_object_returns_404_page_from_template(client, url, text):
    """Нет объекта: страница-шаблон с сообщением и статус 404."""
    response = client.get(url)
    assert response.status_code == 404
    assert text in response.content.decode()
    assert "base.html" in template_names(response)


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


def test_page_helper_is_not_used_any_more():
    """Функция page() удалена, HTML в view-функциях не формируется."""
    assert not hasattr(homepage.views, "page")
    for module in (homepage.views, catalog.views, planner.views):
        source = inspect.getsource(module)
        assert "page(" not in source.replace("page_not_found(", "")
        assert "HttpResponse" not in source
        assert "render(" in source


def test_template_autoescape_protects_from_html():
    """Значения в {{ ... }} экранируются автоматически."""
    template = engines["django"].from_string("{{ value }}")
    assert template.render({"value": "<b>x</b>"}) == "&lt;b&gt;x&lt;/b&gt;"
