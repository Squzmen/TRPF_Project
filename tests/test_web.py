"""Проверки веб-интерфейса Django: маршруты, view-функции, страницы (ПР5)."""

import pytest
from django.test import Client, override_settings
from django.urls import resolve
from django.utils.html import escape

from homepage.views import page
from plans import remaining_seats
from storage import load_data

PAGES = ["/", "/events/", "/events/1/", "/plans/", "/plans/1/"]


@pytest.fixture
def client():
    """Тестовый клиент, обращающийся к разрешённому хосту localhost."""
    return Client(SERVER_NAME="localhost")


@pytest.mark.parametrize("url", PAGES)
def test_pages_open(client, url):
    """Каждая страница отвечает кодом 200 и возвращает HTML."""
    response = client.get(url)
    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]


@pytest.mark.parametrize("url", PAGES)
def test_pages_have_common_layout(client, url):
    """Общий каркас page(): Bootstrap и навигация есть на всех страницах."""
    html = client.get(url).content.decode()
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


def test_event_list_shows_events_from_json(client):
    """Список мероприятий строится по объектам Event из ПР3."""
    events, _users, _plans = load_data()
    html = client.get("/events/").content.decode()
    for event in events:
        assert escape(event.name) in html
        assert f'href="/events/{event.id}/"' in html


def test_event_detail_uses_object_attributes_and_seats(client):
    """Страница мероприятия показывает атрибуты Event и число мест."""
    events, _users, plans = load_data()
    for event in events:
        html = client.get(f"/events/{event.id}/").content.decode()
        seats = remaining_seats(plans, event)
        assert escape(event.name) in html
        assert event.category in html
        assert f"{event.ticket_price:.2f}" in html
        assert (f"свободно мест: {seats}" if seats else "мест нет") in html


def test_plan_pages_show_related_objects(client):
    """Запись показывает связанные объекты Event и User и статус."""
    _events, _users, plans = load_data()
    for plan in plans:
        html = client.get(f"/plans/{plan.id}/").content.decode()
        assert escape(plan.event.name) in html
        assert escape(plan.user.name) in html
        assert ("отменена" if plan.is_cancelled else "активна") in html


@pytest.mark.parametrize("url, text", [
    ("/events/999/", "Мероприятие не найдено"),
    ("/plans/999/", "Запись не найдена"),
])
def test_missing_object_returns_404(client, url, text):
    """Несуществующий идентификатор даёт страницу с кодом 404."""
    response = client.get(url)
    assert response.status_code == 404
    assert text in response.content.decode()


def test_non_integer_id_is_not_routed(client):
    """Конвертер <int:...> не пропускает текст вместо идентификатора."""
    assert client.get("/events/abc/").status_code == 404
    assert client.get("/plans/abc/").status_code == 404


def test_custom_404_handler_when_debug_is_off(client):
    """При DEBUG=False неизвестный адрес обрабатывает handler404."""
    with override_settings(DEBUG=False):
        response = client.get("/nonexistent/")
    assert response.status_code == 404
    html = response.content.decode()
    assert "404 – страница не найдена" in html
    assert "bootstrap@5.3.3" in html


def test_page_escapes_title():
    """Заголовок вкладки экранируется и не ломает разметку."""
    html = page("<b>Тест</b>", "")
    assert "<title>&lt;b&gt;Тест&lt;/b&gt;</title>" in html
