"""Проверки веб-интерфейса Django: маршруты, шаблоны, статика (ПР5–ПР6)."""

import inspect

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
from plans import remaining_seats
from storage import load_data

PAGES = ["/", "/events/", "/events/1/", "/plans/", "/plans/1/"]


@pytest.fixture
def client():
    """Тестовый клиент, обращающийся к разрешённому хосту localhost."""
    return Client(SERVER_NAME="localhost")


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
    ("/events/3/", "event_detail", {"event_id": 3}),
    ("/plans/", "plan_list", {}),
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
    assert reverse("planner:list") == "/plans/"
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
    """Фильтр length, цикл по Event и ссылки через {% url %}."""
    events, _users, plans = load_data()
    html = client.get("/events/").content.decode()
    assert f"Всего мероприятий: {len(events)}" in html
    for event in events:
        assert escape(event.name) in html
        assert f'href="/events/{event.id}/"' in html
        assert event.event_date.strftime("%d.%m.%Y") in html
        assert f"{floatformat(event.ticket_price, 2)} руб." in html
        seats = remaining_seats(plans, event)
        assert (f"свободно мест: {seats}" if seats else "мест нет") in html


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


def test_plans_page_shows_related_objects_and_status(client):
    """Записи показывают связанные Event и User и include статуса."""
    _events, _users, plans = load_data()
    html = client.get("/plans/").content.decode()
    assert f"Всего записей: {len(plans)}" in html
    assert html.count("plan-status-cancelled") == sum(
        plan.is_cancelled for plan in plans
    )
    assert html.count("plan-status-active") == sum(
        not plan.is_cancelled for plan in plans
    )
    for plan in plans:
        detail = client.get(f"/plans/{plan.id}/").content.decode()
        assert escape(plan.event.name) in detail
        assert escape(plan.user.name) in detail
        assert ("Отменена" if plan.is_cancelled else "Активна") in detail


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
