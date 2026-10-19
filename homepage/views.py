"""Главная страница и обработчик ошибки 404 (HTML формируют шаблоны)."""

from django.shortcuts import render


def index(request):
    """Главная страница: контекст не нужен, данные не выводятся."""
    return render(
        request,
        "homepage/index.html",
    )


def page_not_found(request, exception):
    """Собственная страница ошибки 404 для любого неизвестного адреса."""
    return render(
        request,
        "homepage/404.html",
        status=404,
    )
