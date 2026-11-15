"""Корневая конфигурация маршрутов проекта."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("homepage.urls")),
    path("events/", include("catalog.urls")),
    path("plans/", include("planner.urls")),
]

# В режиме разработки Django сам раздаёт загруженные файлы.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

if settings.DEBUG_TOOLBAR:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()

handler404 = "homepage.views.page_not_found"
