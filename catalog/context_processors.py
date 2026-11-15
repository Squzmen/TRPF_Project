"""Контекстный процессор проекта (ПР10).

Функция вызывается при отрисовке каждого шаблона через RequestContext и
добавляет общие для всех страниц данные, не дублируя их в представлениях.
"""

from catalog.models import Event
from planner.models import Plan

SITE_NAME = "Культурный досуг"


def leisure_context(request):
    """Название сайта, число мероприятий и константы статусов записи."""
    return {
        "site_name": SITE_NAME,
        # count() выполняет SELECT COUNT(*) и не загружает объекты.
        "events_count": Event.objects.count(),
        # Шаблоны сравнивают статус с Plan.Status, а не со строками.
        "plan_status": Plan.Status,
    }
