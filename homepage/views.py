"""Главная страница, общий каркас HTML-страниц и обработчик ошибки 404."""

from django.http import HttpResponse
from django.utils.html import escape


def page(title, content):
    """Собрать HTML-документ: кодировка, заголовок, Bootstrap, навигация."""
    bootstrap = (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3"
        "/dist/css/bootstrap.min.css"
    )
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)}</title>
    <link rel="stylesheet" href="{bootstrap}">
</head>
<body>
    <nav class="nav">
        <a class="nav-link" href="/">Главная</a>
        <a class="nav-link" href="/events/">Мероприятия</a>
        <a class="nav-link" href="/plans/">Планы</a>
    </nav>
    <main class="container">{content}</main>
</body>
</html>"""


def index(request):
    """Главная страница: описание системы и ссылки на разделы."""
    content = """
    <h1 class="display-4">Культурный досуг</h1>
    <p class="lead">Система планирования культурного досуга.</p>
    <p>Основные разделы:</p>
    <a href="/events/" class="btn btn-primary me-2">Мероприятия</a>
    <a href="/plans/" class="btn btn-secondary">Планы</a>
    """
    return HttpResponse(page("Культурный досуг", content))


def page_not_found(request, exception):
    """Собственная страница ошибки 404 для любого неизвестного адреса."""
    content = """
    <h1 class="text-danger">404 – страница не найдена</h1>
    <p>Проверьте адрес или вернитесь на главную.</p>
    <a href="/" class="btn btn-primary">На главную</a>
    """
    return HttpResponse(
        page("404 – страница не найдена", content),
        status=404,
    )
